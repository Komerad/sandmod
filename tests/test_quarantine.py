import json
import tempfile
import unittest
from pathlib import Path

from sandmod.audit import compare_mods
from sandmod.game import get_mods_path, get_state_path
from sandmod.install import InstallError
from sandmod.quarantine import get_local_status, quarantine_mod, restore_mod


class QuarantineTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        self.root = Path(temp.name) / "storage"
        self.mods = get_mods_path(254, self.root)
        self.mods.mkdir(parents=True)

        self.target = self.mods / "448415"
        self.target.mkdir()
        (self.target / "test.pak").write_bytes(b"test content")

        self.state = get_state_path(254, self.root)
        self.state.parent.mkdir(parents=True)

        self.data = {
            "Mods": [
                {
                    "ID": 448415,
                    "State": 1,
                    "PathOnDisk": str(self.target),
                    "Profile": {
                        "name": "Mud Village",
                        "modfile": {"version": "1.9"},
                    },
                }
            ]
        }

        self.state.write_text(json.dumps(self.data))

    def quarantine(self):
        return quarantine_mod(
            game_id=254,
            storage_root=self.root,
            mod_id=448415,
        )

    def restore(self):
        return restore_mod(
            game_id=254,
            storage_root=self.root,
            mod_id=448415,
        )

    def test_quarantine_and_restore_preserve_state(self):
        original_state = self.state.read_bytes()

        self.quarantine()

        self.assertFalse(self.target.exists())
        self.assertEqual(self.state.read_bytes(), original_state)

        self.restore()

        self.assertTrue(self.target.is_dir())
        self.assertEqual(
            (self.target / "test.pak").read_bytes(),
            b"test content",
        )
        self.assertEqual(self.state.read_bytes(), original_state)

    def test_restore_refuses_redownloaded_installation(self):
        self.quarantine()

        self.target.mkdir()
        (self.target / "new.pak").write_bytes(b"replacement")

        with self.assertRaises(InstallError):
            self.restore()

        self.assertEqual(
            (self.target / "new.pak").read_bytes(),
            b"replacement",
        )

    def test_quarantined_mod_is_reported(self):
        mod = self.data["Mods"][0]

        remote = {
            448415: {
                "id": 448415,
                "name": "Mud Village",
                "modfile": {"id": 123, "version": "1.9"},
            },
        }

        self.quarantine()

        self.assertEqual(
            get_local_status(mod, self.mods),
            "quarantined",
        )

        results = compare_mods([mod], remote, self.mods)

        self.assertEqual(results[0].status, "quarantined")

    def test_invalid_quarantine_remains_missing(self):
        mod = self.data["Mods"][0]

        self.quarantine()

        manifest = self.mods.parent / ".sandmod-quarantine" / "448415" / "manifest.json"
        manifest.write_text("{}", encoding="utf-8")

        self.assertEqual(
            get_local_status(mod, self.mods),
            "missing",
        )


if __name__ == "__main__":
    unittest.main()
