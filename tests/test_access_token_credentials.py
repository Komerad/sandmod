import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sandmod.credentials import get_access_token, get_api_key, save_keyring_access_token


class AccessTokenCredentialTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        self.app_dir = Path(temp.name)
        (self.app_dir / ".env").write_text(
            'MODIO_API_KEY="dotenv-key"\n' 'MODIO_ACCESS_TOKEN="dotenv-pat"\n',
            encoding="utf-8",
        )

    def test_environment_takes_precedence(self):
        with patch.dict(os.environ, {"MODIO_ACCESS_TOKEN": "env-pat"}, clear=True):
            with patch("sandmod.credentials.keyring.get_password") as keyring_get:
                self.assertEqual(get_access_token(self.app_dir), "env-pat")
                keyring_get.assert_not_called()

    def test_keyring_precedes_dotenv(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "sandmod.credentials.keyring.get_password",
                return_value="keyring-pat",
            ) as keyring_get:
                self.assertEqual(get_access_token(self.app_dir), "keyring-pat")
                keyring_get.assert_called_once_with("sandmod", "modio_access_token")

    def test_dotenv_fallback(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "sandmod.credentials.keyring.get_password",
                return_value=None,
            ):
                self.assertEqual(get_access_token(self.app_dir), "dotenv-pat")

    def test_existing_api_key_lookup_unchanged(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "sandmod.credentials.keyring.get_password",
                return_value=None,
            ):
                self.assertEqual(get_api_key(self.app_dir), "dotenv-key")

    def test_oversized_windows_pat_skips_keyring(self):
        token = "x" * 1281

        with (
            patch("sandmod.credentials.os.name", "nt"),
            patch("sandmod.credentials.keyring.set_password") as save,
        ):
            result = save_keyring_access_token(token)

        self.assertFalse(result)
        save.assert_not_called()

    def test_windows_pat_within_limit_uses_keyring(self):
        token = "x" * 1280

        with (
            patch("sandmod.credentials.os.name", "nt"),
            patch("sandmod.credentials.keyring.set_password") as save,
        ):
            result = save_keyring_access_token(token)

        self.assertTrue(result)
        save.assert_called_once_with(
            "sandmod",
            "modio_access_token",
            token,
        )
