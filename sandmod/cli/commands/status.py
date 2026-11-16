from pathlib import Path

from ...game import get_installed_mod, get_mods_path, get_state_path
from ...quarantine import get_local_status
from ...types import ModProfileType


def sandmod_status(game_id: int, storage_root: Path, mod_id: int) -> int:
    state_path = get_state_path(game_id, storage_root)

    if not state_path.is_file():
        print(f"Did not find state file: {state_path}")
        return 1

    mod = get_installed_mod(state_path, mod_id)

    if mod is None:
        print(f"Mod {mod_id} not found")
        return 1

    profile: ModProfileType = mod.get("Profile", {})
    modfile = profile.get("modfile", {})

    print("Mod ID:", mod.get("ID"))
    print("Name:", profile.get("name"))
    print("Modfile ID:", modfile.get("id"))
    print("Version:", modfile.get("version"))
    print("Path:", mod.get("PathOnDisk"))
    print("State:", mod.get("State"))
    print(
        "Local Status:",
        get_local_status(mod, get_mods_path(game_id, storage_root)),
    )

    return 0
