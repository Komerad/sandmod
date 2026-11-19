from pathlib import Path

from ...game import get_mods_path, get_state_path, load_state
from ...modio import get_subscribed_mods
from ...quarantine import get_local_status


def sandmod_subscriptions(
    access_token: str,
    game_id: int,
    storage_root: Path | None = None,
) -> int:
    mods = get_subscribed_mods(game_id, access_token)

    if storage_root is not None:
        return _compare_subscriptions(game_id, storage_root, mods)

    print(f"\nSubscribed mods (PAT account, game {game_id}): {len(mods)}")

    if not mods:
        return 0

    print(f"\n{'ID':<12} Name")
    print("-" * 56)

    for mod_id in sorted(mods):
        name = mods[mod_id].get("name") or "Unknown"
        print(f"{mod_id:<12} {name}")

    return 0


def _compare_subscriptions(
    game_id: int,
    storage_root: Path,
    subscribed: dict[int, dict],
) -> int:
    state_path = get_state_path(game_id, storage_root)

    if not state_path.is_file():
        print(f"State file not found: {state_path}")
        return 1

    state = load_state(state_path)
    local_mods = {mod["ID"]: mod for mod in state.get("Mods", [])}
    mods_root = get_mods_path(game_id, storage_root)

    print(f"\nSubscribed: {len(subscribed)} | " f"Locally tracked: {len(local_mods)}\n")
    print(f"{'ID':<12} {'Name':<36} {'Subscribed':<12} Local")
    print("-" * 76)

    all_ids = set(local_mods) | set(subscribed)

    # Show local-only records first for easier cleanup review.
    for mod_id in sorted(all_ids, key=lambda mid: (mid in subscribed, mid)):
        local_mod = local_mods.get(mod_id)
        remote_mod = subscribed.get(mod_id)

        name = (remote_mod or {}).get("name")
        if not name and local_mod is not None:
            name = (local_mod.get("Profile") or {}).get("name")
        name = name or "Unknown"

        subscription = "yes" if mod_id in subscribed else "no"
        local = get_local_status(local_mod, mods_root) if local_mod is not None else "not tracked"

        print(f"{mod_id:<12} " f"{name[:35]:<36} " f"{subscription:<12} " f"{local}")

    return 0
