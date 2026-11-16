from pathlib import Path

from ...quarantine import quarantine_mod, restore_mod


def _display_move(action: str, move) -> None:
    print(f"{action} {move.name} ({move.mod_id}), version {move.version or '-'}")
    print(f"  {move.source} -> {move.destination}")


def sandmod_quarantine(
    game_id: int,
    storage_root: Path,
    mod_id: int,
    dry_run: bool = False,
) -> int:
    preview = quarantine_mod(
        game_id=game_id,
        storage_root=storage_root,
        mod_id=mod_id,
        dry_run=True,
    )

    _display_move("Would quarantine", preview)

    if dry_run:
        return 0

    if input("Confirm Sandstorm/servers are stopped (type YES): ").strip() != "YES":
        print("Cancelled; no mod files moved.")
        return 1

    move = quarantine_mod(
        game_id=game_id,
        storage_root=storage_root,
        mod_id=mod_id,
    )

    _display_move("Quarantined", move)
    print("SDK state.json and mod.io subscriptions were not changed.")
    return 0


def sandmod_restore(
    game_id: int,
    storage_root: Path,
    mod_id: int,
    dry_run: bool = False,
) -> int:
    preview = restore_mod(
        game_id=game_id,
        storage_root=storage_root,
        mod_id=mod_id,
        dry_run=True,
    )

    _display_move("Would restore", preview)

    if dry_run:
        return 0

    if input("Confirm Sandstorm/servers are stopped (type YES): ").strip() != "YES":
        print("Cancelled; no mod files moved.")
        return 1

    move = restore_mod(
        game_id=game_id,
        storage_root=storage_root,
        mod_id=mod_id,
    )

    _display_move("Restored", move)
    print("SDK state.json and mod.io subscriptions were not changed.")
    return 0
