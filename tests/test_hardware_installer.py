from __future__ import annotations

import struct
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path

from scripts.build_hardware_installer import (
    MANIFEST_MAGIC,
    PARTITION_OFFSET,
    SECTOR_SIZE,
    build_hardware_installer,
)
from scripts.build_physical_installer_from_backup import (
    fat12_length,
    physical_readme,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class HardwareInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="pwenglish-test-hw-")
        root = Path(cls.temporary.name)
        cls.output = root / "output"
        cls.archive = root / "hardware-installer.zip"
        cls.package = build_hardware_installer(
            PROJECT_ROOT / "dist" / "Personaware-English-2.0.img",
            cls.output,
            cls.archive,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_embedded_volume_is_exact_release_partition(self) -> None:
        disk = (PROJECT_ROOT / "dist" / "Personaware-English-2.0.img").read_bytes()
        volume = (self.package / "PW-EN.IMG").read_bytes()
        self.assertEqual(disk[PARTITION_OFFSET:], volume)
        self.assertEqual(8160 * SECTOR_SIZE, len(volume))
        self.assertEqual(b"\x55\xaa", volume[510:512])

    def test_manifest_matches_complete_embedded_volume(self) -> None:
        volume = (self.package / "PW-EN.IMG").read_bytes()
        manifest = (self.package / "PW-EN.CRC").read_bytes()
        magic, sectors, sector_size, serial, crc = struct.unpack(
            "<8sHHII", manifest
        )
        self.assertEqual(MANIFEST_MAGIC, magic)
        self.assertEqual(8160, sectors)
        self.assertEqual(SECTOR_SIZE, sector_size)
        self.assertEqual(struct.unpack_from("<I", volume, 39)[0], serial)
        self.assertEqual(zlib.crc32(volume) & 0xFFFFFFFF, crc)

    def test_installer_is_backup_first_and_full_volume(self) -> None:
        script = (self.package / "INSTALL.BAT").read_text(encoding="ascii")
        backup = script.index("PWIMAGE.COM /B")
        install = script.index("PWIMAGE.COM /I")
        self.assertLess(backup, install)
        self.assertIn("PWIMAGE.COM /Q", script)
        self.assertIn("D-ORIG.IMG", script)
        self.assertIn("GOTO WAIT", script)
        self.assertNotIn("FILES.BAT", script)
        self.assertFalse((self.package / "PAYLOAD").exists())

    def test_dos_writer_has_hardware_install_safeguards(self) -> None:
        binary = (self.package / "PWIMAGE.COM").read_bytes()
        self.assertIn(b"Type INSTALL and press Enter to continue:", binary)
        self.assertIn(b"C:\\PWMINST\\PW-EN.IMG", binary)
        self.assertIn(b"PC110 English image byte for byte", binary)

        source = (PROJECT_ROOT / "installer" / "dos" / "pwimage.asm").read_text(
            encoding="ascii"
        )
        data_loop = source.index(".restore_loop:")
        boot_write = source.index(".restore_boot_sector:")
        verification = source.index("call verify_target_crc", boot_write)
        self.assertLess(data_loop, boot_write)
        self.assertLess(boot_write, verification)

    def test_package_contains_only_hardware_install_and_recovery_files(self) -> None:
        expected = {
            "FORCERST.BAT",
            "INSTALL.BAT",
            "NOTICE.TXT",
            "PW-EN.CRC",
            "PW-EN.IMG",
            "PWCOPY.COM",
            "PWIMAGE.COM",
            "README.TXT",
            "RESTDATA.BAT",
            "RESTORE.BAT",
            "SHA256.TXT",
            "STARTPW.BAT",
            "STATE.OK",
        }
        self.assertEqual(expected, {path.name for path in self.package.iterdir()})
        with zipfile.ZipFile(self.archive) as archive:
            names = set(archive.namelist())
        self.assertEqual({f"PWMINST/{name}" for name in expected}, names)

    def test_machine_specific_layout_uses_bootable_fat12_size(self) -> None:
        self.assertEqual(12, fat12_length(7776, 1, 2, 32))

    def test_machine_specific_readme_describes_pcdos_repack(self) -> None:
        readme = physical_readme(7776, 0x12345678, 2, 0x80).decode("ascii")
        self.assertIn("7,776 sectors", readme)
        self.assertIn("1,024 bytes", readme)
        self.assertIn("contiguous from cluster 2", readme)
        self.assertIn("Boot-time BIOS drive: 80h", readme)


if __name__ == "__main__":
    unittest.main()
