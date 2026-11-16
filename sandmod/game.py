import json
from pathlib import Path
from typing import Literal

from .types import ModDictType, StateDictType

InstallationHealth = Literal["present", "missing", "unknown"]


def get_state_path(game_id: int, storage_root: Path) -> Path:
    return storage_root / str(game_id) / "metadata" / "state.json"


def get_mods_path(game_id: int, storage_root: Path) -> Path:
    return storage_root / str(game_id) / "mods"


def load_state(state_path: Path) -> StateDictType:
    with state_path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def get_installed_mod(
    state_path: Path,
    mod_id: int,
) -> ModDictType | None:
    state = load_state(state_path)

    for mod in state.get("Mods", []):
        if mod["ID"] == mod_id:
            return mod

    return None


def get_installation_health(
    mod: ModDictType,
    mods_root: Path,
) -> InstallationHealth:
    if mod.get("State") != 1:
        return "unknown"

    mod_id = mod.get("ID")
    recorded_path = mod.get("PathOnDisk")

    if not isinstance(mod_id, int) or not isinstance(recorded_path, str):
        return "unknown"

    expected = mods_root / str(mod_id)
    recorded = Path(recorded_path)

    if not recorded.is_absolute() or recorded.resolve() != expected.resolve():
        return "unknown"

    if expected.is_symlink() or getattr(expected, "is_junction", lambda: False)():
        return "unknown"

    if not expected.is_dir():
        return "missing"

    return "present"


# def get_installation_health(
#     mod: ModDictType,
#     mods_root: Path,
# ) -> InstallationHealth:

#     if mod.get("ID") == 4278920:
#         print("DEBUG State:", repr(mod.get("State")))
#         print("DEBUG ID:", repr(mod.get("ID")))
#         print("DEBUG mods_root:", mods_root)
#         print("DEBUG directory:", mods_root / str(mod["ID"]))
#         print("DEBUG exists:", (mods_root / str(mod["ID"])).is_dir())

#     if mod.get("State") != 1:
#         return "unknown"

#     mod_id = mod.get("ID")

#     if not isinstance(mod_id, int):
#         return "unknown"

#     path = mods_root / str(mod_id)

#     if not path.is_dir():
#         return "missing"

#     return "present"
