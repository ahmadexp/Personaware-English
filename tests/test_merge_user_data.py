from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.build_enhanced_image import add_notebook_help
from scripts.merge_user_data import merge_user_data
from tools.personaware_photos import copy_from_image


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class MergeUserDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="pwmerge-tests-")
        self.root = Path(self.temporary.name)
        self.existing = (
            PROJECT_ROOT / "resources" / "base" / "Personaware-English-1.0.img"
        )
        self.release = PROJECT_ROOT / "dist" / "Personaware-English-2.0.img"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def extract(self, image: Path, name: str) -> bytes:
        destination = self.root / f"{image.stem}-{name}"
        copy_from_image(image, f"/PW/DATA/{name}", destination)
        return destination.read_bytes()

    def test_fresh_defaults_preserve_only_nondefault_user_databases(self) -> None:
        output = self.root / "fresh-defaults.img"
        copied = merge_user_data(
            self.existing,
            self.release,
            output,
            fresh_defaults=True,
        )
        self.assertNotIn("DEFAULT.NTD", copied)
        self.assertIn("NOTEMAIL.NTD", copied)
        self.assertEqual(
            self.extract(self.release, "DEFAULT.NTD"),
            self.extract(output, "DEFAULT.NTD"),
        )
        self.assertEqual(
            self.extract(self.existing, "NOTEMAIL.NTD"),
            self.extract(output, "NOTEMAIL.NTD"),
        )

    def test_preserved_default_notebook_receives_photo_help(self) -> None:
        output = self.root / "preserved-defaults.img"
        copied = merge_user_data(self.existing, self.release, output)
        self.assertIn("DEFAULT.NTD", copied)
        self.assertEqual(
            add_notebook_help(self.extract(self.existing, "DEFAULT.NTD")),
            self.extract(output, "DEFAULT.NTD"),
        )


if __name__ == "__main__":
    unittest.main()
