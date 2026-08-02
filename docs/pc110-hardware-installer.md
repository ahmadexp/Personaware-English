# Physical IBM PC 110 full-volume installer

Use this installer for an actual IBM Palm Top PC 110. It avoids MiSTer VHD
geometry assumptions and avoids replacing the internal PersonaWare disk one
file at a time.

## What it installs

`PW-EN.IMG` is the complete 8,160-sector logical PersonaWare volume taken from
the current release image. It contains the original PC110 volume boot sector,
both FATs, original root-directory and DOS system-file layout, PC DOS files,
and PersonaWare English 2.0 with Power Management and the DOS Photo Manager.

The installer addresses the DOS logical drive `D:` through DOS absolute-volume
sector I/O. It does not write the physical disk MBR or partition table. The
target therefore keeps the media-specific partitioning already used by the
physical PC110 while receiving the complete known volume contents.

## Prepare the existing bootable CF

1. Keep the CF that successfully boots DOS as drive `C:`.
2. Do not format it and do not replace its DOS system files.
3. Extract `PersonaWare-English-2.0.2-PC110-Hardware-Installer.zip` onto its
   root, replacing files under `PWMINST` when prompted.
4. If `PWMINST` already contains `D-ORIG.IMG`, `D-ORIG.CRC`, or `USERDATA`,
   preserve them. They are not present in the archive and must not be deleted.
5. Connect reliable external power to the PC110 and CF adapter.

## Install

Boot from the CF and confirm that it is `C:` and the internal PersonaWare
volume is `D:`. Run:

```bat
C:\PWMINST\INSTALL.BAT
```

The installer performs three stages:

1. It creates and reads back an exact `D-ORIG.IMG`, or verifies the existing
   recovery image without overwriting it.
2. It saves the four current default PersonaWare databases under `USERDATA`.
3. It validates the complete embedded image, checks that `D:` has exactly
   8,160 sectors, and asks you to type `INSTALL`. It writes sectors 1 through
   8,159 first, writes the volume boot sector last, then reads every sector
   back and checks the complete CRC-32.

After verification, the batch file deliberately loops forever. DOS still has
the pre-install FAT and directory state cached, so do not access `D:`. Remove
the CF and restart the PC110 immediately.

## Recovery

To return the entire internal volume to its exact pre-install state, boot the
same CF and run:

```bat
C:\PWMINST\RESTORE.BAT
```

Type `YES` only after confirming that the internal volume is still `D:`. The
recovery image is checksum-verified before writing, the original boot sector
is written last, and the restored volume is read back completely. If the
volume boot sector is too damaged for normal identity checks, `FORCERST.BAT`
provides a separate recovery path requiring the word `FORCE`.

`RESTDATA.BAT` can optionally restore the four saved personal databases after
a successful installation and restart. Those databases may contain Japanese
user-entered text, so they are not restored automatically.

## Acceptance record

The release test installed the complete hardware volume onto a disposable copy
of the original PC110 disk. The resulting full disk matched the release image
byte for byte with SHA-256
`d66065cf935c4ed266660c13594f0cf1e0348391994c97b7c9818a5ebe2a91d0`
and reached PC DOS when booted by itself. The recovery path then restored the
target byte for byte to the original disk SHA-256
`5149db391d13cfeab330016fcf0edbe6b0d379cbb66a3aed91dbf7684142d52e`.
