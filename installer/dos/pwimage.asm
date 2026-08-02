; PersonaWare D: volume backup and restore utility.
; The image is an exact sector copy of the DOS D: logical volume.
; Usage: PWIMAGE /B   create C:\PWMINST\D-ORIG.IMG and checksum sidecar
;        PWIMAGE /R   verify and restore the saved D: volume
;        PWIMAGE /F   force recovery only when the D: boot sector is damaged

bits 16
org 0x100

TARGET_DRIVE equ 3
SECTOR_SIZE equ 512
MANIFEST_SIZE equ 20
MAN_SECTORS equ 8
MAN_BPS equ 10
MAN_SERIAL equ 12
MAN_CRC equ 16

start:
    push cs
    pop ds
    push cs
    pop es
    mov word [image_handle], 0xffff
    mov word [manifest_handle], 0xffff
    call parse_mode
    jc usage_error
    cmp al, 'B'
    je backup_mode
    cmp al, 'R'
    je restore_mode
    cmp al, 'F'
    je force_restore_mode
    cmp al, 'V'
    je verify_existing_mode

usage_error:
    mov dx, usage_text
    call print_string
    jmp exit_usage

backup_mode:
    mov dx, backup_intro
    call print_string
    mov ah, 0x0d
    int 0x21
    call inspect_target
    jc target_error
    call backup_paths_clear
    jc backup_exists_error
    call check_backup_space
    jc backup_space_error

    mov ax, [current_sectors]
    mov [manifest_buffer + MAN_SECTORS], ax
    mov word [manifest_buffer + MAN_BPS], SECTOR_SIZE
    mov eax, [current_serial]
    mov [manifest_buffer + MAN_SERIAL], eax

    mov dx, image_path
    xor cx, cx
    mov ah, 0x5b
    int 0x21
    jc backup_exists_error
    mov [image_handle], ax
    mov dword [crc_value], 0xffffffff
    mov word [current_sector], 0

.backup_loop:
    mov ax, [current_sector]
    call read_target_sector
    jc backup_failed
    call update_crc
    mov bx, [image_handle]
    mov dx, sector_buffer
    mov cx, SECTOR_SIZE
    mov ah, 0x40
    int 0x21
    jc backup_failed
    cmp ax, SECTOR_SIZE
    jne backup_failed
    call progress_dot
    inc word [current_sector]
    mov ax, [current_sector]
    cmp ax, [current_sectors]
    jb .backup_loop

    call close_image
    jc backup_failed
    mov eax, [crc_value]
    not eax
    mov [manifest_buffer + MAN_CRC], eax

    mov dx, manifest_path
    xor cx, cx
    mov ah, 0x3c
    int 0x21
    jc backup_failed
    mov [manifest_handle], ax
    mov bx, ax
    mov dx, manifest_buffer
    mov cx, MANIFEST_SIZE
    mov ah, 0x40
    int 0x21
    jc backup_failed
    cmp ax, MANIFEST_SIZE
    jne backup_failed
    call close_manifest
    jc backup_failed
    mov dx, backup_verify_text
    call print_string
    call load_manifest
    jc backup_failed
    mov ax, [current_sectors]
    cmp ax, [manifest_buffer + MAN_SECTORS]
    jne backup_failed
    mov eax, [current_serial]
    cmp eax, [manifest_buffer + MAN_SERIAL]
    jne backup_failed
    call verify_backup_file
    jc backup_failed
    mov dx, backup_success
    call print_string
    jmp exit_success

backup_exists_error:
    mov dx, backup_exists_text
    call print_string
    jmp exit_error

backup_space_error:
    mov dx, backup_space_text
    call print_string
    jmp exit_error

backup_failed:
    call close_all
    mov dx, image_path
    mov ah, 0x41
    int 0x21
    mov dx, manifest_path
    mov ah, 0x41
    int 0x21
    mov dx, backup_failed_text
    call print_string
    jmp exit_error

force_restore_mode:
    mov byte [force_mode], 1
    jmp restore_mode

verify_existing_mode:
    mov dx, verify_existing_text
    call print_string
    call load_manifest
    jc invalid_backup_error
    call verify_backup_file
    jc invalid_backup_error
    call inspect_target
    jc target_error
    mov ax, [current_sectors]
    cmp ax, [manifest_buffer + MAN_SECTORS]
    jne wrong_target_error
    mov eax, [current_serial]
    cmp eax, [manifest_buffer + MAN_SERIAL]
    jne wrong_target_error
    mov dx, existing_valid_text
    call print_string
    jmp exit_success

restore_mode:
    mov dx, restore_intro
    call print_string
    call load_manifest
    jc invalid_backup_error
    call verify_backup_file
    jc invalid_backup_error
    cmp byte [force_mode], 1
    je .force_target
    call inspect_target
    jc target_error
    mov ax, [current_sectors]
    cmp ax, [manifest_buffer + MAN_SECTORS]
    jne wrong_target_error
    mov eax, [current_serial]
    cmp eax, [manifest_buffer + MAN_SERIAL]
    jne wrong_target_error
    jmp .target_ready
.force_target:
    mov dx, force_target_text
    call print_string
.target_ready:
    mov dx, backup_verified_text
    call print_string
    cmp byte [force_mode], 1
    je .confirm_force
    call confirm_restore
    jc restore_cancelled
    jmp .confirmed
.confirm_force:
    call confirm_force_restore
    jc restore_cancelled
.confirmed:

    mov ah, 0x0d
    int 0x21
    mov dx, image_path
    mov ax, 0x3d00
    int 0x21
    jc invalid_backup_error
    mov [image_handle], ax
    mov bx, [image_handle]
    mov dx, boot_sector_buffer
    mov cx, SECTOR_SIZE
    mov ah, 0x3f
    int 0x21
    jc restore_failed
    cmp ax, SECTOR_SIZE
    jne restore_failed
    mov word [current_sector], 1

.restore_loop:
    mov ax, [current_sector]
    cmp ax, [manifest_buffer + MAN_SECTORS]
    jae .restore_boot_sector
    mov bx, [image_handle]
    mov dx, sector_buffer
    mov cx, SECTOR_SIZE
    mov ah, 0x3f
    int 0x21
    jc restore_failed
    cmp ax, SECTOR_SIZE
    jne restore_failed
    mov ax, [current_sector]
    call write_target_sector
    jc restore_failed
    call progress_dot
    inc word [current_sector]
    mov ax, [current_sector]
    cmp ax, [manifest_buffer + MAN_SECTORS]
    jb .restore_loop

.restore_boot_sector:
    mov si, boot_sector_buffer
    mov di, sector_buffer
    mov cx, SECTOR_SIZE / 2
    cld
    rep movsw
    xor ax, ax
    call write_target_sector
    jc restore_failed
    call close_image
    jc restore_failed
    call verify_target_crc
    jc restore_failed
    mov dx, restore_success
    call print_string
    jmp exit_success

restore_cancelled:
    mov dx, restore_cancelled_text
    call print_string
    jmp exit_error

restore_failed:
    call close_all
    mov dx, restore_failed_text
    call print_string
    jmp exit_error

invalid_backup_error:
    call close_all
    mov dx, invalid_backup_text
    call print_string
    jmp exit_error

wrong_target_error:
    mov dx, wrong_target_text
    call print_string
    jmp exit_error

target_error:
    mov dx, target_error_text
    call print_string
    jmp exit_error

inspect_target:
    xor ax, ax
    call read_target_sector
    jc .bad
    cmp word [sector_buffer + 510], 0xaa55
    jne .bad
    cmp word [sector_buffer + 11], SECTOR_SIZE
    jne .bad
    cmp byte [sector_buffer + 38], 0x29
    jne .bad
    mov ax, [sector_buffer + 19]
    test ax, ax
    jnz .have_sectors
    cmp word [sector_buffer + 34], 0
    jne .bad
    mov ax, [sector_buffer + 32]
.have_sectors:
    test ax, ax
    jz .bad
    mov [current_sectors], ax
    mov eax, [sector_buffer + 39]
    mov [current_serial], eax
    clc
    ret
.bad:
    stc
    ret

backup_paths_clear:
    mov dx, image_path
    mov ax, 0x4300
    int 0x21
    jnc .occupied
    cmp ax, 2
    jne .occupied
    mov dx, manifest_path
    mov ax, 0x4300
    int 0x21
    jnc .occupied
    cmp ax, 2
    jne .occupied
    clc
    ret
.occupied:
    stc
    ret

check_backup_space:
    mov dl, 3
    mov ah, 0x36
    int 0x21
    cmp ax, 0xffff
    je .insufficient
    movzx eax, ax
    movzx ebx, bx
    imul eax, ebx
    movzx ebx, cx
    imul eax, ebx
    movzx ebx, word [current_sectors]
    shl ebx, 9
    add ebx, 3145728
    cmp eax, ebx
    jb .insufficient
    clc
    ret
.insufficient:
    stc
    ret

load_manifest:
    mov dx, manifest_path
    mov ax, 0x3d00
    int 0x21
    jc .bad
    mov [manifest_handle], ax
    mov bx, ax
    mov dx, manifest_buffer
    mov cx, MANIFEST_SIZE
    mov ah, 0x3f
    int 0x21
    jc .bad
    cmp ax, MANIFEST_SIZE
    jne .bad
    mov bx, [manifest_handle]
    mov dx, sector_buffer
    mov cx, 1
    mov ah, 0x3f
    int 0x21
    jc .bad
    test ax, ax
    jne .bad
    call close_manifest
    jc .bad

    mov si, manifest_buffer
    mov di, manifest_magic
    mov cx, 8
    repe cmpsb
    jne .bad
    cmp word [manifest_buffer + MAN_BPS], SECTOR_SIZE
    jne .bad
    cmp word [manifest_buffer + MAN_SECTORS], 0
    je .bad
    clc
    ret
.bad:
    call close_manifest
    stc
    ret

verify_backup_file:
    mov dx, image_path
    mov ax, 0x3d00
    int 0x21
    jc .bad
    mov [image_handle], ax
    mov dword [crc_value], 0xffffffff
    mov word [current_sector], 0
.read_loop:
    mov bx, [image_handle]
    mov dx, sector_buffer
    mov cx, SECTOR_SIZE
    mov ah, 0x3f
    int 0x21
    jc .bad
    cmp ax, SECTOR_SIZE
    jne .bad
    call update_crc
    call progress_dot
    inc word [current_sector]
    mov ax, [current_sector]
    cmp ax, [manifest_buffer + MAN_SECTORS]
    jb .read_loop

    mov bx, [image_handle]
    mov dx, sector_buffer
    mov cx, 1
    mov ah, 0x3f
    int 0x21
    jc .bad
    test ax, ax
    jne .bad
    call close_image
    jc .bad
    mov eax, [crc_value]
    not eax
    cmp eax, [manifest_buffer + MAN_CRC]
    jne .bad
    clc
    ret
.bad:
    call close_image
    stc
    ret

verify_target_crc:
    mov dword [crc_value], 0xffffffff
    mov word [current_sector], 0
.verify_loop:
    mov ax, [current_sector]
    call read_target_sector
    jc .bad
    call update_crc
    call progress_dot
    inc word [current_sector]
    mov ax, [current_sector]
    cmp ax, [manifest_buffer + MAN_SECTORS]
    jb .verify_loop
    mov eax, [crc_value]
    not eax
    cmp eax, [manifest_buffer + MAN_CRC]
    jne .bad
    clc
    ret
.bad:
    stc
    ret

confirm_restore:
    mov dx, confirm_text
    call print_string
    mov dx, confirm_buffer
    mov ah, 0x0a
    int 0x21
    cmp byte [confirm_buffer + 1], 3
    jne .cancel
    mov al, [confirm_buffer + 2]
    and al, 0xdf
    cmp al, 'Y'
    jne .cancel
    mov al, [confirm_buffer + 3]
    and al, 0xdf
    cmp al, 'E'
    jne .cancel
    mov al, [confirm_buffer + 4]
    and al, 0xdf
    cmp al, 'S'
    jne .cancel
    clc
    ret
.cancel:
    stc
    ret

confirm_force_restore:
    mov dx, force_confirm_text
    call print_string
    mov dx, confirm_buffer
    mov ah, 0x0a
    int 0x21
    cmp byte [confirm_buffer + 1], 5
    jne .cancel
    mov si, confirm_buffer + 2
    mov di, force_word
    mov cx, 5
.compare:
    mov al, [si]
    and al, 0xdf
    cmp al, [di]
    jne .cancel
    inc si
    inc di
    loop .compare
    clc
    ret
.cancel:
    stc
    ret

read_target_sector:
    push bx
    push cx
    push dx
    mov dx, ax
    mov bx, sector_buffer
    mov cx, 1
    mov al, TARGET_DRIVE
    int 0x25
    pop ax
    pop dx
    pop cx
    pop bx
    ret

write_target_sector:
    push bx
    push cx
    push dx
    mov dx, ax
    mov bx, sector_buffer
    mov cx, 1
    mov al, TARGET_DRIVE
    int 0x26
    pop ax
    pop dx
    pop cx
    pop bx
    ret

update_crc:
    push bx
    push cx
    push si
    mov eax, [crc_value]
    mov si, sector_buffer
    mov cx, SECTOR_SIZE
.crc_byte:
    xor al, [si]
    inc si
    mov bl, 8
.crc_bit:
    shr eax, 1
    jnc .no_polynomial
    xor eax, 0xedb88320
.no_polynomial:
    dec bl
    jnz .crc_bit
    loop .crc_byte
    mov [crc_value], eax
    pop si
    pop cx
    pop bx
    ret

progress_dot:
    cmp byte [current_sector], 0
    jne .done
    mov dl, '.'
    mov ah, 0x02
    int 0x21
.done:
    ret

close_image:
    mov bx, [image_handle]
    cmp bx, 0xffff
    je .not_open
    mov ah, 0x3e
    int 0x21
    mov word [image_handle], 0xffff
    ret
.not_open:
    clc
    ret

close_manifest:
    mov bx, [manifest_handle]
    cmp bx, 0xffff
    je .not_open
    mov ah, 0x3e
    int 0x21
    mov word [manifest_handle], 0xffff
    ret
.not_open:
    clc
    ret

close_all:
    call close_image
    call close_manifest
    ret

parse_mode:
    mov si, 0x81
.skip:
    lodsb
    cmp al, ' '
    je .skip
    cmp al, 9
    je .skip
    cmp al, '/'
    jne .bad
    lodsb
    mov bl, al
.tail:
    lodsb
    cmp al, 13
    je .mode
    cmp al, ' '
    je .tail
    cmp al, 9
    je .tail
    jmp .bad
.mode:
    mov al, bl
    and al, 0xdf
    cmp al, 'B'
    je .ok
    cmp al, 'R'
    je .ok
    cmp al, 'F'
    je .ok
    cmp al, 'V'
    je .ok
.bad:
    stc
    ret
.ok:
    clc
    ret

print_string:
    mov ah, 0x09
    int 0x21
    ret

exit_success:
    mov ax, 0x4c00
    int 0x21
exit_error:
    mov ax, 0x4c01
    int 0x21
exit_usage:
    mov ax, 0x4c02
    int 0x21

usage_text db 'Usage: PWIMAGE /B, /R, /V, or emergency /F', 13, 10, '$'
backup_intro db 'Imaging the complete DOS D: volume to the CF.', 13, 10, '$'
backup_success db 13, 10, 'Backup created and checksummed:', 13, 10
               db 'C:\PWMINST\D-ORIG.IMG', 13, 10, '$'
backup_exists_text db 'Backup image already exists. It was not overwritten.', 13, 10, '$'
backup_space_text db 'The CF does not have enough free space for the full image.', 13, 10, '$'
backup_verify_text db 13, 10, 'Reading the saved image back from the CF for verification.', 13, 10, '$'
backup_failed_text db 13, 10, 'Backup failed. Partial backup files were removed.', 13, 10, '$'
restore_intro db 'Checking the saved image and the current D: volume.', 13, 10, '$'
verify_existing_text db 'Verifying the existing recovery image and D: identity.', 13, 10, '$'
existing_valid_text db 13, 10, 'Existing recovery image is complete and valid.', 13, 10, '$'
backup_verified_text db 13, 10, 'Backup image checksum is valid.', 13, 10, '$'
confirm_text db 13, 10, 'RESTORE WILL REPLACE EVERY SECTOR ON D:', 13, 10
             db 'Type YES and press Enter to continue: $'
force_target_text db 13, 10, 'WARNING: D: volume identity check is bypassed.', 13, 10
                  db 'Emergency recovery will still write only to D:.', 13, 10, '$'
force_confirm_text db 13, 10, 'FORCE RECOVERY WILL REPLACE EVERY SECTOR ON D:', 13, 10
                   db 'Type FORCE and press Enter to continue: $'
force_word db 'FORCE'
restore_success db 13, 10, 'D: matches the original image byte for byte.', 13, 10
                db 'Restart the computer now. Do not access D: first.', 13, 10, '$'
restore_cancelled_text db 13, 10, 'Restore cancelled. D: was not changed.', 13, 10, '$'
restore_failed_text db 13, 10, 'Restore or read-back verification failed.', 13, 10
                    db 'Keep the CF and backup files. Retry after a restart.', 13, 10, '$'
invalid_backup_text db 13, 10, 'Backup image or checksum sidecar is missing or invalid.', 13, 10, '$'
wrong_target_text db 13, 10, 'D: does not match the saved size and volume serial.', 13, 10
                  db 'Restore was blocked to protect the wrong drive.', 13, 10, '$'
target_error_text db 'D: is not a supported FAT volume with 512-byte sectors.', 13, 10, '$'

image_path db 'C:\PWMINST\D-ORIG.IMG', 0
manifest_path db 'C:\PWMINST\D-ORIG.CRC', 0
manifest_magic db 'PWIMG001'
manifest_buffer db 'PWIMG001'
                dw 0
                dw SECTOR_SIZE
                dd 0
                dd 0
confirm_buffer db 8, 0
               times 9 db 0
image_handle dw 0xffff
manifest_handle dw 0xffff
current_sector dw 0
current_sectors dw 0
current_serial dd 0
crc_value dd 0xffffffff
force_mode db 0
sector_buffer times SECTOR_SIZE db 0
boot_sector_buffer times SECTOR_SIZE db 0
