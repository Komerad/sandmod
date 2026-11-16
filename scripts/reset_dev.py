import keyring
from dotenv import unset_key
from keyring.errors import KeyringError

from sandmod.config import get_config_path
from sandmod.credentials import KEY_NAME, SERVICE


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

    # Remove only our key, preserving other .env entries
    if env_path.is_file():
        unset_key(str(env_path), "MODIO_API_KEY")

        if not env_path.read_text(encoding="utf-8").strip():
            env_path.unlink()

    # OS credential store
    try:
        keyring.delete_password(SERVICE, KEY_NAME)
        print("Keyring credential removed.")
    except KeyringError as exc:
        print(f"Keyring could not be cleared: {exc}")

    print("Local configuration reset.")
    print("Check that MODIO_API_KEY is unset in your shell.")


if __name__ == "__main__":
    main()
