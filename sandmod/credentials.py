import json
import os
from pathlib import Path

import keyring
from dotenv import dotenv_values, set_key
from keyring.errors import KeyringError

# ENV
ACCESS_TOKEN_ENV_KEY = "MODIO_ACCESS_TOKEN"
API_KEY_ENV_KEY = "MODIO_API_KEY"
# Keyring
SERVICE = "sandmod"
ACCESS_TOKEN_KEY_NAME = "modio_access_token"
API_KEY_NAME = "modio_api_key"


def _find_credential(
    app_dir: Path,
    env_name: str,
    key_name: str,
) -> tuple[str, str] | None:
    if value := os.environ.get(env_name):
        return value, "environment"

    try:
        if value := keyring.get_password(SERVICE, key_name):
            return value, "keyring"
    except KeyringError:
        pass

    if value := dotenv_values(app_dir / ".env").get(env_name):
        return value, "dotenv"

    return None


def find_api_key(app_dir: Path) -> tuple[str, str] | None:
    return _find_credential(app_dir, API_KEY_ENV_KEY, API_KEY_NAME)


def find_access_token(app_dir: Path) -> tuple[str, str] | None:
    return _find_credential(
        app_dir,
        ACCESS_TOKEN_ENV_KEY,
        ACCESS_TOKEN_KEY_NAME,
    )


def get_api_key(app_dir: Path) -> str | None:
    result = find_api_key(app_dir)
    return result[0] if result else None


def get_access_token(app_dir: Path) -> str | None:
    result = find_access_token(app_dir)
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
        keyring.set_password(SERVICE, API_KEY_NAME, key)
        return True
    except KeyringError:
        return False


def save_keyring_access_token(token: str) -> bool:
    if not token.strip():
        raise ValueError("Access token cannot be empty")

    # Windows Credential Manager limits credential blobs
    # to 2560 bytes. keyring stores them as UTF-16.
    if os.name == "nt" and len(token.encode("utf-16-le")) > 2560:
        return False

    try:
        keyring.set_password(SERVICE, ACCESS_TOKEN_KEY_NAME, token)
        return True
    except KeyringError:
        return False


def save_env_access_token(app_dir: Path, token: str) -> Path:
    if not token.strip() or "\n" in token or "\r" in token:
        raise ValueError("Invalid access token")

    path = app_dir / ".env"

    if not path.exists():
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(path, flags, 0o600)

        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(f"{ACCESS_TOKEN_ENV_KEY}={json.dumps(token)}\n")

        return path

    if os.name == "posix":
        path.chmod(0o600)

    set_key(
        str(path),
        ACCESS_TOKEN_ENV_KEY,
        token,
        quote_mode="always",
    )

    if os.name == "posix":
        path.chmod(0o600)

    return path
