import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from sandmod.cli import runner
from sandmod.cli.commands.subscriptions import (
    sandmod_subscription_cleanup,
    sandmod_subscriptions,
)
from sandmod.config import GameConfig, ModIOConfig
from sandmod.game import get_mods_path, get_state_path


class SubscriptionCommandTests(unittest.TestCase):
    def test_lists_subscriptions(self):
        mods = {
            525547: {"id": 525547, "name": "Last Light"},
            391659: {"id": 391659, "name": "Prison_T"},
        }

        output = io.StringIO()

        with patch(
            "sandmod.cli.commands.subscriptions.get_subscribed_mods",
            return_value=mods,
        ) as get_mods:
            with redirect_stdout(output):
                result = sandmod_subscriptions("test-pat", 254)

        self.assertEqual(result, 0)
        get_mods.assert_called_once_with(254, "test-pat")
        self.assertIn("Prison_T", output.getvalue())
        self.assertIn("Last Light", output.getvalue())
        self.assertIn("2", output.getvalue())

    def test_empty_subscriptions(self):
        output = io.StringIO()

        with patch(
            "sandmod.cli.commands.subscriptions.get_subscribed_mods",
            return_value={},
        ):
            with redirect_stdout(output):
                result = sandmod_subscriptions("test-pat", 254)

        self.assertEqual(result, 0)
        self.assertIn("0", output.getvalue())


class SubscriptionDispatchTests(unittest.TestCase):
    def setUp(self):
        self.config = (
            ModIOConfig(game_id=254, platform="linuxserver"),
            GameConfig(storage_root=Path("unused")),
        )

    def test_dispatch_with_pat(self):
        with (
            patch.object(sys, "argv", ["sandmod", "subscriptions"]),
            patch("sandmod.cli.runner.load_config", return_value=self.config),
            patch("sandmod.cli.runner.get_access_token", return_value="test-pat"),
            patch("sandmod.cli.runner.get_api_key") as get_api_key,
            patch(
                "sandmod.cli.runner.sandmod_commands.subscriptions",
                return_value=0,
            ) as command,
        ):
            result = runner._run()

        self.assertEqual(result, 0)
        command.assert_called_once_with("test-pat", 254, None)
        get_api_key.assert_not_called()

    def test_missing_pat_reports_configuration_error(self):
        stderr = io.StringIO()

        with (
            patch.object(sys, "argv", ["sandmod", "subscriptions"]),
            patch("sandmod.cli.runner.load_config", return_value=self.config),
            patch("sandmod.cli.runner.get_access_token", return_value=None),
            redirect_stderr(stderr),
        ):
            with self.assertRaises(SystemExit) as caught:
                runner._run()

        self.assertEqual(caught.exception.code, 2)
        self.assertIn("MODIO_ACCESS_TOKEN", stderr.getvalue())


class SubscriptionComparisonTests(unittest.TestCase):
    def test_comparison_preserves_local_states(self):
        import json
        import tempfile

        from sandmod.game import get_mods_path, get_state_path

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_path = get_state_path(254, root)
            mods_root = get_mods_path(254, root)

            state_path.parent.mkdir(parents=True)
            mods_root.mkdir()
            (mods_root / "100").mkdir()

            def local_mod(mod_id):
                return {
                    "ID": mod_id,
                    "State": 1,
                    "PathOnDisk": str(mods_root / str(mod_id)),
                    "Profile": {"name": f"Local {mod_id}"},
                }

            state_path.write_text(
                json.dumps(
                    {
                        "Mods": [
                            local_mod(100),  # Present
                            local_mod(200),  # Missing
                            local_mod(300),  # Quarantined
                        ]
                    }
                ),
                encoding="utf-8",
            )

            record = mods_root.parent / ".sandmod-quarantine" / "300"
            (record / "content").mkdir(parents=True)
            (record / "manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "mod_id": 300,
                        "name": "Local 300",
                        "version": "1.0",
                        "original_path": str(mods_root / "300"),
                    }
                ),
                encoding="utf-8",
            )

            subscribed = {
                100: {"id": 100, "name": "Remote 100"},
                400: {"id": 400, "name": "Remote 400"},
            }

            output = io.StringIO()
            with patch(
                "sandmod.cli.commands.subscriptions.get_subscribed_mods",
                return_value=subscribed,
            ):
                with redirect_stdout(output):
                    result = sandmod_subscriptions("test-pat", 254, root)

            self.assertEqual(result, 0)

            rows = {}
            for line in output.getvalue().splitlines():
                columns = line.split()
                if columns and columns[0].isdigit():
                    rows[int(columns[0])] = line

            self.assertIn("yes", rows[100])
            self.assertIn("present", rows[100])
            self.assertIn("no", rows[200])
            self.assertIn("missing", rows[200])
            self.assertIn("quarantined", rows[300])
            self.assertIn("not tracked", rows[400])
            self.assertIn("yes", rows[400])


class SubscriptionCleanupTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        self.root = Path(temp.name)
        self.mods_root = get_mods_path(254, self.root)
        self.mods_root.mkdir(parents=True)

        def entry(mod_id):
            return {
                "ID": mod_id,
                "State": 1,
                "PathOnDisk": str(self.mods_root / str(mod_id)),
                "Profile": {"name": f"Mod {mod_id}"},
            }

        # 100 and 400 are present and unsubscribed.
        # 200 is present and subscribed.
        # 300 is unsubscribed but missing.
        for mod_id in (100, 200, 400):
            (self.mods_root / str(mod_id)).mkdir()

        state_path = get_state_path(254, self.root)
        state_path.parent.mkdir(parents=True)
        state_path.write_text(
            json.dumps({"Mods": [entry(i) for i in (100, 200, 300, 400)]}),
            encoding="utf-8",
        )

        self.subscribed = {
            200: {"id": 200, "name": "Subscribed mod"},
        }

    def test_dry_run_only_selects_eligible_mods(self):
        with (
            patch(
                "sandmod.cli.commands.subscriptions.get_subscribed_mods",
                return_value=self.subscribed,
            ),
            patch("builtins.input", return_value="1 2"),
            patch(
                "sandmod.cli.commands.subscriptions.sandmod_preview_quarantine",
                return_value=0,
            ) as preview,
            patch("sandmod.cli.commands.subscriptions.sandmod_quarantine_many") as execute,
        ):
            result = sandmod_subscription_cleanup("test-pat", 254, self.root, dry_run=True)

        self.assertEqual(result, 0)
        preview.assert_called_once_with(254, self.root, [100, 400])
        execute.assert_not_called()

    def test_execution_delegates_to_bulk_quarantine(self):
        with (
            patch(
                "sandmod.cli.commands.subscriptions.get_subscribed_mods",
                return_value=self.subscribed,
            ),
            patch("builtins.input", return_value="1"),
            patch(
                "sandmod.cli.commands.subscriptions.sandmod_quarantine_many",
                return_value=0,
            ) as execute,
        ):
            result = sandmod_subscription_cleanup("test-pat", 254, self.root)

        self.assertEqual(result, 0)
        execute.assert_called_once_with(254, self.root, [100])

    def test_invalid_selection_does_not_execute(self):
        with (
            patch(
                "sandmod.cli.commands.subscriptions.get_subscribed_mods",
                return_value=self.subscribed,
            ),
            patch("builtins.input", return_value="3"),
            patch("sandmod.cli.commands.subscriptions.sandmod_quarantine_many") as execute,
        ):
            result = sandmod_subscription_cleanup("test-pat", 254, self.root)

        self.assertEqual(result, 1)
        execute.assert_not_called()

    def test_no_candidates_requires_no_input(self):
        subscribed = {
            100: {"id": 100},
            200: {"id": 200},
            400: {"id": 400},
        }

        with (
            patch(
                "sandmod.cli.commands.subscriptions.get_subscribed_mods",
                return_value=subscribed,
            ),
            patch("builtins.input") as prompt,
        ):
            result = sandmod_subscription_cleanup("test-pat", 254, self.root)

        self.assertEqual(result, 0)
        prompt.assert_not_called()


if __name__ == "__main__":
    unittest.main()
