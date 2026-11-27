import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from sandmod.cli import runner
from sandmod.cli.commands.quarantine import (
    sandmod_preview_quarantine,
    sandmod_quarantine_many,
)
from sandmod.config import GameConfig, ModIOConfig
from sandmod.game import get_mods_path, get_state_path
from sandmod.install import InstallError


class BulkQuarantinePreviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        self.root = Path(temp.name)
        self.mods = get_mods_path(254, self.root)
        self.mods.mkdir(parents=True)

        self.ids = [391659, 525547]
        entries = []

        for mod_id in self.ids:
            target = self.mods / str(mod_id)
            target.mkdir()
            (target / "test.pak").write_bytes(b"test content")

            entries.append(
                {
                    "ID": mod_id,
                    "State": 1,
                    "PathOnDisk": str(target),
                    "Profile": {
                        "name": f"Mod {mod_id}",
                        "modfile": {"version": "1.0"},
                    },
                }
            )

        self.state = get_state_path(254, self.root)
        self.state.parent.mkdir(parents=True)
        self.state.write_text(
            json.dumps({"Mods": entries}),
            encoding="utf-8",
        )
        self.original_state = self.state.read_bytes()

    def test_bulk_preview_does_not_move_files(self):
        output = io.StringIO()

        with redirect_stdout(output):
            result = sandmod_preview_quarantine(254, self.root, self.ids)

        self.assertEqual(result, 0)
        self.assertIn("Previewed 2 mods", output.getvalue())

        for mod_id in self.ids:
            self.assertTrue((self.mods / str(mod_id) / "test.pak").is_file())

        self.assertEqual(self.state.read_bytes(), self.original_state)
        self.assertFalse((self.mods.parent / ".sandmod-quarantine").exists())

    def test_invalid_selection_fails_without_partial_preview(self):
        output = io.StringIO()

        with redirect_stdout(output):
            with self.assertRaises(InstallError):
                sandmod_preview_quarantine(254, self.root, [391659, 999999])

        self.assertNotIn("Would quarantine", output.getvalue())
        self.assertTrue((self.mods / "391659").is_dir())

    def test_duplicate_ids_are_rejected(self):
        with self.assertRaises(InstallError):
            sandmod_preview_quarantine(254, self.root, [391659, 391659])

    def test_bulk_execution_moves_all_mods(self):
        output = io.StringIO()

        with (
            patch("builtins.input", return_value="YES"),
            redirect_stdout(output),
        ):
            result = sandmod_quarantine_many(254, self.root, self.ids)

        self.assertEqual(result, 0)

        for mod_id in self.ids:
            self.assertFalse((self.mods / str(mod_id)).exists())

            record = self.mods.parent / ".sandmod-quarantine" / str(mod_id)
            self.assertTrue((record / "content" / "test.pak").is_file())
            self.assertTrue((record / "manifest.json").is_file())

        self.assertEqual(self.state.read_bytes(), self.original_state)
        self.assertIn("Successfully quarantined 2 mods", output.getvalue())

    def test_bulk_execution_can_be_cancelled(self):
        with patch("builtins.input", return_value="NO"):
            result = sandmod_quarantine_many(254, self.root, self.ids)

        self.assertEqual(result, 1)

        for mod_id in self.ids:
            self.assertTrue((self.mods / str(mod_id)).is_dir())

        self.assertEqual(self.state.read_bytes(), self.original_state)

    def test_bulk_stops_after_failed_move(self):
        from sandmod.quarantine import quarantine_mod as real_quarantine

        def quarantine_or_fail(**kwargs):
            if kwargs["mod_id"] == 525547 and not kwargs.get("dry_run"):
                raise InstallError("simulated failure")

            return real_quarantine(**kwargs)

        errors = io.StringIO()

        with (
            patch("builtins.input", return_value="YES"),
            patch(
                "sandmod.cli.commands.quarantine.quarantine_mod",
                side_effect=quarantine_or_fail,
            ),
            redirect_stderr(errors),
        ):
            result = sandmod_quarantine_many(254, self.root, self.ids)

        self.assertEqual(result, 1)

        # First mod succeeded; second remains untouched.
        self.assertFalse((self.mods / "391659").exists())
        self.assertTrue((self.mods / "525547").is_dir())

        self.assertEqual(self.state.read_bytes(), self.original_state)
        self.assertIn("Completed 1 of 2", errors.getvalue())


class BulkQuarantineDispatchTests(unittest.TestCase):
    def setUp(self):
        self.config = (
            ModIOConfig(game_id=254, platform="linuxserver"),
            GameConfig(storage_root=Path("unused")),
        )

    def test_single_mod_uses_existing_command(self):
        with (
            patch.object(sys, "argv", ["sandmod", "quarantine", "391659"]),
            patch(
                "sandmod.cli.runner.load_config",
                return_value=self.config,
            ),
            patch(
                "sandmod.cli.runner.sandmod_commands.quarantine",
                return_value=0,
            ) as command,
        ):
            result = runner._run()

        self.assertEqual(result, 0)
        command.assert_called_once_with(254, Path("unused"), 391659, dry_run=False)

    def test_bulk_dry_run_dispatch(self):
        with (
            patch.object(
                sys,
                "argv",
                ["sandmod", "quarantine", "391659", "525547", "--dry-run"],
            ),
            patch(
                "sandmod.cli.runner.load_config",
                return_value=self.config,
            ),
            patch(
                "sandmod.cli.runner.sandmod_commands.quarantine_preview_many",
                return_value=0,
            ) as command,
        ):
            result = runner._run()

        self.assertEqual(result, 0)
        command.assert_called_once_with(254, Path("unused"), [391659, 525547])

    def test_bulk_without_dry_run_dispatches_execution(self):
        with (
            patch.object(
                sys,
                "argv",
                ["sandmod", "quarantine", "391659", "525547"],
            ),
            patch(
                "sandmod.cli.runner.load_config",
                return_value=self.config,
            ),
            patch(
                "sandmod.cli.runner.sandmod_commands.quarantine_many",
                return_value=0,
            ) as command,
        ):
            result = runner._run()

        self.assertEqual(result, 0)

        command.assert_called_once_with(
            254,
            Path("unused"),
            [391659, 525547],
        )


if __name__ == "__main__":
    unittest.main()
