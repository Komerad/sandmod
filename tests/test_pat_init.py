import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

from dotenv import dotenv_values

from sandmod.cli.commands.init import (
    _configure_access_token,
    sandmod_init,
)
from sandmod.config import GameConfig, ModIOConfig
from sandmod.credentials import save_env_access_token
from scripts.reset_dev import main as reset_dev


class PATInitTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.config = ModIOConfig(game_id=254, platform="linuxserver")

    def test_pat_is_optional(self):
        with (
            patch("sandmod.cli.commands.init.get_config_path", return_value=self.root / "sandmod.toml"),
            patch("sandmod.cli.commands.init.find_access_token", return_value=None),
            patch("sandmod.cli.commands.init.ask_yes_no", return_value=False),
            patch("sandmod.cli.commands.init.validate_access_token") as validate,
        ):
            self.assertEqual(_configure_access_token(self.config), 0)
            validate.assert_not_called()

    def test_pat_saved_to_keyring(self):
        with (
            patch("sandmod.cli.commands.init.get_config_path", return_value=self.root / "sandmod.toml"),
            patch("sandmod.cli.commands.init.find_access_token", return_value=None),
            patch("sandmod.cli.commands.init.ask_yes_no", return_value=True),
            patch("sandmod.cli.commands.init.getpass", return_value="test-pat"),
            patch("sandmod.cli.commands.init.validate_access_token") as validate,
            patch("sandmod.cli.commands.init.save_keyring_access_token", return_value=True) as save,
        ):
            self.assertEqual(_configure_access_token(self.config), 0)

        validate.assert_called_once_with(254, "test-pat")
        save.assert_called_once_with("test-pat")

    def test_env_fallback_preserves_api_key(self):
        env_path = self.root / ".env"
        env_path.write_text(
            'MODIO_API_KEY="keep-api-key"\nOTHER_SETTING="keep"\n',
            encoding="utf-8",
        )

        save_env_access_token(self.root, "test-pat")

        values = dotenv_values(env_path)
        self.assertEqual(values["MODIO_API_KEY"], "keep-api-key")
        self.assertEqual(values["MODIO_ACCESS_TOKEN"], "test-pat")
        self.assertEqual(values["OTHER_SETTING"], "keep")

    def test_init_runs_both_credential_steps(self):
        config_path = self.root / "sandmod.toml"
        config_path.touch()

        with (
            patch("sandmod.cli.commands.init.get_config_path", return_value=config_path),
            patch("sandmod.cli.commands.init.load_config", return_value=(self.config, GameConfig(self.root))),
            patch("sandmod.cli.commands.init._configure_api_key", return_value=0) as api_setup,
            patch("sandmod.cli.commands.init._configure_access_token", return_value=0) as pat_setup,
        ):
            self.assertEqual(sandmod_init(), 0)

        api_setup.assert_called_once_with(self.config, reauth=False)
        pat_setup.assert_called_once_with(self.config, reauth=False)

    def test_dev_reset_removes_both_credentials(self):
        config_path = self.root / "sandmod.toml"
        config_path.write_text("test", encoding="utf-8")

        env_path = self.root / ".env"
        env_path.write_text(
            'MODIO_API_KEY="api-key"\n' 'MODIO_ACCESS_TOKEN="pat"\n' 'OTHER_SETTING="keep"\n',
            encoding="utf-8",
        )

        with (
            patch("scripts.reset_dev.get_config_path", return_value=config_path),
            patch("builtins.input", return_value="RESET"),
            patch("scripts.reset_dev.keyring.get_password", return_value="stored-secret"),
            patch("scripts.reset_dev.keyring.delete_password") as delete,
        ):
            reset_dev()

        self.assertFalse(config_path.exists())

        values = dotenv_values(env_path)
        self.assertNotIn("MODIO_API_KEY", values)
        self.assertNotIn("MODIO_ACCESS_TOKEN", values)
        self.assertEqual(values["OTHER_SETTING"], "keep")

        self.assertEqual(
            delete.call_args_list,
            [
                call("sandmod", "modio_api_key"),
                call("sandmod", "modio_access_token"),
            ],
        )
