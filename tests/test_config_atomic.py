"""Configuration overwrites preserve the previous file on failure."""

import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from sandmod.config import (
    GameConfig,
    ModIOConfig,
    _replace_config,
    save_config,
)


class ConfigAtomicTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.config_path = self.root / "sandmod.toml"

    def test_successful_replacement(self):
        self.config_path.write_text("old content", encoding="utf-8")
        _replace_config(self.config_path, "new content")
        self.assertEqual(self.config_path.read_text(encoding="utf-8"), "new content")

    def test_failed_replacement_preserves_original(self):
        original = "[game]\nstorage_root = '/original'\n"
        self.config_path.write_text(original, encoding="utf-8")

        with patch("sandmod.config.os.replace", side_effect=OSError("blocked")):
            with self.assertRaises(OSError):
                _replace_config(self.config_path, "overwritten")

        self.assertEqual(self.config_path.read_text(encoding="utf-8"), original)
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_unicode_storage_path_produces_valid_toml(self):
        path_with_unicode = self.root / "\U0001f680"
        with patch("sandmod.config.get_config_path", return_value=self.config_path):
            save_config(
                ModIOConfig(game_id=254, platform="windows"),
                GameConfig(storage_root=path_with_unicode),
            )

        content = self.config_path.read_text(encoding="utf-8")
        parsed = tomllib.loads(content)
        self.assertEqual(parsed["game"]["storage_root"], str(path_with_unicode))


if __name__ == "__main__":
    unittest.main()
