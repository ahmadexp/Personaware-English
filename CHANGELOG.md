# Changelog

All notable project changes are documented here.

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
