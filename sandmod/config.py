import json
import os
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path

PLATFORMS = {
    "windows",
    "linux",
    "windowsserver",
    "linuxserver",
}


@dataclass(frozen=True)
class ModIOConfig:
    game_id: int
    platform: str


@dataclass(frozen=True)
class GameConfig:
    storage_root: Path


def get_config_path() -> Path:
    if getattr(sys, "frozen", False):
        root = Path(sys.executable).resolve().parent
    else:
        root = Path(__file__).resolve().parent.parent

    return root / "sandmod.toml"


def load_config() -> tuple[ModIOConfig, GameConfig]:
    path = get_config_path()

    if not path.is_file():
        raise FileNotFoundError(f"Configuration not found: {path}. Run 'sandmod init'.")

    with path.open("rb") as file:
        data = tomllib.load(file)

    game_settings = data["game"]
    modio_settings = data["modio"]

    root = Path(game_settings["storage_root"]).expanduser()
    platform = modio_settings["platform"]
    game_id = modio_settings["game_id"]

    if platform not in PLATFORMS:
        raise ValueError(f"Unsupported platform: {platform}")

    game_config = GameConfig(storage_root=root)
    modio_config = ModIOConfig(game_id=game_id, platform=platform)

    return (modio_config, game_config)


def __get_config_content(modio_config: ModIOConfig, game_config: GameConfig):
    return (
        "[modio]\n"
        f"game_id = {json.dumps(modio_config.game_id)}\n"
        f"platform = {json.dumps(modio_config.platform)}\n"
        "\n"
        "[game]\n"
        f"storage_root = {json.dumps(str(game_config.storage_root), ensure_ascii=False)}\n"
    )


def save_config(modio_config: ModIOConfig, game_config: GameConfig) -> Path:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    content = __get_config_content(modio_config, game_config)

    # Verify that our generated content is valid TOML.
    tomllib.loads(content)

    # Exclusive creation: don't silently overwrite existing settings.
    with path.open("x", encoding="utf-8") as file:
        file.write(content)

    return path


def replace_config(modio_config: ModIOConfig, game_config: GameConfig) -> Path:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    content = __get_config_content(modio_config, game_config)

    # Verify that our generated content is valid TOML.
    tomllib.loads(content)

    _replace_config(path, content)

    return path


def _replace_config(path: Path, content: str) -> None:
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temp_path = Path(file.name)
            file.write(content)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temp_path, path)

    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
