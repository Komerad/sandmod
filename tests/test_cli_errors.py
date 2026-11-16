"""The CLI handles expected failures but does not mask coding errors."""

import io
import unittest
from contextlib import redirect_stderr
from json import JSONDecodeError
from unittest.mock import patch

from sandmod.cli import runner
from sandmod.download import StageError
from sandmod.install import InstallError
from sandmod.modio import ModIOError


class CLIErrorTests(unittest.TestCase):
    def run_with_error(self, error):
        stderr = io.StringIO()
        with patch("sandmod.cli.runner._run", side_effect=error):
            with redirect_stderr(stderr):
                status = runner.main()
        return status, stderr.getvalue()

    def test_application_errors_have_clean_messages(self):
        errors = (
            ModIOError("mod.io returned HTTP 503", status_code=503),
            StageError("Archive checksum failed"),
            InstallError("Existing backup requires attention"),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__):
                status, output = self.run_with_error(error)
                self.assertEqual(status, 1)
                self.assertIn(str(error), output)
                self.assertNotIn("Traceback", output)

    def test_missing_file_is_reported(self):
        status, output = self.run_with_error(FileNotFoundError("Configuration missing. Run sandmod init"))
        self.assertEqual(status, 1)
        self.assertIn("sandmod init", output)

    def test_malformed_json_is_reported(self):
        error = JSONDecodeError("Invalid JSON", "{", 1)
        status, output = self.run_with_error(error)
        self.assertEqual(status, 1)
        self.assertIn("invalid", output.lower())

    def test_unexpected_programming_errors_still_raise(self):
        with patch("sandmod.cli.runner._run", side_effect=TypeError("real bug")):
            with self.assertRaisesRegex(TypeError, "real bug"):
                runner.main()

    def test_success_returns_dispatch_status(self):
        with patch("sandmod.cli.runner._run", return_value=0):
            self.assertEqual(runner.main(), 0)


if __name__ == "__main__":
    unittest.main()
