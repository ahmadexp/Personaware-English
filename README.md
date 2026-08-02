<div align="center">
  <img src="docs/images/launcher.png" alt="PersonaWare English launcher" width="720">
  <h1>PersonaWare English</h1>
  <p><strong>A comprehensive English translation of PersonaWare for the IBM Palm Top PC 110.</strong></p>
  <p>
    <img alt="Translation status: complete" src="https://img.shields.io/badge/translation-complete-2ea44f">
    <a href="https://github.com/ahmadexp/PersonaWare-English/actions/workflows/verify.yml"><img alt="Verify release" src="https://github.com/ahmadexp/PersonaWare-English/actions/workflows/verify.yml/badge.svg"></a>
    <img alt="Platform: IBM Palm Top PC 110" src="https://img.shields.io/badge/platform-IBM%20PC%20110-0f62fe">
    <img alt="Disk size: 4 MiB" src="https://img.shields.io/badge/disk-4%20MiB-6f42c1">
    <img alt="UI language: English" src="https://img.shields.io/badge/UI-English-f5a623">
    <img alt="Recovery: exact D volume image" src="https://img.shields.io/badge/recovery-exact%20D%3A%20image-cb2431">
  </p>
</div>

PersonaWare English replaces the Japanese application interface, warnings,
help panels, launcher metadata, bundled data, and active DOS environment with
concise English text while preserving the original software layout and PC 110
hardware behavior. Version 2.0 also adds a native DOS Photo Manager with
protected original pictures and tools for preparing modern image files. The
original Power Management launcher entry remains in place.

## Get the image

| Item | Value |
| --- | --- |
| Bootable image | [`dist/Personaware-English-2.0.img`](dist/Personaware-English-2.0.img) |
| DOS CF installer | [`dist/PersonaWare-English-2.0-CF-Installer.zip`](dist/PersonaWare-English-2.0-CF-Installer.zip) |
| Screenshot archive | [`dist/PersonaWare-English-2.0-Screenshots.zip`](dist/PersonaWare-English-2.0-Screenshots.zip) |
| Format | 4 MiB raw MBR disk image with an active FAT partition |
| Boot environment | PC DOS 7, U.S. English code page 437 |
| Keyboard | Original PC 110 Japanese keyboard mapping |
| Launcher gallery | 9 user pictures, 5 assignable picture slots |

SHA-256 checksums:

```text
d66065cf935c4ed266660c13594f0cf1e0348391994c97b7c9818a5ebe2a91d0  Personaware-English-2.0.img
fcab04abdd9f906a306c366e31460ef35d91c20a11427df6e7a3318e25aacaac  PersonaWare-English-2.0-CF-Installer.zip
8e09e1a3995b09aa598101e272948c16ae51b2ac508db03eccfe918a0fc12442  PersonaWare-English-2.0-Screenshots.zip
```

Verify the download before booting:

```sh
shasum -a 256 -c dist/SHA256SUMS.txt
```

Boot a copy of the image on an IBM PC 110 or a compatible emulator. The final
runtime pass was performed with the
[`pc110-qemu`](https://github.com/ahmadexp/pc110-qemu) environment in snapshot
mode.

## Install from a bootable DOS CF

Unzip `PersonaWare-English-2.0-CF-Installer.zip` onto the root of a DOS-bootable
CF so it creates `C:\PWMINST`. Boot from the CF, confirm that the existing
PersonaWare installation is `D:\PW`, then run:

```bat
C:\PWMINST\INSTALL.BAT
```

Before changing `D:`, the installer saves every sector of the logical `D:`
volume to `C:\PWMINST\D-ORIG.IMG`, creates a size, volume-identity, and CRC-32
sidecar, then reopens and reads the entire image back from the CF. It refuses
to overwrite an existing recovery image. Each payload CRC is checked before
copying, and every installed file is then read back and compared. It also
preserves the four current PersonaWare databases in `C:\PWMINST\USERDATA` and
can safely resume an interrupted installation from a verified image.

To restore the complete original `D:` volume, boot from the same CF and run:

```bat
C:\PWMINST\RESTORE.BAT
```

Recovery verifies the image, matches the target volume size and serial, and
requires typed `YES` confirmation. After writing, it reads all of `D:` back and
checks the complete CRC-32. The volume boot sector is written last, and the
batch file locks further DOS access until restart. If the boot sector is
already unreadable, `FORCERST.BAT` provides a separate emergency path requiring
typed `FORCE` confirmation. Emergency recovery requires the intended volume to
remain assigned as DOS `D:`. The image covers the logical DOS volume, not the
physical disk MBR or partition table.

The archive does not include DOS. Use reliable power, and provide free CF space
equal to the size of `D:` plus at least 3 MiB. The target must be FAT12 or
FAT16, use 512-byte sectors, contain at most 65,535 sectors, and run on a
386-or-newer processor. See the
[complete CF installation and recovery guide](docs/cf-installer.md) before
using it on hardware.

## DOS Photo Manager

Open DOS from the PersonaWare launcher, type `PWPHOTO`, and press Enter. Photo
Manager keeps the original five launcher pictures in
`C:\PW\PHOTO\STOCK1.BMP` through
`STOCK5.BMP`, and stores up to nine user pictures as `USR1.BMP` through
`USR9.BMP`. From the manager you can list and import pictures, assign one to any
launcher picture slot, remove gallery copies, or restore one or all original
pictures. Restart PersonaWare after assigning or restoring a slot.

Photo Manager is deliberately a DOS command rather than a seventeenth launcher
entry. This keeps DOS and Power Management in their original launcher slots.

PersonaWare requires an uncompressed 190x250, 16-color Windows BMP. The host
tool converts PNG, JPEG, GIF, TIFF, BMP, and other formats supported by
ImageMagick:

```sh
python3 tools/personaware_photos.py prepare family.jpg USR1.BMP
```

Install ImageMagick first with `brew install imagemagick` on macOS or your
distribution's `imagemagick` package on Linux. The tool validates the final BMP
header, dimensions, palette depth, compression, and exact file size.

It can also safely manage a disk image while PersonaWare and the emulator or
MiSTer core are stopped:

```sh
# Inspect the nine-picture gallery.
python3 tools/personaware_photos.py list Personaware-English-2.0.img

# Convert, add, and immediately assign a photo to launcher slot 3.
python3 tools/personaware_photos.py add Personaware-English-2.0.img family.jpg \
  --slot 3 --backup Personaware-English-2.0.before-photos.img

# Change assignments, remove a gallery copy, or restore the stock pictures.
python3 tools/personaware_photos.py assign Personaware-English-2.0.img 1 5
python3 tools/personaware_photos.py remove Personaware-English-2.0.img 1
python3 tools/personaware_photos.py restore Personaware-English-2.0.img
```

The manager never deletes an active slot when removing a gallery copy. The
host tool refuses to overwrite an existing backup. Do not edit a disk image
that is mounted or currently running.

## Screenshots

<table>
  <tr>
    <td width="50%" align="center">
      <img src="docs/images/launcher.png" alt="English PersonaWare launcher with Power Management"><br>
      <sub>Original launcher layout with Power Management</sub>
    </td>
    <td width="50%" align="center">
      <img src="docs/images/photo-manager-menu.png" alt="PersonaWare DOS Photo Manager menu"><br>
      <sub>Add, remove, assign, and restore launcher pictures</sub>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center">
      <img src="docs/images/address-book-help.png" alt="English Address Book help"><br>
      <sub>Address Book help and keyboard reference</sub>
    </td>
    <td width="50%" align="center">
      <img src="docs/images/address-book-warning.png" alt="English Address Book cancel warning"><br>
      <sub>Translated warning and confirmation dialog</sub>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center">
      <img src="docs/images/email-help.png" alt="English E-Mail help"><br>
      <sub>E-Mail help</sub>
    </td>
    <td width="50%" align="center">
      <img src="docs/images/fax-help.png" alt="English FAX help"><br>
      <sub>FAX help</sub>
    </td>
  </tr>
  <tr>
    <td colspan="2" align="center">
      <img src="docs/images/dos-command.png" alt="English PC DOS command error"><br>
      <sub>English DOS shell and command errors</sub>
    </td>
  </tr>
</table>

<table>
  <tr>
    <td width="50%" align="center">
      <img src="docs/images/personaware-english-cf-installer.png" alt="PersonaWare English CF installer completed in DOS"><br>
      <sub>Backup-first English installation from the DOS CF</sub>
    </td>
    <td width="50%" align="center">
      <img src="docs/images/personaware-english-cf-restore.png" alt="Original PersonaWare D volume restored and verified in DOS"><br>
      <sub>Checksummed sector restore with full read-back verification</sub>
    </td>
  </tr>
</table>

## What was translated

### Applications

- Address Book, Schedule, ToDo, Notebook, Editor, E-Mail, FAX, and the FAX
  viewer.
- Shared file dialogs, buttons, warnings, device errors, print errors, search,
  passwords, secret mode, and clipboard operations.
- Previously untranslated F1 help pages and late-path confirmation dialogs.
- Launcher titles, application metadata, and DOS PM command-line messages.

### Bundled data

- Default Notebook and Address Book content, sample game scores, holidays, era
  names, communications defaults, and editor help.
- All 326 World Clock city names.
- All 140 historical dial-directory location labels.

### Boot environment

- Active PC DOS locale changed from Japanese CP932 to U.S. English CP437.
- Japanese IME startup disabled.
- DOS/V input-status text, word-registration prompts, and related warnings
  translated.
- PC 110 keyboard mapping retained.

### Version 2.0 additions

- Native 16-bit DOS Photo Manager available through the `PWPHOTO` command.
- Nine-picture user gallery, five assignable launcher slots, and protected
  copies of every original picture.
- Modern host-side converter and image-management commands.
- Original DOS and Power Management launcher entries preserved.
- English Notebook and DOS help covering photo management.

The Japanese-only postal lookup database was removed. Address Book remains
usable through manual postal and address entry, and its help explains the
change.

## Verification

The release image passed structural, static, and runtime checks:

- Confirmed as a 4 MiB MBR image with its original active FAT partition.
- Extracted every replaced file from the finished image and compared it with
  the translated source.
- Decompressed all 20 PKLITE-compressed PersonaWare modules and confirmed them
  as valid DOS executables.
- Audited translated data and scoped display-string regions for remaining
  Japanese UI text.
- Confirmed that the remaining CP932 scanner hits are inactive DOS/V and IME
  resource banks, character-conversion tables, or binary false positives.
- Booted to the launcher and exercised Address Book warnings and help, E-Mail
  help and setup, FAX help, the DOS launcher, and an English command error.
- Confirmed the original 16-item launcher and Power Management entry are
  unchanged, then ran `PWPHOTO` from DOS, listed an empty gallery, and restored
  all five original pictures.
- Rebuilt and tested the DOS CF installer, recovery image metadata, backup-first
  ordering, verified resume, payload CRCs, complete image read-back, target
  identity checks, boot-sector-last restore, emergency recovery, and the
  interrupted-install recovery path.

The automated repository check verifies the image checksum, compiles every
Python utility, validates the translation table, and confirms the release
artifact's size and MBR signature.

## Translation approach

PersonaWare stores CP932 strings inside fixed-layout DOS executables and data
files. The patcher replaces display text within the original byte slots so code,
relocations, and file offsets stay intact. Data rebuilders translate structured
resources separately, and the audit utility scans printable CP932 runs for
likely user-facing Japanese.

Internal CP932 conversion tables and the Address Book kana/romanization lookup
table are intentionally preserved because they implement text conversion and
name lookup rather than visible UI. IBM PC DOS files also retain dormant
Japanese DOS/V and IME resource copies. The active English boot configuration
does not load them. All reachable PersonaWare application UI, launcher
metadata, bundled starter data, help, and active DOS startup text are English.

## Repository layout

```text
dist/                         Bootable image, CF installer, and SHA-256 manifest
docs/images/                  Runtime screenshots from the finished build
installer/dos/                16-bit backup, restore, and verified-copy sources
utilities/dos/pwphoto.asm     Native PersonaWare DOS Photo Manager
resources/name-translations.tsv
                              Reviewed city and dial-directory names
scripts/audit_japanese.py     CP932-aware Japanese text scanner
scripts/build_cf_installer.py Deterministic DOS CF package builder
scripts/build_enhanced_image.py
                              Photo Manager image integration
scripts/merge_user_data.py    Host-specific user database preservation
scripts/patch_binaries.py     Fixed-slot executable translations
scripts/patch_boot.py         English locale and DOS/V startup patches
scripts/patch_data.py         Data, help, and launcher translations
tests/                        Installer packaging and recovery-safety tests
tools/personaware_photos.py   Modern picture converter and disk-image manager
```

The patch scripts expect legally obtained source files from the original media
and, for the executable pass, the historical partially translated modules.
They deliberately fail when expected bytes differ so an incompatible source
cannot be patched silently.

## Contributing

Bug reports, clearer wording, and additional runtime verification are welcome.
See [`CONTRIBUTING.md`](CONTRIBUTING.md) before submitting source material or
binary artifacts.

## Legal

Project-authored scripts and documentation are available under the
[`LICENSE`](LICENSE). The disk image and its IBM software are not relicensed by
this project. Read [`NOTICE.md`](NOTICE.md) and use or redistribute the image
only when you have the necessary rights to the underlying software and media.
