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
