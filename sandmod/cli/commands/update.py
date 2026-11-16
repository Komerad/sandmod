from pathlib import Path
from tempfile import TemporaryDirectory

from ...download import StageError, download_modfile, extract_modfile
from ...game import (
    get_installation_health,
    get_installed_mod,
    get_mods_path,
    get_state_path,
)
from ...install import InstallError, commit_staged_mod
from ...modio import ModIOError, get_mod


def sandmod_update(
    api_key: str,
    game_id: int,
    platform: str,
    storage_root: Path,
    mod_id: int,
    force: bool = False,
) -> int:
    state_path = get_state_path(game_id, storage_root)
    mods_root = get_mods_path(game_id, storage_root)

    if not state_path.is_file() or not mods_root.is_dir():
        print("Sandstorm installation state or mods directory not found.")
        return 1

    try:
        installed = get_installed_mod(state_path, mod_id)
    except KeyError:
        installed = None

    if installed is None:
        print(f"Mod {mod_id} is not registered locally.")
        return 1

    # Verify the local installation before checking remote versions.
    health = get_installation_health(installed, mods_root)

    if health != "present":
        print(f"Cannot update mod {mod_id}: " f"local installation is {health}.")
        print("No files have been modified.")
        return 1

    backup = mods_root.parent / f".sandmod-backup-{mod_id}"
    if backup.exists() or backup.is_symlink():
        print(f"Unresolved backup detected: {backup}")
        print("Inspect or restore it before proceeding.")
        return 1

    try:
        remote = get_mod(game_id, mod_id, api_key, platform)
        if remote.get("id") != mod_id:
            print("Unexpected mod ID returned by mod.io.")
            return 1

        modfile = remote.get("modfile") or {}
        remote_id = modfile.get("id")
        if remote_id is None:
            print(f"No active release for platform {platform}.")
            return 1

        local_file = (installed.get("Profile") or {}).get("modfile") or {}
        if local_file.get("id") == remote_id and not force:
            print(f"{remote.get('name', mod_id)} is already up to date.")
            return 0

        try:
            url = modfile["download"]["binary_url"]
            md5 = modfile["filehash"]["md5"]
            size = modfile["filesize"]
            unpacked_size = modfile["filesize_uncompressed"]

            if (
                not isinstance(url, str)
                or not isinstance(md5, str)
                or type(size) is not int
                or type(unpacked_size) is not int
                or size <= 0
                or unpacked_size <= 0
            ):
                print("mod.io returned invalid download metadata.")
                return 1

        except (KeyError, TypeError):
            print("mod.io did not return complete download metadata.")
            return 1

        print(f"Updating: {remote.get('name', mod_id)}")
        print(f"Installed: {local_file.get('version', '-')}")
        print(f"Available: {modfile.get('version', '-')}")

        with TemporaryDirectory(prefix=".sandmod-", dir=mods_root.parent) as tmp:
            work = Path(tmp)
            archive = work / "download.zip"
            staged = work / "extracted"

            print("Downloading and verifying...")
            download_modfile(url, archive, md5, size)
            print("Extracting...")
            count = extract_modfile(archive, staged, unpacked_size)
            print(f"Verified {count} extracted files.")

            print("\nStop Sandstorm and any servers sharing this mod directory.")
            if input("Type YES when all are stopped (anything else cancels): ").strip() != "YES":
                print("Update cancelled. Installed files unchanged.")
                return 1

            remaining_backup = commit_staged_mod(
                mod_id=mod_id,
                staging=staged,
                mods_root=mods_root,
                state_path=state_path,
                remote_modfile=modfile,
            )

    except (ModIOError, StageError, InstallError, OSError) as exc:
        print(f"Update failed: {exc}")
        return 1

    print("Update installed successfully.")
    if remaining_backup:
        print(f"Warning: old backup could not be deleted: {remaining_backup}")
    return 0
