import keyring
from dotenv import dotenv_values, unset_key
from keyring.errors import KeyringError

from sandmod.config import get_config_path
from sandmod.credentials import (
    ACCESS_TOKEN_ENV_KEY,
    ACCESS_TOKEN_KEY_NAME,
    API_KEY_ENV_KEY,
    API_KEY_NAME,
    SERVICE,
)


def main() -> None:
    config_path = get_config_path()
    env_path = config_path.parent / ".env"

    print("Resetting Sandmod development configuration")
    print(f"Config: {config_path}")
    print(f"Environment file: {env_path}")

    if input("Type RESET to continue: ") != "RESET":
        return

    # Application configuration
    config_path.unlink(missing_ok=True)

    # Remove Sandmod credentials, preserving unrelated .env entries.
    if env_path.is_file():
        existing_keys = dotenv_values(env_path)

        for env_key in (API_KEY_ENV_KEY, ACCESS_TOKEN_ENV_KEY):
            if env_key in existing_keys:
                unset_key(str(env_path), env_key)

        if not env_path.read_text(encoding="utf-8").strip():
            env_path.unlink()

    # Remove both credentials from the OS credential store.
    for key_name in (API_KEY_NAME, ACCESS_TOKEN_KEY_NAME):
        try:
            if keyring.get_password(SERVICE, key_name) is None:
                continue

            keyring.delete_password(SERVICE, key_name)
            print(f"Keyring credential removed: {key_name}")
        except KeyringError as exc:
            print(f"Could not clear {key_name}: {exc}")

    print("Local configuration reset.")
    print("Check that MODIO_API_KEY and MODIO_ACCESS_TOKEN")
    print("are unset in your shell.")


if __name__ == "__main__":
    main()
