import sys
from pathlib import Path

from ...install import InstallError
from ...quarantine import quarantine_mod, restore_mod


def _display_move(action: str, move) -> None:
    print(f"{action} {move.name} ({move.mod_id}), version {move.version or '-'}")
    print(f"  {move.source} -> {move.destination}")


def sandmod_preview_quarantine(
    game_id: int,
    storage_root: Path,
    mod_ids: list[int],
) -> int:
    if len(mod_ids) != len(set(mod_ids)):
        raise InstallError("Duplicate mod IDs in quarantine selection")

    moves = []

    # Validate the entire selection before displaying results.
    for mod_id in mod_ids:
        move = quarantine_mod(
            game_id=game_id,
            storage_root=storage_root,
            mod_id=mod_id,
            dry_run=True,
        )
        moves.append(move)

    for move in moves:
        _display_move("Would quarantine", move)

    print(f"\nPreviewed {len(moves)} mods; no files moved.")
    return 0


def sandmod_quarantine_many(
    game_id: int,
    storage_root: Path,
    mod_ids: list[int],
) -> int:
    # Validate and preview the complete selection.
    sandmod_preview_quarantine(game_id, storage_root, mod_ids)

    if input("Confirm Sandstorm/servers are stopped and " "quarantine all selected mods (type YES): ").strip() != "YES":
        print("Cancelled; no mod files moved.")
        return 1

    completed = 0

    for mod_id in mod_ids:
        try:
            move = quarantine_mod(
                game_id=game_id,
                storage_root=storage_root,
                mod_id=mod_id,
            )
        except (InstallError, OSError) as exc:
            print(
                f"Quarantine failed for mod {mod_id}: {exc}",
                file=sys.stderr,
            )
            print(
                f"Completed {completed} of {len(mod_ids)} quarantines. " "Later mods were not attempted.",
                file=sys.stderr,
            )
            print(
                "Completed moves were not rolled back. " "Inspect the failing mod before retrying.",
                file=sys.stderr,
            )
            return 1

        _display_move("Quarantined", move)
        completed += 1

    print(f"\nSuccessfully quarantined {completed} mods.")
    print("SDK state.json and mod.io subscriptions were not changed.")
    return 0


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
