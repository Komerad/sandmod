from pathlib import Path

from ...game import get_state_path, load_state


def sandmod_list(game_id: int, storage_root: Path) -> int:
    state_path = get_state_path(game_id, storage_root)

    if not state_path.is_file():
        print(f"State file not found: {state_path}")
        return 1

    state = load_state(state_path)
    mods = state.get("Mods", [])

    print(f"\nLocally tracked mods: {len(mods)}\n")
    print(f"{'ID':<12} {'Name':<36} {'Version':<14} {'State'}")
    print("-" * 75)

    for mod in mods:
        profile = mod.get("Profile") or {}
        modfile = profile.get("modfile") or {}

        mod_id = mod["ID"]
        name = profile.get("name", "Unknown")
        version = modfile.get("version") or "-"
        install_state = mod.get("State", "-")

        print(f"{mod_id:<12} " f"{name[:35]:<36} " f"{version:<14} " f"{install_state}")

    return 0
