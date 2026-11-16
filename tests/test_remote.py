"""A mod may exist without an active file for the requested platform."""

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from sandmod.cli.commands.remote import sandmod_remote


class RemoteCommandTests(unittest.TestCase):
    def test_no_active_platform_release(self):
        mod = {"id": 42, "name": "Example Mod", "modfile": None}
        output = io.StringIO()

        with patch("sandmod.cli.commands.remote.get_mod", return_value=mod):
            with redirect_stdout(output):
                result = sandmod_remote("unused", 254, "linuxserver", 42)

        self.assertEqual(result, 1)
        self.assertIn("No active release", output.getvalue())
        self.assertIn("linuxserver", output.getvalue())

    def test_active_release_displays_modfile(self):
        mod = {
            "id": 42,
            "name": "Example Mod",
            "modfile": {"id": 101, "version": "1.2"},
        }
        output = io.StringIO()

        with patch("sandmod.cli.commands.remote.get_mod", return_value=mod):
            with redirect_stdout(output):
                result = sandmod_remote("unused", 254, "windows", 42)

        self.assertEqual(result, 0)
        self.assertIn("101", output.getvalue())
        self.assertIn("1.2", output.getvalue())


if __name__ == "__main__":
    unittest.main()
