import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch

from sandmod.install import InstallError, commit_staged_mod


class InstallTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.mods = self.root / "mods"
        self.mods.mkdir()
        self.target = self.mods / "42"
        self.target.mkdir()
        (self.target / "old.pak").write_bytes(b"old data")
        self.staging = self.mods / ".sandmod-stage" / "extracted"
        self.staging.mkdir(parents=True)
        (self.staging / "new.pak").write_bytes(b"new data...")
        self.meta = self.root / "metadata"
        self.meta.mkdir()
        self.state = self.meta / "state.json"
        self.initial = {
            "Mods": [
                {
                    "ID": 99,
                    "Profile": {"modfile": {"id": 77}},
                    "State": 1,
                    "PathOnDisk": str(self.mods / "99"),
                    "SizeOnDisk": 100,
                    "ExtraField": "keep",
                },
                {
                    "ID": 42,
                    "Profile": {"name": "Test", "modfile": {"id": 8, "version": "old"}},
                    "State": 1,
                    "PathOnDisk": str(self.target),
                    "SizeOnDisk": 8,
                    "Subscriptions": [1],
                },
            ],
            "version": 15,
            "some_other": "preserve",
        }
        self.state.write_text(json.dumps(self.initial))
        self.remote = {"id": 9, "version": "new", "mod_id": 42}

    def commit(self):
        return commit_staged_mod(
            mod_id=42, staging=self.staging, mods_root=self.mods, state_path=self.state, remote_modfile=self.remote
        )

    def test_success(self):
        self.assertIsNone(self.commit())
        self.assertEqual((self.target / "new.pak").read_bytes(), b"new data...")
        self.assertFalse((self.target / "old.pak").exists())
        self.assertFalse((self.mods.parent / ".sandmod-backup-42").exists())
        data = json.loads(self.state.read_text())
        self.assertEqual(data["Mods"][0], self.initial["Mods"][0])
        self.assertEqual(data["Mods"][1]["Profile"]["modfile"]["id"], 9)
        self.assertEqual(data["Mods"][1]["SizeOnDisk"], len(b"new data..."))
        self.assertEqual(data["Mods"][1]["Subscriptions"], [1])
        self.assertEqual(data["version"], 15)

    def test_state_replace_failure_rolls_back(self):
        original = self.state.read_bytes()
        with patch("sandmod.install.os.replace", side_effect=OSError("permission denied")):
            with self.assertRaisesRegex(InstallError, "original restored"):
                self.commit()
        self.assertEqual(self.state.read_bytes(), original)
        self.assertEqual((self.target / "old.pak").read_bytes(), b"old data")
        self.assertFalse((self.target / "new.pak").exists())
        self.assertFalse((self.mods.parent / ".sandmod-backup-42").exists())
        self.assertTrue((self.staging / "new.pak").exists())

    def test_wrong_path_rejected_before_changes(self):
        data = json.loads(self.state.read_text())
        data["Mods"][1]["PathOnDisk"] = "/somewhere/else"
        self.state.write_text(json.dumps(data))
        with self.assertRaisesRegex(InstallError, "Unexpected PathOnDisk"):
            self.commit()
        self.assertEqual((self.target / "old.pak").read_bytes(), b"old data")

    def test_leftover_backup_prevents_install(self):
        (self.mods.parent / ".sandmod-backup-42").mkdir()
        with self.assertRaisesRegex(InstallError, "Existing backup"):
            self.commit()
        self.assertTrue((self.target / "old.pak").exists())

    def test_concurrent_commits_preserve_both_metadata_updates(self):
        other_target = self.mods / "99"
        other_target.mkdir()
        (other_target / "old.pak").write_bytes(b"other old")
        other_stage = self.mods / ".sandmod-stage-99" / "extracted"
        other_stage.mkdir(parents=True)
        (other_stage / "new.pak").write_bytes(b"other new")

        def other_commit():
            return commit_staged_mod(
                mod_id=99,
                staging=other_stage,
                mods_root=self.mods,
                state_path=self.state,
                remote_modfile={"id": 78, "mod_id": 99},
            )

        first_at_publication = threading.Event()
        release_publication = threading.Event()
        second_started = threading.Event()
        real_replace = os.replace

        def delayed_replace(source, destination):
            if Path(destination) == self.state:
                first_at_publication.set()
                if not release_publication.wait(timeout=5):
                    raise AssertionError("test did not release state publication")
            return real_replace(source, destination)

        with patch("sandmod.install.os.replace", side_effect=delayed_replace):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(self.commit)
                try:
                    self.assertTrue(first_at_publication.wait(timeout=5))

                    def run_second():
                        second_started.set()
                        return other_commit()

                    second = pool.submit(run_second)
                    self.assertTrue(second_started.wait(timeout=5))
                    # Without a commit lock, both operations can prepare the
                    # same original state while publication is blocked.
                    time.sleep(0.3)
                finally:
                    release_publication.set()
                self.assertIsNone(first.result(timeout=5))
                self.assertIsNone(second.result(timeout=5))

        mods = {mod["ID"]: mod for mod in json.loads(self.state.read_text())["Mods"]}
        self.assertEqual(mods[42]["Profile"]["modfile"]["id"], 9)
        self.assertEqual(mods[99]["Profile"]["modfile"]["id"], 78)
        self.assertEqual((self.target / "new.pak").read_bytes(), b"new data...")
        self.assertEqual((other_target / "new.pak").read_bytes(), b"other new")

    def test_keyboard_interrupt_after_state_publication_preserves_new_files(self):
        real_replace = os.replace

        def interrupt_after_replace(source, destination):
            real_replace(source, destination)
            raise KeyboardInterrupt()

        with patch("sandmod.install.os.replace", side_effect=interrupt_after_replace):
            with self.assertRaises(KeyboardInterrupt):
                self.commit()

        self.assertEqual((self.target / "new.pak").read_bytes(), b"new data...")
        self.assertEqual(json.loads(self.state.read_text())["Mods"][1]["Profile"]["modfile"]["id"], 9)
        self.assertEqual((self.mods.parent / ".sandmod-backup-42" / "old.pak").read_bytes(), b"old data")

    def test_oserror_after_state_publication_reports_committed_backup(self):
        real_replace = os.replace

        def error_after_replace(source, destination):
            real_replace(source, destination)
            raise OSError("interrupted after replacement")

        with patch("sandmod.install.os.replace", side_effect=error_after_replace):
            backup = self.commit()

        self.assertEqual(backup, self.mods.parent / ".sandmod-backup-42")
        self.assertEqual((backup / "old.pak").read_bytes(), b"old data")
        self.assertEqual((self.target / "new.pak").read_bytes(), b"new data...")
        self.assertEqual(json.loads(self.state.read_text())["Mods"][1]["Profile"]["modfile"]["id"], 9)

    def test_unknown_state_after_swap_preserves_recovery_files(self):
        def state_changed_during_publish(source, destination):
            self.state.write_text('{"Mods": [], "external": true}')
            raise OSError("state publication interrupted")

        with patch("sandmod.install.os.replace", side_effect=state_changed_during_publish):
            with self.assertRaisesRegex(InstallError, "uncertain"):
                self.commit()

        self.assertEqual((self.target / "new.pak").read_bytes(), b"new data...")
        self.assertEqual((self.mods.parent / ".sandmod-backup-42" / "old.pak").read_bytes(), b"old data")
        self.assertEqual(len(list(self.meta.glob(".sandmod-state-*.tmp"))), 1)

    def test_interrupt_after_old_directory_move_restores_original(self):
        backup = self.mods.parent / ".sandmod-backup-42"
        real_rename = Path.rename
        original_state = self.state.read_bytes()

        def interrupted_rename(path, destination):
            result = real_rename(path, destination)
            if path == self.target and Path(destination) == backup:
                raise KeyboardInterrupt()
            return result

        with patch("sandmod.install.Path.rename", new=interrupted_rename):
            with self.assertRaises(KeyboardInterrupt):
                self.commit()

        self.assertEqual(self.state.read_bytes(), original_state)
        self.assertEqual((self.target / "old.pak").read_bytes(), b"old data")
        self.assertEqual((self.staging / "new.pak").read_bytes(), b"new data...")
        self.assertFalse(backup.exists())

    def test_interrupt_after_new_directory_move_restores_original(self):
        backup = self.mods.parent / ".sandmod-backup-42"
        real_rename = Path.rename
        original_state = self.state.read_bytes()

        def interrupted_rename(path, destination):
            result = real_rename(path, destination)
            if path == self.staging and Path(destination) == self.target:
                raise KeyboardInterrupt()
            return result

        with patch("sandmod.install.Path.rename", new=interrupted_rename):
            with self.assertRaises(KeyboardInterrupt):
                self.commit()

        self.assertEqual(self.state.read_bytes(), original_state)
        self.assertEqual((self.target / "old.pak").read_bytes(), b"old data")
        self.assertEqual((self.staging / "new.pak").read_bytes(), b"new data...")
        self.assertFalse(backup.exists())

    def test_backup_cleanup_failure_returns_backup_for_recovery(self):
        backup = self.mods.parent / ".sandmod-backup-42"
        with patch("sandmod.install.shutil.rmtree", side_effect=OSError("busy")):
            self.assertEqual(self.commit(), backup)
        self.assertEqual((backup / "old.pak").read_bytes(), b"old data")
        self.assertEqual((self.target / "new.pak").read_bytes(), b"new data...")
        self.assertEqual(json.loads(self.state.read_text())["Mods"][1]["Profile"]["modfile"]["id"], 9)

    def test_sdk_state_change_before_publication_restores_files(self):
        initial_bytes = self.state.read_bytes()
        replacement_state = json.loads(initial_bytes)
        replacement_state["some_other"] = "external SDK edit"
        real_read_bytes = Path.read_bytes
        state_reads = 0

        def sdk_changes_state_between_checks(path):
            nonlocal state_reads
            if path == self.state:
                state_reads += 1
                if state_reads == 3:  # After swapping dirs, before os.replace.
                    self.state.write_text(json.dumps(replacement_state))
            return real_read_bytes(path)

        with patch("sandmod.install.Path.read_bytes", new=sdk_changes_state_between_checks):
            with self.assertRaisesRegex(InstallError, "original restored"):
                self.commit()

        self.assertEqual((self.target / "old.pak").read_bytes(), b"old data")
        self.assertEqual((self.staging / "new.pak").read_bytes(), b"new data...")
        self.assertFalse((self.mods.parent / ".sandmod-backup-42").exists())
        self.assertEqual(json.loads(self.state.read_text()), replacement_state)

    def test_lock_is_shared_between_processes(self):
        from sandmod.install import _commit_lock

        script = (
            "import sys\n"
            "from pathlib import Path\n"
            "from sandmod.install import _commit_lock\n"
            "with _commit_lock(Path(sys.argv[1])):\n"
            "    print('locked', flush=True)\n"
            "    sys.stdin.readline()\n"
        )
        process = subprocess.Popen(
            [sys.executable, "-c", script, str(self.state)],
            cwd=str(Path(__file__).resolve().parent.parent),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual(process.stdout.readline().strip(), "locked")
            attempted = threading.Event()
            acquired = threading.Event()

            def try_lock():
                attempted.set()
                with _commit_lock(self.state):
                    acquired.set()

            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(try_lock)
                try:
                    self.assertTrue(attempted.wait(timeout=5))
                    self.assertFalse(acquired.wait(timeout=0.2), "lock ignored by second process")
                finally:
                    process.stdin.write("release\n")
                    process.stdin.flush()
                    process.stdin.close()
                future.result(timeout=5)
                self.assertTrue(acquired.is_set())
            self.assertEqual(process.wait(timeout=5), 0, process.stderr.read())
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            process.stdin.close()
            process.stdout.close()
            process.stderr.close()


if __name__ == "__main__":
    main()
