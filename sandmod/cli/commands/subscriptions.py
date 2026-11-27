from pathlib import Path

from ...game import get_mods_path, get_state_path, load_state
from ...modio import get_subscribed_mods
from ...quarantine import get_local_status
from .quarantine import sandmod_preview_quarantine, sandmod_quarantine_many


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


def sandmod_subscription_cleanup(
    access_token: str,
    game_id: int,
    storage_root: Path,
    dry_run: bool = False,
) -> int:
    state_path = get_state_path(game_id, storage_root)

    if not state_path.is_file():
        print(f"State file not found: {state_path}")
        return 1

    subscribed = get_subscribed_mods(game_id, access_token)
    state = load_state(state_path)
    mods_root = get_mods_path(game_id, storage_root)

    candidates = []

    for mod in state.get("Mods", []):
        mod_id = mod["ID"]

        if mod_id in subscribed:
            continue

        if get_local_status(mod, mods_root) != "present":
            continue

        name = (mod.get("Profile") or {}).get("name") or f"Mod {mod_id}"
        candidates.append((mod_id, name))

    candidates.sort(key=lambda item: item[0])

    print(f"\nLocal-only installed mods: {len(candidates)}")

    if not candidates:
        print("No eligible quarantine candidates found.")
        return 0

    print(f"\n{'#':<5} {'ID':<12} Name")
    print("-" * 56)

    for index, (mod_id, name) in enumerate(candidates, start=1):
        print(f"{index:<5} {mod_id:<12} {name}")

    print("\nThese mods are not subscribed by the PAT account.")
    print("They may still be required by a server or map rotation.")

    selection = input("\nSelect numbers to quarantine (e.g. 1 3 5, Enter to cancel): ").strip()

    if not selection:
        print("Cancelled; no mod files moved.")
        return 1

    try:
        indices = [int(value) for value in selection.replace(",", " ").split()]
    except ValueError:
        print("Invalid selection; enter candidate numbers only.")
        return 1

    if len(indices) != len(set(indices)) or any(index < 1 or index > len(candidates) for index in indices):
        print("Invalid or duplicate selection; no files moved.")
        return 1

    selected_ids = [candidates[index - 1][0] for index in indices]

    if dry_run:
        return sandmod_preview_quarantine(game_id, storage_root, selected_ids)

    return sandmod_quarantine_many(game_id, storage_root, selected_ids)
