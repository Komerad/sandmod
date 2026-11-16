"""Audit and updater must not call missing installs 'current'."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sandmod.audit import compare_mods
from sandmod.cli.commands.update import sandmod_update
from sandmod.game import get_mods_path, get_state_path


class AuditHealthTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.storage = Path(temp.name) / "storage"
        self.mods_root = get_mods_path(254, self.storage)
        self.mods_root.mkdir(parents=True)
        self.target = self.mods_root / "42"
        self.state_path = get_state_path(254, self.storage)
        self.state_path.parent.mkdir(parents=True)
        self.local = {
            "ID": 42,
            "State": 1,
            "PathOnDisk": str(self.target),
            "Profile": {
                "name": "Example Mod",
                "modfile": {"id": 101, "version": "1.0"},
            },
        }
        self.remote = {
            42: {
                "id": 42,
                "name": "Example Mod",
                "modfile": {"id": 101, "version": "1.0"},
            }
        }

    def audit_status(self):
        results = compare_mods([self.local], self.remote, self.mods_root)
        self.assertEqual(len(results), 1)
        return results[0].status

    def test_matching_release_and_existing_directory_is_current(self):
        self.target.mkdir()
        self.assertEqual(self.audit_status(), "current")

    def test_missing_directory_is_not_current(self):
        self.assertEqual(self.audit_status(), "missing")

    def test_non_installed_state_is_unknown(self):
        self.target.mkdir()
        self.local["State"] = 0
        self.assertEqual(self.audit_status(), "unknown")

    def test_mismatched_release_is_outdated(self):
        self.target.mkdir()
        self.remote[42]["modfile"]["id"] = 102
        self.assertEqual(self.audit_status(), "outdated")

    def test_updater_refuses_missing_install_without_network(self):
        self.state_path.write_text(json.dumps({"Mods": [self.local]}), encoding="utf-8")
        with patch("sandmod.cli.commands.update.get_mod") as get_mod:
            result = sandmod_update("unused", 254, "windows", self.storage, 42)

        self.assertEqual(result, 1)
        get_mod.assert_not_called()


if __name__ == "__main__":
    unittest.main()
