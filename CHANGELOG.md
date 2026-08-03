# Changelog

All notable project changes are documented here.

## 2.0.6 - 2026-08-03

### Fixed

- Restored every English caption in the launcher's lower center LCD panel by
  preserving the original per-entry field alignment used by `MDLAUNCH`.
- Changed the active memory-manager setup to `EMM386 NOEMS`, preventing its
  page frame from occupying the PC110 option-ROM window and eliminating the
  option ROM and RAM warning during startup.

### Verified

- Confirmed the complete `DOS Command` caption on MiSTer `192.168.1.74` and
  the complete `Clock` caption on `192.168.10.251`.
- Both MiSTer systems boot PersonaWare with BIOS error count `00` and first
  error code `0000`.

### Documentation

- Refreshed the README and screenshot archive with live MiSTer captures of the
  restored `Clock` and `DOS Command` LCD captions.

## 2.0.5 - 2026-08-03

### Added

- Verified factory-layout installer for the tested 7,776-sector PC110
  PersonaWare volume with serial `3F4B-1004`.
- Redistributable modern fourteen-picture pack with complete source and
  license credits, including an original Nitrous Blue Focus RS photograph
  and a rear-view alternate.

### Fixed

- Recreated the original IBM PC DOS boot layout from the verified PowerQuest
  image, keeping `IBMBIO.COM` and `IBMDOS.COM` first, contiguous, and booting
  the internal disk as BIOS drive `80h` after removal of the installer CF.
- Remapped imported photograph colors and pixel indexes to PersonaWare's fixed
  sixteen-color IBM palette, eliminating false color and rainbow artifacts.

### Verified

- The factory-layout installer boots PersonaWare on physical IBM PC110
  hardware after the installer CF is removed.
- The corrected image set boots on both MiSTer test units with zero POST
  errors and correct picture colors.

## 2.0.0 - 2026-08-02

### Added

- Native PersonaWare Photo Manager available as the `PWPHOTO` DOS command.
- Nine-picture user gallery with add, list, assign, and remove operations.
- Protected backups and one-slot or all-slot restoration for the five original
  launcher pictures.
- ImageMagick-based host tool for converting modern pictures to exact 190x250,
  uncompressed 4-bit BMP files and managing an offline disk image.
- English Notebook and DOS help for picture management.
- Clean English boot without loading the inactive Japanese DOS/V display
  driver or printing its code-page warning.
- Automated image, converter, gallery, assignment, removal, restoration, and
  source-preservation tests.

### Verified

- The original 16-item launcher and Power Management entry remain unchanged.
- Photo Manager runs on PC DOS, lists the gallery, and restores all stock
  pictures.
- All reachable PersonaWare UI, help, launcher metadata, starter data, and
  active DOS startup text are English.

### Preserved

- Dormant Japanese DOS/V and IME resources used only by the disabled Japanese
  boot path.
- Internal CP932 conversion and kana lookup tables required for compatibility.

## 1.1.0 - 2026-08-01

### Added

- Self-contained DOS CF installer for upgrading PersonaWare on `D:`.
- Exact logical `D:` volume imaging with CRC-32 and volume-identity metadata.
- Saved-image and metadata read-back before installation begins.
- Guarded sector restore with boot-sector-last ordering, typed confirmation,
  complete post-write verification, and a separately confirmed emergency path
  for damaged volume metadata.
- Verified DOS file copier with build-time payload CRC enforcement, a 3 MiB CF
  reserve, and optional personal database recovery.
- Safe interrupted-install resume using verified image and state markers.
- Active English boot configuration that remains directly bootable as `C:`
  after the installer CF is removed.
- Reproducible installer packaging, automated recovery-safety tests, hardware
  guide, and DOS runtime screenshots.

### Verified

- The installer payload is reconstructed from the finished English release
  image and contains no PersonaWare Modern files.
- Structured PersonaWare data remains free of natural Japanese text, and the
  Japanese-only postal database is excluded and removed during installation.
- Full recovery remains available after an interrupted file-copy phase because
  it relies on the image checksum and target volume identity, not installed
  PersonaWare files.

## 1.0.0 - 2026-07-24

### Added

- Comprehensive English application-layer translation.
- English F1 help, warnings, dialogs, DOS PM errors, and launcher metadata.
- English active PC DOS boot locale with Japanese IME startup disabled.
- Translated bundled data, 326 World Clock cities, and 140 dial-directory
  labels.
- CP932-aware Japanese display-string audit.
- Verified 4 MiB bootable release image and runtime screenshot gallery.

### Changed

- Removed the Japanese-only postal lookup database; manual Address Book entry
  remains available.

### Preserved

- Internal CP932 conversion tables and kana/romanization lookup data.
- Original PC 110 keyboard mapping and bootable disk layout.
