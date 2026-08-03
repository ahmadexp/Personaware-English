# Physical IBM PC 110 full-volume installer

Use a machine-specific installer for an actual IBM Palm Top PC 110. It avoids
MiSTer VHD geometry assumptions and avoids replacing the internal PersonaWare
disk one file at a time.

## What it installs

`PW-EN.IMG` is a complete logical PersonaWare volume built for one PC110 from
that machine's verified `D-ORIG.IMG`. PC110 volumes can have different sector
counts and allocation layouts. The builder preserves the captured capacity,
CHS geometry, serial number, factory utilities, and media-specific files. It
adds PersonaWare English 2.0 with Power Management and the DOS Photo Manager.

The PC DOS boot sector requires `IBMBIO.COM` and `IBMDOS.COM` to be the first
two root-directory entries and to occupy consecutive clusters from cluster 2.
The builder creates a fresh FAT12 filesystem using the captured cluster size,
copies the DOS system files first, restores the remaining captured files and
their DOS attributes, and verifies every resulting file byte for byte. An
original PowerQuest image can supply the factory IBM PC DOS 7 boot sector. The
verified factory image uses 4 KiB clusters and BIOS drive `80h`.

The installer addresses the DOS logical drive `D:` through DOS absolute-volume
sector I/O. It does not write the physical disk MBR or partition table. The
target therefore keeps the media-specific partitioning already used by the
physical PC110 while receiving the complete known volume contents.

## Prepare the existing bootable CF

1. Keep the CF that successfully boots DOS as drive `C:`.
2. Do not format it and do not replace its DOS system files.
3. Copy the verified `D-ORIG.IMG` and `D-ORIG.CRC` from the CF to a host and
   build the tailored archive:

   ```sh
   python3 scripts/build_physical_installer_from_backup.py \
     --backup /path/to/D-ORIG.IMG \
     --manifest /path/to/D-ORIG.CRC \
     --factory-pqi /path/to/Personaware.PQI \
     --output build/pc110-tailored-installer \
     --zip build/PersonaWare-English-PC110-Tailored-Installer.zip
   ```

4. Extract the tailored archive onto the CF root, replacing files under
   `PWMINST` when prompted.
5. If `PWMINST` already contains `D-ORIG.IMG`, `D-ORIG.CRC`, or `USERDATA`,
   preserve them. They are not present in the archive and must not be deleted.
6. Connect reliable external power to the PC110 and CF adapter.

The prebuilt 2.0.2 archive is a legacy fixed-layout image containing 8,160
sectors. It safely refuses a different target size and is not a universal
physical-PC110 installer.

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
3. It validates the complete embedded image, checks that the size and serial
   match `D:`, and asks you to type `INSTALL`. It writes all sectors except the
   volume boot sector first, writes the boot sector last, then reads every
   sector back and checks the complete CRC-32.

After verification, the batch file deliberately loops forever. DOS still has
the pre-install FAT and directory state cached, so do not access `D:`. Remove
the CF and restart the PC110 immediately. Leaving the installer CF connected
changes the BIOS drive order and is not supported by the default package.

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

The machine-specific path was tested with an actual PC110 D: capture containing
7,776 sectors and its original PowerQuest image. The PQI independently confirms
the factory 4 KiB FAT12 cluster size, contiguous system files, and BIOS drive
`80h`. A complete DOS installation wrote and read back the tailored volume byte
for byte, and the installed volume reached PC DOS as the only hard disk. The
recovery path then restored every sector to the supplied `D-ORIG.IMG`, also byte
for byte.
