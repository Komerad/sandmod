import os
from getpass import getpass
from pathlib import Path

from ...config import (
    PLATFORMS,
    GameConfig,
    ModIOConfig,
    get_config_path,
    load_config,
    replace_config,
    save_config,
)
from ...credentials import (
    find_access_token,
    find_api_key,
    replace_env_api_key,
    save_env_access_token,
    save_env_api_key,
    save_keyring_access_token,
    save_keyring_api_key,
)
from ...game import get_state_path
from ...modio import ModIOError, validate_access_token, validate_api_key


def __print_banner() -> None:
    print(r"""
  ____                  _                     _
 / ___|  __ _ _ __   __| |_ __ ___   ___   __| |
 \___ \ / _` | '_ \ / _` | '_ ` _ \ / _ \ / _` |
  ___) | (_| | | | | (_| | | | | | | | (_) | (_| |
 |____/ \__,_|_| |_|\__,_|_| |_| |_|\___/ \__,_|

                 S E T U P
  ---------------------------------------------
  Insurgency: Sandstorm Mod Manager
    """)


def __print_setup_complete() -> None:
    print(r"""
  -------------------------------------------------
                  SETUP COMPLETE
  -------------------------------------------------

       All systems go. The mods await.

             Happy trails, partner!

  -------------------------------------------------
    """)


def __spacing_please():
    print("\n")


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"

    while True:
        answer = input(f"{prompt} {suffix}: ").strip().lower()

        if not answer:
            return default

        if answer in ("y", "yes"):
            return True

        if answer in ("n", "no"):
            return False

        print("Please enter yes or no.")


def _configure_api_key(config: ModIOConfig, reauth: bool = False) -> int:
    app_dir = get_config_path().parent

    existing = find_api_key(app_dir)
    source = existing[1] if existing else None

    if source == "environment" and reauth:
        print("MODIO_API_KEY is set in the environment.")
        print("Update or unset it before replacing stored credentials.")
        return 1

    if existing and not reauth:
        try:
            validate_api_key(
                config.game_id,
                existing[0],
                config.platform,
            )
        except ModIOError as exc:
            if exc.status_code not in (401, 403):
                print(f"Could not verify credentials: {exc}")
                return 1

            print("Existing API key was rejected.")

            if source == "environment":
                print("Update or unset MODIO_API_KEY.")
                return 1

            if not ask_yes_no("Replace API key?", default=True):
                return 1
        else:
            print(f"mod.io credentials verified. Source: {source}")
            return 0

    # Prompt until a valid replacement key is supplied.
    while True:
        print("Get your API key at:\nhttps://mod.io/me/access")
        __spacing_please()

        key = getpass("mod.io API key (Enter to cancel): ").strip()

        if not key:
            return 1

        try:
            __spacing_please()
            print("Validating credentials...")
            validate_api_key(
                config.game_id,
                key,
                config.platform,
            )
        except ModIOError as exc:
            print(f"Validation failed: {exc}")

            if exc.status_code in (401, 403):
                continue

            # A remote-service problem is not a bad credential.
            return 1

        break

    print("API key accepted")
    __spacing_please()

    if save_keyring_api_key(key):
        print("API key saved to the OS credential store.")
        return 0

    print("No supported credential store is available.")
    print("The fallback stores your API key in plaintext.")
    print("Restrict access to your Sandmod directory.")
    __spacing_please()

    if not ask_yes_no("Save to local .env?", default=False):
        return 1
    if reauth:
        try:
            path = replace_env_api_key(app_dir, key)
        except OSError as exc:
            print(f"Could not save credential file: {exc}")
            return 1
    else:
        try:
            path = save_env_api_key(app_dir, key)
        except FileExistsError:
            print("A .env file already exists; it was not overwritten.")
            print("Update the existing key manually or use a keyring.")
            return 1
        except OSError as exc:
            print(f"Could not save credential file: {exc}")
            return 1

    print(f"API key saved to {path}")
    return 0


def _configure_access_token(config: ModIOConfig, reauth: bool = False) -> int:
    app_dir = get_config_path().parent
    existing = find_access_token(app_dir)
    source = existing[1] if existing else None

    if existing and not reauth:
        try:
            validate_access_token(config.game_id, existing[0])
        except ModIOError as exc:
            if exc.status_code not in (401, 403):
                print(f"Could not verify PAT: {exc}")
                return 1

            print("Existing Personal Access Token was rejected.")

            if source == "environment":
                print("Update or unset MODIO_ACCESS_TOKEN.")
                return 1

            if not ask_yes_no("Replace PAT?", default=True):
                return 1
        else:
            print(f"mod.io PAT verified. Source: {source}")
            return 0

    elif existing and reauth:
        if not ask_yes_no("Replace existing PAT?", default=False):
            return 0

        if source == "environment":
            print("MODIO_ACCESS_TOKEN is set in the environment.")
            print("Update or unset it before replacing stored credentials.")
            return 1

    elif not ask_yes_no(
        "Configure a mod.io PAT for subscription discovery?",
        default=False,
    ):
        return 0

    while True:
        print("Create a read-only Personal Access Token at:")
        print("https://mod.io/me/access")

        token = getpass("mod.io PAT (Enter to cancel): ").strip()
        if not token:
            return 1

        try:
            print("Validating PAT...")
            validate_access_token(config.game_id, token)
        except ModIOError as exc:
            print(f"Validation failed: {exc}")

            if exc.status_code in (401, 403):
                continue

            return 1

        break

    print("Personal Access Token accepted.")

    if save_keyring_access_token(token):
        print("PAT saved to the OS credential store.")
        return 0

    print("Could not save PAT to the OS credential store.")
    print("Windows Credential Manager cannot store oversized credentials.")
    print("The fallback stores your PAT in plaintext.")
    print("Restrict access to your Sandmod directory.")

    if not ask_yes_no("Save PAT to local .env?", default=False):
        return 1

    try:
        path = save_env_access_token(app_dir, token)
    except (OSError, ValueError) as exc:
        print(f"Could not save PAT: {exc}")
        return 1

    print(f"PAT saved to {path}")
    return 0


def _configure_settings(reconfigure: bool = False):
    default_platform = "windows" if os.name == "nt" else "linuxserver"

    while True:
        platform = input(f"Platform [{default_platform}]: ").strip() or default_platform

        if platform in PLATFORMS:
            break

        print(f"Invalid platform: {platform}")
        print(f"Valid options: {', '.join(sorted(PLATFORMS))}")

    default_game_id = "254"

    while True:
        game_id = input(f"game_id[{default_game_id}]: ").strip() or default_game_id

        if game_id.isnumeric():
            break

        print(f"Invalid game id: {game_id}")
        print("Game id must be numeric")

    default_root = "C:\\Users\\Public\\mod.io" if platform == "windows" else "/home/sandstorm/steamcmd/mod.io/common"

    while True:
        root = input(f"mod.io storage root[{default_root}]: ").strip() or default_root

        state_path = get_state_path(int(game_id), Path(root).expanduser())
        if root and state_path.is_file():
            break

        print(f"Invalid root, or state file not found at: {root}")
        print("Ensure the supplied directory contains state.json.")
        print(f"The full path checked was: {state_path}")

    modio_config = ModIOConfig(game_id=int(game_id), platform=platform)
    game_config = GameConfig(storage_root=Path(root).expanduser())

    state_path = get_state_path(modio_config.game_id, game_config.storage_root)

    if reconfigure:
        if not ask_yes_no("Are you sure you wish to overwrite the current config?", default=False):
            return 1
        path = replace_config(modio_config, game_config)
    else:
        try:
            path = save_config(modio_config, game_config)
        except FileExistsError:
            print(f"Configuration file already exists.")
            return 1

    verb = "updated" if reconfigure else "created"

    __spacing_please()
    print(f"Configuration {verb}: {path}")
    __spacing_please()

    return 0


def sandmod_init(
    reconfigure: bool = False,
    reauth: bool = False,
) -> int:
    config_path = get_config_path()

    __print_banner()
    __spacing_please()

    if not config_path.exists() or reconfigure:
        ui_state = "Reconfiguring existing config." if reconfigure else "No configuration found."

        print(ui_state)
        __spacing_please()

        # TODO: Support current settings as defaults.
        # Allow replacing config only when reconfigure=True.
        result = _configure_settings(reconfigure)

        if result != 0:
            return result

    modio_config, game_config = load_config()

    print(f"Using configuration: {config_path}")
    print(f"Platform: {modio_config.platform}")
    print(f"Game ID: {modio_config.game_id}")
    print(f"Storage: {game_config.storage_root}")

    __spacing_please()

    credential_result = _configure_api_key(
        modio_config,
        reauth=reauth,
    )
    if credential_result != 0:
        return credential_result

    pat_result = _configure_access_token(
        modio_config,
        reauth=reauth,
    )
    if pat_result != 0:
        return pat_result

    __spacing_please()
    __print_setup_complete()

    return 0
