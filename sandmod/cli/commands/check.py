from pathlib import Path

from ...audit import compare_mods
from ...game import get_installed_mod, get_mods_path, get_state_path, load_state
from ...modio import get_mod, get_mods


def sandmod_check(
    api_key: str, game_id: int, platform: str, storage_root: Path, mod_id: int | list[int], check_all: bool = False
) -> int:
    if check_all:
        return __sandmod_check_all(api_key, game_id, platform, storage_root)
    if isinstance(mod_id, int):
        return __sandmod_check_individual(api_key, game_id, platform, storage_root, mod_id)
    # TODO: See about switching nargs => *
    elif isinstance(mod_id, list) and len(mod_id) > 0 and isinstance(mod_id[0], int):
        results = []
        for id in mod_id:
            result = __sandmod_check_individual(api_key, game_id, platform, storage_root, mod_id)
            results.append(result)
        return 1 if any([result == 1 for result in results]) else 0
    # Something went horribly wrong!
    return 1


# TODO: Clean-up
def __sandmod_check_individual(api_key: str, game_id: int, platform: str, storage_root: Path, mod_id: int) -> int:
    state_path = get_state_path(game_id, storage_root)

    if not state_path.is_file():
        print(f"Did not find state file: {state_path}")
        return 1

    installed = get_installed_mod(state_path, mod_id)

    remote = get_mod(game_id, mod_id, api_key, platform)

    if installed is None:
        print(f"{remote['name']}: Not installed")
        return 0

    mod_root = get_mods_path(game_id, storage_root)

    results = compare_mods([installed], {mod_id: remote}, mod_root)

    for result in results:
        # counts[result.status] = counts.get(result.status, 0) + 1

        # print(
        #     f"{result.mod_id:<12} "
        #     f"{result.name[:30]:<31} "
        #     f"{(result.installed_version or '-'):<12} "
        #     f"{(result.available_version or '-'):<12} "
        #     f"{result.status}"
        # )
        print(f"Mod ID: {result.mod_id:<12}")
        print(f"Mod Name: {result.name[:30]:<31}")
        print(f"Installed: {result.installed_version or '-'}")
        print(f"Available: {result.available_version or '-'}")
        print(f"Status: {result.status}")

        # if installed_file_id is None:
        #     print("Status: Unknown local release")
        # elif installed_file_id == remote_file_id:
        #     print("Status: Up to date")
        # else:
        #     print("Status: Update available")

    # remote_file = remote.get("modfile") or {}
    # remote_file_id = remote_file.get("id")

    # if remote_file_id is None:
    #     print(f"No active modfile found for {platform}")
    #     return 1

    # if installed is None:
    #     print(f"{remote['name']}: Not installed")
    #     return 0

    # installed_file = installed.get("Profile", {}).get("modfile", {})

    # installed_file_id = installed_file.get("id")

    # print(f"Mod: {remote['name']}")
    # print(f"Installed: {installed_file.get('version')}")
    # print(f"Available: {remote_file.get('version')}")

    # if installed_file_id is None:
    #     print("Status: Unknown local release")
    # elif installed_file_id == remote_file_id:
    #     print("Status: Up to date")
    # else:
    #     print("Status: Update available")

    return 0


def __sandmod_check_all(
    api_key: str,
    game_id: int,
    platform: str,
    storage_root: Path,
) -> int:
    state_path = get_state_path(game_id, storage_root)
    mods_root = get_mods_path(game_id, storage_root)

    state = load_state(state_path)
    installed = state.get("Mods", [])

    if not installed:
        print("No locally tracked mods found.")
        return 0

    mod_ids = []

    for mod in installed:
        mod_ids.append(mod["ID"])

    print(f"Checking {len(mod_ids)} mods against mod.io...")

    remote = get_mods(
        game_id,
        mod_ids,
        api_key,
        platform,
    )

    results = compare_mods(installed, remote, mods_root)

    counts = {}

    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1

        print(
            f"{result.mod_id:<12} "
            f"{result.name[:30]:<31} "
            f"{(result.installed_version or '-'):<12} "
            f"{(result.available_version or '-'):<12} "
            f"{result.status}"
        )

    print(f"\nTotal: {len(results)}")
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")

    return 0
