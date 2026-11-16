"""Next-slice regression tests: reject Windows-special ZIP entry names.

These should FAIL on the existing extractor until its filename checks are fixed.
The names are rejected on every OS for predictable cross-platform behavior.
"""

import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from sandmod.download import StageError, extract_modfile


class ZipSecurityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def extract_one(self, filename):
        archive = self.root / "test.zip"
        stage = self.root / "extracted"
        with ZipFile(archive, "w") as zip_file:
            zip_file.writestr(filename, b"test data")
        try:
            return extract_modfile(archive, stage, expected_uncompressed_size=1000)
        finally:
            # Each subtest should use a clean staging directory.
            if stage.exists():
                import shutil

                shutil.rmtree(stage)

    def test_reject_windows_special_names(self):
        unsafe = (
            "folder/map.pak:alternate",
            "folder/NUL",
            "folder/CON.txt",
            "folder/AUX",
            "folder/LPT1.pak",
            "folder/trailing.",
            "folder/trailing ",
            "folder/bad<name>.pak",
        )
        for name in unsafe:
            with self.subTest(name=name):
                with self.assertRaises(StageError):
                    self.extract_one(name)

    def test_reject_parent_directory_traversal(self):
        with self.assertRaises(StageError):
            self.extract_one("../outside.pak")

    def test_accept_normal_pak_filename(self):
        self.assertEqual(self.extract_one("Hydropakchunk0-WindowsClient.pak"), 1)


if __name__ == "__main__":
    unittest.main()
