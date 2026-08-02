# CF install and recovery guide

The CF installer upgrades an existing PersonaWare installation on the DOS
`D:` volume to PersonaWare English. Before it changes anything, it creates and
verifies an exact recovery image of that complete logical volume.

## Before you begin

You need:

- An IBM PC 110 or compatible 386-or-newer DOS environment.
- A CF card that already boots DOS and appears as `C:` after boot.
- The existing PersonaWare volume mounted as `D:`, with `D:\PW\PW.BAT`
  present before installation.
- A FAT12 or FAT16 `D:` volume with 512-byte sectors and no more than 65,535
  sectors, approximately 32 MiB, and an extended BPB volume serial.
- Free CF space equal to the complete size of `D:` plus at least 3 MiB.
- Reliable external power for both installation and recovery.

The archive contains the installer, not a copy of DOS. For the stock 4 MiB
PersonaWare volume, a 16 MiB or larger CF leaves comfortable room for the
installer, recovery image, and working files.

## Prepare the CF

1. Download `dist/PersonaWare-English-2.0-CF-Installer.zip`.
2. Verify it against `dist/SHA256SUMS.txt`.
3. Unzip it onto the CF root. After boot, the directory must be
   `C:\PWMINST`.
4. Do not rename `PWMINST` or rearrange its contents.
5. Boot from the CF and run `DIR C:\PWMINST` and `DIR D:\PW` to confirm the
   drive assignment.

Stop if the CF is not `C:` or PersonaWare is not `D:`. The installer uses
explicit drive letters and refuses to install when `D:\PW\PW.BAT` is missing.

## Install PersonaWare English

At the DOS prompt, run:

```bat
C:\PWMINST\INSTALL.BAT
```

The installer performs three ordered steps:

1. `PWIMAGE.COM` reads every sector of the logical DOS `D:` volume into
   `C:\PWMINST\D-ORIG.IMG`. It records the sector count, bytes per sector,
   volume serial, and CRC-32 in `D-ORIG.CRC`. It then closes and reopens both
   files and reads the complete image back from the CF to verify it.
2. The current four default PersonaWare databases are copied to `USERDATA`
   and verified. These provide a convenient personal-data-only recovery path.
3. The complete English PersonaWare payload, active U.S. English DOS locale
   configuration, and translated DOS/V input-status resource are installed.
   Each source CRC-32 is checked before its destination is changed, then every
   destination is reopened and compared byte for byte. The boot configuration
   is installed last, and the obsolete Japanese-only postal database is
   removed.

The installer never overwrites an existing recovery image. If both recovery
files already exist, it verifies the complete image and current `D:` identity.
A valid pair can safely resume an interrupted installation. Verified state
markers prevent a retry from replacing the original personal-database copies
with partially installed defaults. If the recovery pair is incomplete or does
not verify, installation stops. Keep the installer CF unchanged after a
successful installation.

While still booted from the CF, start the installed copy with:

```bat
C:\PWMINST\STARTPW.BAT
```

After removing the CF, the upgraded internal disk becomes `C:` again and boots
normally using its English startup files.

## Restore the complete original volume

Restoring replaces every sector in the logical `D:` volume. Boot from the same
CF and run:

```bat
C:\PWMINST\RESTORE.BAT
```

Before writing, recovery checks all of the following:

- The sidecar has the expected format and exact length.
- The image length matches its saved sector count.
- The complete saved-image CRC-32 is correct.
- The current `D:` volume has the saved size and volume serial.
- You explicitly type `YES` at the destructive-operation prompt.

The restore does not depend on `D:\PW\PW.BAT` still being readable, so it
remains available after an interrupted installation. The image checksum and
the target volume identity are the restore safety checks. Because cloned
PersonaWare volumes may share both size and serial, you must still confirm that
the intended internal volume is DOS drive `D:` before accepting the prompt.

After writing, every sector is read again and the complete `D:` CRC-32 is
compared with the saved value. Restart the computer immediately after success.
The installer writes the volume boot sector last, reducing the chance that an
interrupted recovery makes normal recovery unavailable. `RESTORE.BAT` then
locks further DOS access until restart because DOS may still hold old
filesystem information in memory.

The image covers the complete logical `D:` volume, including its boot sector,
FAT, directories, files, free space, and volume metadata. It does not cover the
physical disk MBR or partition table, which are outside the DOS volume.

## Emergency recovery for a damaged volume boot sector

Try `RESTORE.BAT` first. If it reports that `D:` is not a supported volume
after an interrupted recovery, boot from the same CF and run:

```bat
C:\PWMINST\FORCERST.BAT
```

Emergency recovery still verifies the complete saved image before writing,
but deliberately bypasses the current `D:` size and serial check because those
fields may be unreadable. It always targets DOS drive `D:` and requires you to
type `FORCE`. Use it only when the normal restore cannot identify the intended
volume. It writes the boot sector last, verifies the fully restored volume, and
locks DOS access until restart.

Emergency recovery still addresses a DOS logical drive, not a physical disk.
The damaged volume must remain assigned as `D:`. If DOS no longer assigns that
volume a drive letter, this installer cannot reach it; use a physical-disk
imaging tool and the original media instead. Never run `FORCERST.BAT` when a
different device has become `D:`.

## Restore only personal databases

To keep PersonaWare English installed but restore the four pre-install default
databases, close PersonaWare and run:

```bat
C:\PWMINST\RESTDATA.BAT
```

This restores `DEFAULT.ADD`, `DEFAULT.NTD`, `DEFAULT.SCD`, and `DEFAULT.TDD`
from `USERDATA`, with byte-for-byte verification. Any Japanese text previously
entered in those databases is preserved as user data and is not automatically
translated. These files are verified when copied, but the checksummed full
volume image remains the authoritative long-term recovery copy.

## Failure behavior

- Insufficient CF space: imaging is blocked before the backup begins.
- Read, write, close, or read-back error during backup: partial recovery files
  are removed and installation does not begin.
- Existing valid recovery image: installation resumes without overwriting it.
- Incomplete or invalid recovery pair: installation stops and preserves it.
  If power failed during the initial imaging step, do not erase the old CF.
  Prepare another installer CF only after confirming that `D:` was never
  modified.
- Payload corruption on the CF: the affected source CRC check fails before its
  destination is changed.
- File verification failure during installation: copying stops and the full
  original recovery image remains on the CF. DOS file replacement is not
  atomic, so use the full restore after any failed installation.
- Missing, altered, or truncated recovery image: restore is blocked.
- Wrong `D:` volume size or serial: restore is blocked to protect another
  drive.
- Damaged `D:` boot-sector identity: normal restore is blocked; the separately
  confirmed emergency recovery path is available.
- Restore write or read-back failure: keep the CF, restart without accessing
  `D:`, verify the media and power, then retry recovery.

## Verification record

The release workflow rebuilds both 16-bit DOS utilities, reconstructs the CF
archive deterministically from the finished English disk image, checks the
English boot configuration, scans structured PersonaWare data for natural
Japanese text, verifies the payload contents, and tests the backup-first and
non-overwriting guards, resume markers, payload CRCs, boot-sector-last restore,
and emergency-recovery dispatch.

The runtime acceptance test uses PC DOS with a 486-class QEMU target. It checks
that the saved image matches the original logical volume, every installed file
matches its CF source, the installed startup files match the directly booted
English release image, and a full recovery returns the disposable test disk to
its original byte sequence.
The completed run also verified a no-overwrite second installation attempt,
normal recovery after deliberately removing `D:\PW\PW.BAT`, and emergency
recovery after deliberately invalidating the volume boot-sector signature.
Both recovery paths returned the complete 4 MiB test disk to SHA-256
`5149db391d13cfeab330016fcf0edbe6b0d379cbb66a3aed91dbf7684142d52e`.
