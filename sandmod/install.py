"""Commit a previously verified Sandstorm modfile installation."""

import json
import os
import shutil
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path


class InstallError(RuntimeError):
    pass


def _is_link(path: Path) -> bool:
    # Path.is_junction() was introduced in Python 3.12.
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


@contextmanager
def _commit_lock(state_path: Path):
    """Serialize Sandmod commits to the same SDK state across processes.

    Leave the lock file in place: deleting it would allow concurrent processes
    to lock different inodes. The OS releases its byte-range lock on close,
    including when the process exits unexpectedly.
    """
    lock_path = state_path.parent / ".sandmod-commit.lock"
    try:
        lock_file = lock_path.open("a+b")
    except OSError as exc:
        raise InstallError(f"Cannot open installer lock {lock_path}: {exc}") from exc

    with lock_file:
        try:
            if os.name == "nt":
                import msvcrt

                # msvcrt.locking locks one byte starting at the file position.
                lock_file.seek(0, os.SEEK_END)
                if lock_file.tell() == 0:
                    lock_file.write(b"\0")
                    lock_file.flush()
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        except OSError as exc:
            raise InstallError(f"Cannot acquire installer lock {lock_path}: {exc}") from exc

        try:
            yield
        finally:
            # Closing the handle also releases the lock if an unlock fails.
            if os.name == "nt":
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _published_state(state_path: Path, original: bytes, updated: bytes) -> str:
    """Classify the on-disk state after a failed or interrupted operation."""
    try:
        observed = state_path.read_bytes()
    except OSError:
        return "uncertain"
    # In a force-reinstall, original and updated may be byte-for-byte equal.
    # Rolling back files is safe in that case because metadata cannot diverge.
    if observed == original:
        return "original"
    if observed == updated:
        return "published"
    return "uncertain"


def _restore_original_files(target: Path, staging: Path, backup: Path) -> None:
    """Roll back a pre-publication swap, including interrupts after rename."""
    if not backup.exists():
        if not target.is_dir() or not staging.is_dir():
            raise InstallError("Cannot identify original installation for rollback")
        return  # Neither directory move happened.

    if not backup.is_dir() or _is_link(backup):
        raise InstallError("Backup is not a safe directory for rollback")

    if target.exists() or _is_link(target):
        if not target.is_dir() or _is_link(target) or staging.exists() or _is_link(staging):
            raise InstallError("Unexpected directory layout during rollback")
        target.rename(staging)  # New files may have moved just before interruption.
    elif not staging.is_dir() or _is_link(staging):
        raise InstallError("Staged files missing during rollback")

    backup.rename(target)  # Put original files back.


def commit_staged_mod(
    *,
    mod_id: int,
    staging: Path,
    mods_root: Path,
    state_path: Path,
    remote_modfile: dict,
) -> Path | None:
    """Swap a staged mod into place, updating only its local release metadata.

    Returns the backup path if it could not be removed after commit.
    The game and all servers using this storage must be stopped.
    """
    # The lock covers validation, the initial state read, every rename,
    # publication, rollback, and cleanup. Do not move any part outside it.
    with _commit_lock(state_path):
        return _commit_staged_mod_locked(
            mod_id=mod_id,
            staging=staging,
            mods_root=mods_root,
            state_path=state_path,
            remote_modfile=remote_modfile,
        )


def _commit_staged_mod_locked(
    *,
    mod_id: int,
    staging: Path,
    mods_root: Path,
    state_path: Path,
    remote_modfile: dict,
) -> Path | None:
    target = mods_root / str(mod_id)
    backup = mods_root.parent / f".sandmod-backup-{mod_id}"

    if backup.exists() or _is_link(backup):
        raise InstallError(f"Existing backup requires attention: {backup}")
    if not staging.is_dir() or _is_link(staging):
        raise InstallError("No extracted mod directory to install")
    if not target.is_dir() or _is_link(target):
        raise InstallError(f"Existing installation is missing or unsafe: {target}")
    if not (staging.stat().st_dev == target.stat().st_dev == backup.parent.stat().st_dev):
        raise InstallError("Staging and installation must be on the same filesystem")
    if target.resolve() == staging.resolve():
        raise InstallError("Staging directory is the installation directory")
    if not state_path.is_file():
        raise InstallError(f"State file not found: {state_path}")

    try:
        original = state_path.read_bytes()
        state = json.loads(original.decode("utf-8-sig"))
        mods = state["Mods"]
        entry = None
        for mod in mods:
            if mod["ID"] == mod_id:
                entry = mod
                break
        if entry is None:
            raise InstallError(f"Mod {mod_id} not found in state.json")
        profile = entry["Profile"]
        recorded_path = Path(entry["PathOnDisk"])
        remote_id = remote_modfile["id"]
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        raise InstallError("Invalid or missing local mod metadata") from exc

    if not isinstance(profile, dict):
        raise InstallError("Invalid local mod profile")

    if not recorded_path.is_absolute() or recorded_path.resolve() != target.resolve():
        raise InstallError(f"Unexpected PathOnDisk: {recorded_path}")
    if entry.get("State") != 1:
        raise InstallError("Mod is not in the Installed state (1)")
    if not isinstance(remote_id, int) or remote_modfile.get("mod_id", mod_id) != mod_id:
        raise InstallError("Remote release metadata does not match the mod")

    size_on_disk = 0
    file_count = 0
    for path in staging.rglob("*"):
        if path.is_file():
            size_on_disk += path.stat().st_size
            file_count += 1
    if not file_count:
        raise InstallError("Staged mod has no files")

    profile["modfile"] = remote_modfile
    entry["SizeOnDisk"] = size_on_disk
    updated = json.dumps(state, ensure_ascii=False, indent=2).encode("utf-8")

    fd, temp_name = tempfile.mkstemp(prefix=".sandmod-state-", suffix=".tmp", dir=state_path.parent)
    temp_state = Path(temp_name)
    preserve_temp_state = False
    publication_attempted = False
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(updated)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(temp_state, stat.S_IMODE(state_path.stat().st_mode))

        # Keep the checks against changes by the mod.io SDK or another tool.
        if state_path.read_bytes() != original:
            raise InstallError("state.json changed before install; aborting")

        target.rename(backup)
        staging.rename(target)

        # The mod.io SDK must not be running while this happens.
        if state_path.read_bytes() != original:
            raise InstallError("state.json changed during swap; rolling back")

        # Set this *before* replacement: an interrupt may follow a successful
        # filesystem operation before the following Python statement runs.
        publication_attempted = True
        os.replace(temp_state, state_path)

    except BaseException as exc:
        # Before attempting publication, Sandmod cannot have changed state.json.
        # External SDK edits should abort the install and restore old files.
        publication = _published_state(state_path, original, updated) if publication_attempted else "original"
        if publication == "published":
            # The new state is already visible: never restore old files here.
            # Keep the old files as a recovery backup if interrupted.
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            return backup

        if publication == "uncertain":
            preserve_temp_state = True
            message = (
                "Install outcome uncertain: state.json changed or could not be read. "
                f"Preserve installed files, backup {backup}, and any remaining state draft {temp_state}; "
                "manual recovery may be required"
            )
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                exc.add_note(message)
                raise
            raise InstallError(message) from exc

        try:
            _restore_original_files(target, staging, backup)
        except (OSError, InstallError) as rollback_exc:
            preserve_temp_state = True
            raise InstallError(
                f"Rollback failed. Preserve the existing backup at {backup} "
                f"and state draft {temp_state}; manual recovery may be required: {rollback_exc}"
            ) from exc
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        raise InstallError(f"Install failed; original restored: {exc}") from exc
    finally:
        if not preserve_temp_state:
            temp_state.unlink(missing_ok=True)

    try:
        shutil.rmtree(backup)
    except OSError:
        return backup
    return None
