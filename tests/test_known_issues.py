import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from sandmod.cli.commands.issues import print_issue_warning
from sandmod.cli.runner import _run
from sandmod.known_issues import match_known_issue


class KnownIssuesTests(unittest.TestCase):
    def test_matches_exact_version(self):
        issue = match_known_issue(448415, "1.9")

        self.assertIsNotNone(issue)
        self.assertEqual(issue.observed_on, "2026-11-15")

    def test_does_not_match_other_versions(self):
        self.assertIsNone(match_known_issue(448415, "2.0"))
        self.assertIsNone(match_known_issue(448415, None))
        self.assertIsNone(match_known_issue(123, "1.9"))

    def test_unaffected_version_produces_no_warning(self):
        output = io.StringIO()

        with redirect_stdout(output):
            print_issue_warning(448415, "2.0")

        self.assertEqual(output.getvalue(), "")

    def test_issues_command_requires_no_configuration(self):
        output = io.StringIO()

        with (
            patch("sys.argv", ["sandmod", "issues", "448415"]),
            patch("sandmod.cli.runner.load_config") as load_config,
            redirect_stdout(output),
        ):
            self.assertEqual(_run(), 0)

        load_config.assert_not_called()
        self.assertIn("Mud Village", output.getvalue())
