; PersonaWare DOS Photo Manager
;
; Manages the five 190x250 16-colour BMP slots used by the PersonaWare
; launcher. The program is intentionally self-contained and runs as a DOS COM
; utility on the PC 110.

bits 16
org 0x100

start:
    push cs
    pop ds
    push cs
    pop es
    call ensure_gallery

menu_loop:
    mov ax, 0x0003
    int 0x10
    mov dx, menu_text
    call print_string
    call read_key
    cmp al, '1'
    je list_gallery
    cmp al, '2'
    je import_photo
    cmp al, '3'
    je assign_photo
    cmp al, '4'
    je remove_photo
    cmp al, '5'
    je restore_photos
    cmp al, '6'
    je show_help
    cmp al, 'Q'
    je exit_success
    cmp al, 'q'
    je exit_success
    jmp menu_loop

list_gallery:
    call newline
    mov dx, gallery_heading
    call print_string
    mov dx, dta
    mov ah, 0x1a
    int 0x21
    mov dx, gallery_pattern
    xor cx, cx
    mov ah, 0x4e
    int 0x21
    jc .none
.next:
    mov dx, gallery_indent
    call print_string
    mov si, dta + 30
    call print_z
    call newline
    mov ah, 0x4f
    int 0x21
    jnc .next
    jmp wait_for_key
.none:
    mov dx, no_gallery_text
    call print_string
    jmp wait_for_key

import_photo:
    call newline
    mov dx, import_prompt
    call print_string
    call read_line
    cmp byte [input_buffer + 1], 0
    je menu_loop
    mov dx, input_buffer + 2
    call validate_bmp
    jc .invalid
    call find_free_gallery_slot
    jc .full
    mov dx, input_buffer + 2
    mov di, gallery_path
    call copy_file
    jc .copy_failed
    mov dx, import_success
    call print_string
    mov si, gallery_path
    call print_z
    call newline
    jmp wait_for_key
.invalid:
    mov dx, invalid_bmp_text
    call print_string
    jmp wait_for_key
.full:
    mov dx, gallery_full_text
    call print_string
    jmp wait_for_key
.copy_failed:
    mov dx, copy_error_text
    call print_string
    jmp wait_for_key

assign_photo:
    call list_gallery_inline
    mov dx, gallery_number_prompt
    call print_string
    call read_key
    cmp al, '1'
    jb .cancel
    cmp al, '9'
    ja .cancel
    mov [gallery_digit], al
    mov dx, gallery_path
    mov ax, 0x4300
    int 0x21
    jc .missing
    call newline
    mov dx, slot_prompt
    call print_string
    call read_key
    cmp al, '1'
    jb .cancel
    cmp al, '5'
    ja .cancel
    sub al, '1'
    xor ah, ah
    shl ax, 1
    mov bx, ax
    mov di, [slot_paths + bx]
    mov dx, gallery_path
    call copy_file
    jc .copy_failed
    mov dx, assign_success
    call print_string
    jmp wait_for_key
.missing:
    mov dx, missing_photo_text
    call print_string
    jmp wait_for_key
.copy_failed:
    mov dx, copy_error_text
    call print_string
    jmp wait_for_key
.cancel:
    call newline
    jmp menu_loop

remove_photo:
    call list_gallery_inline
    mov dx, remove_prompt
    call print_string
    call read_key
    cmp al, '1'
    jb .cancel
    cmp al, '9'
    ja .cancel
    mov [gallery_digit], al
    mov dx, gallery_path
    mov ah, 0x41
    int 0x21
    jc .missing
    mov dx, remove_success
    call print_string
    jmp wait_for_key
.missing:
    mov dx, missing_photo_text
    call print_string
    jmp wait_for_key
.cancel:
    call newline
    jmp menu_loop

restore_photos:
    call newline
    mov dx, restore_prompt
    call print_string
    call read_key
    cmp al, '0'
    je .all
    cmp al, '1'
    jb .cancel
    cmp al, '5'
    ja .cancel
    sub al, '1'
    xor ah, ah
    mov cx, 1
    jmp .restore
.all:
    xor ax, ax
    mov cx, 5
.restore:
    push cx
    push ax
    shl ax, 1
    mov bx, ax
    mov dx, [stock_paths + bx]
    mov di, [slot_paths + bx]
    call copy_file
    pop ax
    pop cx
    jc .copy_failed
    inc ax
    loop .restore
    mov dx, restore_success
    call print_string
    jmp wait_for_key
.copy_failed:
    mov dx, restore_error_text
    call print_string
    jmp wait_for_key
.cancel:
    call newline
    jmp menu_loop

show_help:
    call newline
    mov dx, help_text
    call print_string
    jmp wait_for_key

list_gallery_inline:
    call newline
    mov dx, gallery_heading
    call print_string
    mov dx, dta
    mov ah, 0x1a
    int 0x21
    mov dx, gallery_pattern
    xor cx, cx
    mov ah, 0x4e
    int 0x21
    jc .none
.next:
    mov dx, gallery_indent
    call print_string
    mov si, dta + 30
    call print_z
    call newline
    mov ah, 0x4f
    int 0x21
    jnc .next
    ret
.none:
    mov dx, no_gallery_text
    call print_string
    ret

find_free_gallery_slot:
    mov al, '1'
.try:
    mov [gallery_digit], al
    mov dx, gallery_path
    mov ax, 0x4300
    int 0x21
    jc .found
    mov al, [gallery_digit]
    inc al
    cmp al, '9' + 1
    jb .try
    stc
    ret
.found:
    clc
    ret

ensure_gallery:
    mov dx, gallery_directory
    mov ah, 0x39
    int 0x21
    ret

validate_bmp:
    mov ax, 0x3d00
    int 0x21
    jc .invalid
    mov bx, ax
    mov dx, bmp_header
    mov cx, 54
    mov ah, 0x3f
    int 0x21
    pushf
    push ax
    mov ah, 0x3e
    int 0x21
    pop ax
    popf
    jc .invalid
    cmp ax, 54
    jne .invalid
    cmp word [bmp_header], 0x4d42
    jne .invalid
    cmp dword [bmp_header + 2], 24118
    jne .invalid
    cmp dword [bmp_header + 10], 118
    jne .invalid
    cmp dword [bmp_header + 18], 190
    jne .invalid
    cmp dword [bmp_header + 22], 250
    jne .invalid
    cmp word [bmp_header + 26], 1
    jne .invalid
    cmp word [bmp_header + 28], 4
    jne .invalid
    cmp dword [bmp_header + 30], 0
    jne .invalid
    clc
    ret
.invalid:
    stc
    ret

; DX points to the source ASCIIZ path and DI to the destination ASCIIZ path.
copy_file:
    mov word [source_handle], 0xffff
    mov word [target_handle], 0xffff
    push dx
    mov ax, 0x3d00
    int 0x21
    pop dx
    jc .failed
    mov [source_handle], ax
    push dx
    mov dx, di
    xor cx, cx
    mov ah, 0x3c
    int 0x21
    pop dx
    jc .failed
    mov [target_handle], ax
.copy_loop:
    mov bx, [source_handle]
    push dx
    mov dx, io_buffer
    mov cx, 4096
    mov ah, 0x3f
    int 0x21
    pop dx
    jc .failed
    test ax, ax
    jz .done
    mov cx, ax
    mov bx, [target_handle]
    push dx
    mov dx, io_buffer
    mov ah, 0x40
    int 0x21
    pop dx
    jc .failed
    cmp ax, cx
    jne .failed
    jmp .copy_loop
.done:
    call close_handles
    clc
    ret
.failed:
    call close_handles
    stc
    ret

close_handles:
    mov bx, [source_handle]
    cmp bx, 0xffff
    je .target
    mov ah, 0x3e
    int 0x21
    mov word [source_handle], 0xffff
.target:
    mov bx, [target_handle]
    cmp bx, 0xffff
    je .done
    mov ah, 0x3e
    int 0x21
    mov word [target_handle], 0xffff
.done:
    ret

read_line:
    mov byte [input_buffer + 1], 0
    mov dx, input_buffer
    mov ah, 0x0a
    int 0x21
    xor bx, bx
    mov bl, [input_buffer + 1]
    mov byte [input_buffer + 2 + bx], 0
    call newline
    ret

read_key:
    mov ah, 0x08
    int 0x21
    push ax
    mov dl, al
    mov ah, 0x02
    int 0x21
    call newline
    pop ax
    ret

wait_for_key:
    mov dx, continue_text
    call print_string
    mov ah, 0x08
    int 0x21
    jmp menu_loop

print_string:
    mov ah, 0x09
    int 0x21
    ret

print_z:
    lodsb
    test al, al
    jz .done
    mov dl, al
    mov ah, 0x02
    int 0x21
    jmp print_z
.done:
    ret

newline:
    mov dx, newline_text
    call print_string
    ret

exit_success:
    mov ax, 0x4c00
    int 0x21

menu_text db 13,10
    db 'PersonaWare DOS Photo Manager 2.0',13,10
    db '================================',13,10,13,10
    db '1  List gallery pictures',13,10
    db '2  Import a picture',13,10
    db '3  Assign a picture to a launcher slot',13,10
    db '4  Remove a gallery picture',13,10
    db '5  Restore original launcher pictures',13,10
    db '6  Help',13,10
    db 'Q  Return to DOS',13,10,13,10
    db 'Selection: $'
gallery_heading db 'Gallery pictures:',13,10,'$'
gallery_indent db '  $'
no_gallery_text db '  No user pictures installed.',13,10,'$'
import_prompt db 'Enter a BMP path, or press Enter to cancel:',13,10,'> $'
import_success db 'Imported as $'
invalid_bmp_text db 'The file must be an uncompressed 190x250 16-colour BMP.',13,10,'$'
gallery_full_text db 'The nine-picture user gallery is full.',13,10,'$'
copy_error_text db 'The picture could not be copied. Check the path and free space.',13,10,'$'
gallery_number_prompt db 'Gallery number (1-9, other key cancels): $'
slot_prompt db 'Launcher slot: 1 Flower, 2 Mountain, 3 Blossom, 4 Tree, 5 Garden: $'
assign_success db 'Picture assigned. Restart PersonaWare to refresh the launcher.',13,10,'$'
missing_photo_text db 'That gallery picture is not installed.',13,10,'$'
remove_prompt db 'Remove gallery number (1-9, other key cancels): $'
remove_success db 'Gallery picture removed. Active slots are unchanged.',13,10,'$'
restore_prompt db 'Restore slot 1-5, or 0 for all original pictures: $'
restore_success db 'Original picture restored. Restart PersonaWare to refresh.',13,10,'$'
restore_error_text db 'The original-picture backup is missing or unreadable.',13,10,'$'
help_text db 'ABOUT THE LAUNCHER GALLERY',13,10,13,10
    db 'PersonaWare uses five BMP pictures across its launcher entries.',13,10
    db 'Imported files are stored safely in C:\PW\PHOTO as USR1.BMP',13,10
    db 'through USR9.BMP. Assigning copies a gallery picture into one',13,10
    db 'of the five active slots. Removing a gallery file never deletes',13,10
    db 'an active slot. Restore can recover any factory picture.',13,10,13,10
    db 'Prepare images as uncompressed 190x250, 16-colour BMP files.',13,10
    db 'Run PWPHOTO again after copying a prepared file to a DOS drive.',13,10,'$'
continue_text db 13,10,'Press any key to continue.$'
newline_text db 13,10,'$'

gallery_directory db 'C:\PW\PHOTO',0
gallery_pattern db 'C:\PW\PHOTO\USR?.BMP',0
gallery_path db 'C:\PW\PHOTO\USR'
gallery_digit db '1'
    db '.BMP',0
stock1 db 'C:\PW\PHOTO\STOCK1.BMP',0
stock2 db 'C:\PW\PHOTO\STOCK2.BMP',0
stock3 db 'C:\PW\PHOTO\STOCK3.BMP',0
stock4 db 'C:\PW\PHOTO\STOCK4.BMP',0
stock5 db 'C:\PW\PHOTO\STOCK5.BMP',0
slot1 db 'C:\PW\SYSTEM\P_KI01.BMP',0
slot2 db 'C:\PW\SYSTEM\P_YAMA01.BMP',0
slot3 db 'C:\PW\SYSTEM\P_HANA02.BMP',0
slot4 db 'C:\PW\SYSTEM\P_KO01.BMP',0
slot5 db 'C:\PW\SYSTEM\P_HANA03.BMP',0
stock_paths dw stock1, stock2, stock3, stock4, stock5
slot_paths dw slot1, slot2, slot3, slot4, slot5

source_handle dw 0xffff
target_handle dw 0xffff
input_buffer db 78, 0
    times 80 db 0
bmp_header times 54 db 0
dta times 43 db 0
io_buffer times 4096 db 0
