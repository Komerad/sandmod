from ...modio import get_mod


def sandmod_remote(api_key: str, game_id: int, platform: str, mod_id: int) -> int:
    mod = get_mod(
        game_id,
        mod_id,
        api_key,
        platform,
    )

    modfile = mod.get("modfile", {})

    if not isinstance(modfile, dict):
        print(f"No active release available for platform {platform}.")
        return 1

    print("Mod:", mod.get("name"))
    print("Mod ID:", mod.get("id"))
    print("Active modfile ID:", modfile.get("id"))
    print("Version:", modfile.get("version"))

    return 0
