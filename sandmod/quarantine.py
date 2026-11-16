import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .game import get_installation_health, get_mods_path, get_state_path
from .install import InstallError, _commit_lock, _is_link
from .types import ModDictType


@dataclass(frozen=True)
class ModMove:
    mod_id: int
    name: str
    version: str | None
    source: Path
    destination: Path


def _paths(game_id: int, storage_root: Path, mod_id: int):
    if type(mod_id) is not int or mod_id <= 0:
        raise InstallError("Mod ID must be a positive integer")

    mods_root = get_mods_path(game_id, storage_root)
    state_path = get_state_path(game_id, storage_root)

    target = mods_root / str(mod_id)
    quarantine_root = mods_root.parent / ".sandmod-quarantine"
    record_dir = quarantine_root / str(mod_id)

    if not mods_root.is_dir() or _is_link(mods_root):
        raise InstallError(f"Mods directory is missing or unsafe: {mods_root}")

    if _is_link(quarantine_root) or (quarantine_root.exists() and not quarantine_root.is_dir()):
        raise InstallError(f"Quarantine directory is unsafe: {quarantine_root}")

    return state_path, target, quarantine_root, record_dir, record_dir / "content"


def _installed_metadata(state_path: Path, target: Path, mod_id: int):
    try:
        original = state_path.read_bytes()
        data = json.loads(original.decode("utf-8-sig"))

        matches = [mod for mod in data["Mods"] if mod["ID"] == mod_id]

        if len(matches) != 1:
            raise InstallError(f"Expected one local SDK entry for mod {mod_id}; " f"found {len(matches)}")

        mod = matches[0]
        profile = mod.get("Profile") or {}

        name = profile.get("name") or f"Mod {mod_id}"
        version = (profile.get("modfile") or {}).get("version")

    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        raise InstallError(f"Cannot read local SDK entry for mod {mod_id}: {exc}") from exc

    if get_installation_health(mod, target.parent) != "present":
        raise InstallError(f"Mod {mod_id} is not a safe, present installation at {target}")

    if not isinstance(name, str) or (version is not None and not isinstance(version, str)):
        raise InstallError(f"Mod {mod_id} has invalid name or version metadata")

    return original, name, version


def _write_manifest(path: Path, content: dict) -> None:
    fd, temporary_name = tempfile.mkstemp(
        prefix=".manifest-",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(content, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary, path)

    finally:
        temporary.unlink(missing_ok=True)


def quarantine_mod(
    *,
    game_id: int,
    storage_root: Path,
    mod_id: int,
    dry_run: bool = False,
) -> ModMove:

    state_path, target, quarantine_root, record_dir, content = _paths(game_id, storage_root, mod_id)

    if record_dir.exists() or _is_link(record_dir):
        raise InstallError(f"Quarantine record already exists; inspect before proceeding: {record_dir}")

    def perform() -> ModMove:
        original, name, version = _installed_metadata(state_path, target, mod_id)

        move = ModMove(mod_id, name, version, target, content)

        if dry_run:
            return move

        quarantine_root.mkdir(exist_ok=True)

        if record_dir.exists() or _is_link(record_dir):
            raise InstallError(f"Quarantine record appeared while preparing mod {mod_id}")

        if target.stat().st_dev != quarantine_root.stat().st_dev:
            raise InstallError("Quarantine must be on the same filesystem as the mod")

        record_dir.mkdir()
        manifest = record_dir / "manifest.json"

        try:
            _write_manifest(
                manifest,
                {
                    "schema_version": 1,
                    "mod_id": mod_id,
                    "name": name,
                    "version": version,
                    "original_path": str(target),
                    "quarantined_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            if state_path.read_bytes() != original:
                raise InstallError("state.json changed during quarantine; aborting")

            target.rename(content)

        except BaseException as exc:
            # Preserve the manifest if the move has already happened.
            if target.is_dir() and not content.exists() and not _is_link(content):
                try:
                    manifest.unlink(missing_ok=True)
                    record_dir.rmdir()
                except OSError:
                    pass

            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise

            raise InstallError(f"Quarantine interrupted; inspect {target} and {record_dir}: {exc}") from exc

        return move

    if dry_run:
        return perform()

    with _commit_lock(state_path):
        return perform()


def restore_mod(
    *,
    game_id: int,
    storage_root: Path,
    mod_id: int,
    dry_run: bool = False,
) -> ModMove:

    state_path, target, _, record_dir, content = _paths(game_id, storage_root, mod_id)

    def perform() -> ModMove:
        manifest = record_dir / "manifest.json"

        if not record_dir.is_dir() or _is_link(record_dir) or not manifest.is_file() or _is_link(manifest):
            raise InstallError(f"No safe quarantine record found for mod {mod_id}: {record_dir}")

        if not content.is_dir() or _is_link(content):
            raise InstallError(f"Quarantined content is missing or unsafe: {content}")

        if target.exists() or _is_link(target):
            raise InstallError(f"Cannot restore: destination already exists " f"(possibly redownloaded): {target}")

        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            original = Path(data["original_path"])

            if (
                data["schema_version"] != 1
                or type(data["mod_id"]) is not int
                or data["mod_id"] != mod_id
                or not original.is_absolute()
                or original.resolve() != target.resolve()
                or not isinstance(data["name"], str)
                or (data["version"] is not None and not isinstance(data["version"], str))
            ):
                raise InstallError(f"Invalid quarantine manifest for mod {mod_id}")

        except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
            raise InstallError(f"Cannot read quarantine manifest for mod {mod_id}: {exc}") from exc

        move = ModMove(
            mod_id,
            data["name"],
            data["version"],
            content,
            target,
        )

        if dry_run:
            return move

        try:
            content.rename(target)
        except OSError as exc:
            raise InstallError(f"Restore interrupted; inspect {target} and {content}: {exc}") from exc

        try:
            manifest.unlink()
            record_dir.rmdir()
        except OSError as exc:
            raise InstallError(
                f"Files restored to {target}, but quarantine metadata " f"needs manual cleanup: {record_dir} ({exc})"
            ) from exc

        return move

    if dry_run:
        return perform()

    with _commit_lock(state_path):
        return perform()


def get_local_status(mod: ModDictType, mods_root: Path) -> str:
    """Report local status, including valid Sandmod quarantines."""
    health = get_installation_health(mod, mods_root)

    if health != "missing":
        return health

    mod_id = mod.get("ID")

    if type(mod_id) is not int or mod_id <= 0:
        return health

    quarantine_root = mods_root.parent / ".sandmod-quarantine"
    record = quarantine_root / str(mod_id)
    manifest = record / "manifest.json"
    content = record / "content"

    if any(_is_link(path) for path in (mods_root, quarantine_root, record, manifest, content)):
        return health

    if not (record.is_dir() and manifest.is_file() and content.is_dir()):
        return health

    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return health

    if not isinstance(data, dict):
        return health

    original_path = data.get("original_path")

    if not isinstance(original_path, str):
        return health

    try:
        original = Path(original_path)
        matching_path = original.resolve() == (mods_root / str(mod_id)).resolve()
    except (OSError, RuntimeError, ValueError):
        return health

    if (
        type(data.get("schema_version")) is not int
        or data["schema_version"] != 1
        or type(data.get("mod_id")) is not int
        or data["mod_id"] != mod_id
        or not isinstance(data.get("name"), str)
        or (data.get("version") is not None and not isinstance(data["version"], str))
        or not original.is_absolute()
        or not matching_path
    ):
        return health

    return "quarantined"
