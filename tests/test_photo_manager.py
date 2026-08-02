from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.build_enhanced_image import (
    PHOTO_SLOTS,
    add_launcher_record,
    add_notebook_help,
    build_enhanced_image,
    disable_inactive_dosv_driver,
)
from tools.personaware_photos import (
    add_photo,
    assign_photo,
    copy_from_image,
    list_gallery,
    prepare_photo,
    remove_photo,
    restore_photo,
    validate_photo_bytes,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PhotoManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="pwphoto-tests-")
        cls.root = Path(cls.temporary.name)
        cls.source_image = PROJECT_ROOT / "dist" / "Personaware-English.img"
        cls.source_hash = hashlib.sha256(cls.source_image.read_bytes()).hexdigest()
        cls.enhanced_image = cls.root / "enhanced.img"
        build_enhanced_image(cls.source_image, cls.enhanced_image)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_build_does_not_modify_english_1_image(self) -> None:
        self.assertEqual(
            self.source_hash,
            hashlib.sha256(self.source_image.read_bytes()).hexdigest(),
        )

    def test_launcher_record_is_native_sized_and_idempotent(self) -> None:
        table = self.root / "launcher.ctl"
        copy_from_image(self.source_image, "/PW/DATA/MDLAUNCH.CTL", table)
        original = table.read_bytes()
        enhanced = add_launcher_record(original)
        self.assertEqual(len(original) + 120, len(enhanced))
        self.assertEqual(b"\0\0\0\xf0", enhanced[-4:])
        self.assertEqual(1, enhanced.count(b"PWPHOTO.COM"))
        self.assertEqual(b"Photo Mgr", enhanced[14 * 120 + 6 : 14 * 120 + 15])
        self.assertIn(b"COMMAND.COM", enhanced[15 * 120 : 16 * 120])
        self.assertIn(b"ps2.exe", enhanced[16 * 120 : 17 * 120])
        self.assertEqual(enhanced, add_launcher_record(enhanced))

    def test_notebook_help_is_added_once(self) -> None:
        notebook = self.root / "DEFAULT.NTD"
        copy_from_image(self.source_image, "/PW/DATA/DEFAULT.NTD", notebook)
        original = notebook.read_bytes()
        enhanced = add_notebook_help(original)
        self.assertEqual(1, enhanced.count(b"11. Launcher Photos"))
        self.assertEqual(enhanced, add_notebook_help(enhanced))
        self.assertTrue(enhanced.endswith(b"\x1a"))
        without_marker = add_notebook_help(original.rstrip(b"\x1a"))
        self.assertEqual(1, without_marker.count(b"11. Launcher Photos"))
        self.assertFalse(without_marker.endswith(b"\x1a"))

    def test_inactive_dosv_display_driver_is_disabled(self) -> None:
        config = self.root / "CONFIG.SYS"
        copy_from_image(self.enhanced_image, "/CONFIG.SYS", config)
        data = config.read_bytes()
        font = b"DEVICEHIGH=C:\\DOS\\$FONT.SYS /MSG=OFF"
        display = b"DEVICEHIGH=C:\\DOS\\$DISP.SYS /MSG=OFF"
        self.assertIn(b"\r\n" + font, data)
        self.assertNotIn(b"REM " + font, data)
        self.assertIn(b"REM " + display, data)
        self.assertNotIn(b"\r\n" + display, data)
        self.assertEqual(data, disable_inactive_dosv_driver(data))

    def test_enhanced_image_has_stock_backups_and_launcher_utility(self) -> None:
        utility = self.root / "PWPHOTO.COM"
        copy_from_image(self.enhanced_image, "/PW/PWPHOTO.COM", utility)
        self.assertIn(b"PersonaWare Launcher Photo Manager 2.0", utility.read_bytes())
        for number in range(1, 6):
            stock = self.root / f"STOCK{number}.BMP"
            copy_from_image(
                self.enhanced_image, f"/PW/PHOTO/STOCK{number}.BMP", stock
            )
            validate_photo_bytes(stock.read_bytes())

    def test_converter_writes_exact_native_bmp_format(self) -> None:
        source = self.root / "source.ppm"
        output = self.root / "prepared.bmp"
        pixels = bytes(
            component
            for y in range(360)
            for x in range(640)
            for component in (x % 256, y % 256, (x + y) % 256)
        )
        source.write_bytes(b"P6\n640 360\n255\n" + pixels)
        prepare_photo(source, output)
        validate_photo_bytes(output.read_bytes())
        self.assertEqual(24118, output.stat().st_size)

    def test_add_assign_remove_and_restore_workflow(self) -> None:
        working = self.root / "workflow.img"
        working.write_bytes(self.enhanced_image.read_bytes())
        source = self.root / "gallery-source.ppm"
        source.write_bytes(b"P6\n320 480\n255\n" + bytes((20, 120, 220)) * 320 * 480)

        number = add_photo(working, source, slot=3)
        self.assertEqual(1, number)
        self.assertEqual([1], list_gallery(working))
        user = self.root / "user.bmp"
        active = self.root / "active.bmp"
        copy_from_image(working, "/PW/PHOTO/USR1.BMP", user)
        copy_from_image(working, f"/PW/SYSTEM/{PHOTO_SLOTS[2]}", active)
        self.assertEqual(user.read_bytes(), active.read_bytes())

        remove_photo(working, 1)
        self.assertEqual([], list_gallery(working))
        active_after_remove = self.root / "active-after-remove.bmp"
        copy_from_image(
            working, f"/PW/SYSTEM/{PHOTO_SLOTS[2]}", active_after_remove
        )
        self.assertEqual(active.read_bytes(), active_after_remove.read_bytes())

        restore_photo(working, 3)
        restored = self.root / "restored.bmp"
        stock = self.root / "workflow-stock.bmp"
        copy_from_image(working, f"/PW/SYSTEM/{PHOTO_SLOTS[2]}", restored)
        copy_from_image(working, "/PW/PHOTO/STOCK3.BMP", stock)
        self.assertEqual(stock.read_bytes(), restored.read_bytes())

    def test_assign_rejects_a_missing_gallery_picture(self) -> None:
        with self.assertRaisesRegex(ValueError, "not installed"):
            assign_photo(self.enhanced_image, 9, 1)


if __name__ == "__main__":
    unittest.main()
