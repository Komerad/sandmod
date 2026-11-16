import json
import os
from pathlib import Path

import keyring
from dotenv import dotenv_values, set_key
from keyring.errors import KeyringError

SERVICE = "sandmod"
KEY_NAME = "modio_api_key"


def find_api_key(app_dir: Path) -> tuple[str, str] | None:
    if key := os.environ.get("MODIO_API_KEY"):
        return key, "environment"

    try:
        if key := keyring.get_password(SERVICE, KEY_NAME):
            return key, "keyring"
    except KeyringError:
        pass

    if key := dotenv_values(app_dir / ".env").get("MODIO_API_KEY"):
        return key, "dotenv"

    return None


def get_api_key(app_dir: Path) -> str | None:
    result = find_api_key(app_dir)
    return result[0] if result else None


def save_env_api_key(app_dir: Path, key: str) -> Path:
    if not key or "\n" in key or "\r" in key:
        raise ValueError("Invalid API key")

    path = app_dir / ".env"

    # Create exclusively: never overwrite existing secrets.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)

    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write(f"MODIO_API_KEY={json.dumps(key)}\n")

    return path


def replace_env_api_key(app_dir: Path, key: str) -> Path:
    path = app_dir / ".env"

    if not path.is_file():
        return save_env_api_key(app_dir, key)

    if os.name == "posix":
        path.chmod(0o600)

    set_key(
        str(path),
        "MODIO_API_KEY",
        key,
        quote_mode="always",
    )

    if os.name == "posix":
        path.chmod(0o600)

    return path


def save_keyring_api_key(key: str) -> bool:
    if not key.strip():
        raise ValueError("API key cannot be empty")

    try:
        keyring.set_password(SERVICE, KEY_NAME, key)
        return True
    except KeyringError:
        return False
