; PersonaWare verified file copier for the CF installer.
; Usage: PWCOPY source destination CRC32
;        PWCOPY source destination -
;        PWCOPY /C file CRC32
;        PWCOPY /D file

bits 16
org 0x100

start:
    push cs
    pop ds
    push cs
    pop es
    mov word [source_handle], 0xffff
    mov word [target_handle], 0xffff
    mov byte [target_created], 0
    xor ax, ax
    mov al, [0x80]
    add ax, 0x81
    mov [command_end], ax

    call parse_arguments
    jc usage_error

    cmp byte [arg1], '/'
    jne copy_mode
    mov al, [arg1 + 1]
    and al, 0xdf
    cmp byte [arg1 + 2], 0
    jne usage_error
    cmp al, 'C'
    je check_mode
    cmp al, 'D'
    jne usage_error
    call arguments_finished
    jc usage_error
    call delete_file
    jc operation_error
    jmp success

check_mode:
    mov di, arg3
    call parse_one
    jc usage_error
    call arguments_finished
    jc usage_error
    call parse_crc_argument
    jc usage_error
    cmp byte [expected_crc_present], 1
    jne usage_error
    mov si, arg2
    mov di, arg1
.copy_path:
    lodsb
    stosb
    test al, al
    jnz .copy_path
    call verify_source_crc
    jc operation_error
    jmp success

copy_mode:
    mov di, arg3
    call parse_one
    jc usage_error
    call arguments_finished
    jc usage_error
    call parse_crc_argument
    jc usage_error
    cmp byte [expected_crc_present], 0
    je .copy
    call verify_source_crc
    jc operation_error
.copy:
    call copy_file
    jc operation_error

success:
    mov ax, 0x4c00
    int 0x21

usage_error:
    mov dx, usage_text
    call print_string
    mov ax, 0x4c02
    int 0x21

operation_error:
    mov dx, error_text
    call print_string
    mov ax, 0x4c01
    int 0x21

delete_file:
    mov dx, arg2
    xor cx, cx
    mov ax, 0x4301
    int 0x21
    mov ah, 0x41
    int 0x21
    jnc .done
    cmp ax, 2
    je .done
    stc
    ret
.done:
    clc
    ret

copy_file:
    mov dx, arg1
    mov ax, 0x4300
    int 0x21
    jc .failed
    mov [source_attributes], cx

    mov dx, arg2
    xor cx, cx
    mov ax, 0x4301
    int 0x21

    mov dx, arg1
    mov ax, 0x3d00
    int 0x21
    jc .failed
    mov [source_handle], ax

    mov bx, ax
    mov ax, 0x5700
    int 0x21
    jc .failed
    mov [source_time], cx
    mov [source_date], dx

    mov dx, arg2
    xor cx, cx
    mov ah, 0x3c
    int 0x21
    jc .failed
    mov [target_handle], ax
    mov byte [target_created], 1

.copy_block:
    mov bx, [source_handle]
    mov dx, copy_buffer
    mov cx, 4096
    mov ah, 0x3f
    int 0x21
    jc .failed
    test ax, ax
    jz .copy_complete
    mov cx, ax
    mov bx, [target_handle]
    mov dx, copy_buffer
    mov ah, 0x40
    int 0x21
    jc .failed
    cmp ax, cx
    jne .failed
    jmp .copy_block

.copy_complete:
    mov bx, [target_handle]
    mov cx, [source_time]
    mov dx, [source_date]
    mov ax, 0x5701
    int 0x21
    jc .failed
    call close_handles
    jc .failed

    mov dx, arg2
    mov cx, [source_attributes]
    mov ax, 0x4301
    int 0x21
    jc .failed

    call verify_copy
    jc .failed
    clc
    ret

.failed:
    call close_handles
    cmp byte [target_created], 1
    jne .return_error
    mov dx, arg2
    xor cx, cx
    mov ax, 0x4301
    int 0x21
    mov dx, arg2
    mov ah, 0x41
    int 0x21
.return_error:
    stc
    ret

verify_copy:
    mov word [source_handle], 0xffff
    mov word [target_handle], 0xffff
    mov dx, arg1
    mov ax, 0x3d00
    int 0x21
    jc .verify_failed
    mov [source_handle], ax
    mov dx, arg2
    mov ax, 0x3d00
    int 0x21
    jc .verify_failed
    mov [target_handle], ax

.verify_block:
    mov bx, [source_handle]
    mov dx, verify_source
    mov cx, 2048
    mov ah, 0x3f
    int 0x21
    jc .verify_failed
    mov [verify_count], ax

    mov bx, [target_handle]
    mov dx, verify_target
    mov cx, 2048
    mov ah, 0x3f
    int 0x21
    jc .verify_failed
    cmp ax, [verify_count]
    jne .verify_failed
    test ax, ax
    jz .verified

    mov cx, ax
    mov si, verify_source
    mov di, verify_target
    repe cmpsb
    jne .verify_failed
    jmp .verify_block

.verified:
    call close_handles
    jc .verify_failed
    clc
    ret

.verify_failed:
    call close_handles
    stc
    ret

verify_source_crc:
    mov word [source_handle], 0xffff
    mov word [target_handle], 0xffff
    mov dx, arg1
    mov ax, 0x3d00
    int 0x21
    jc .failed
    mov [source_handle], ax
    mov dword [crc_value], 0xffffffff
.read_block:
    mov bx, [source_handle]
    mov dx, copy_buffer
    mov cx, 4096
    mov ah, 0x3f
    int 0x21
    jc .failed
    test ax, ax
    jz .complete
    mov cx, ax
    call update_crc
    jmp .read_block
.complete:
    call close_handles
    jc .failed
    mov eax, [crc_value]
    not eax
    cmp eax, [expected_crc]
    jne .failed
    clc
    ret
.failed:
    call close_handles
    stc
    ret

update_crc:
    push bx
    push cx
    push si
    mov eax, [crc_value]
    mov si, copy_buffer
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

close_handles:
    mov byte [close_error], 0
    mov bx, [source_handle]
    cmp bx, 0xffff
    je .close_target
    mov ah, 0x3e
    int 0x21
    jnc .source_closed
    mov byte [close_error], 1
.source_closed:
    mov word [source_handle], 0xffff
.close_target:
    mov bx, [target_handle]
    cmp bx, 0xffff
    je .closed
    mov ah, 0x3e
    int 0x21
    jnc .target_closed
    mov byte [close_error], 1
.target_closed:
    mov word [target_handle], 0xffff
.closed:
    cmp byte [close_error], 0
    je .success
    stc
    ret
.success:
    clc
    ret

parse_arguments:
    mov si, 0x81
    mov di, arg1
    call parse_one
    jc .bad
    mov di, arg2
    call parse_one
    jc .bad
    clc
    ret
.bad:
    stc
    ret

parse_crc_argument:
    mov byte [expected_crc_present], 0
    cmp byte [arg3], '-'
    jne .hex
    cmp byte [arg3 + 1], 0
    jne .bad
    clc
    ret
.hex:
    mov si, arg3
    xor eax, eax
    mov cx, 8
.digit:
    mov bl, [si]
    inc si
    cmp bl, '0'
    jb .bad
    cmp bl, '9'
    jbe .decimal
    and bl, 0xdf
    cmp bl, 'A'
    jb .bad
    cmp bl, 'F'
    ja .bad
    sub bl, 'A' - 10
    jmp .append
.decimal:
    sub bl, '0'
.append:
    shl eax, 4
    movzx ebx, bl
    or eax, ebx
    loop .digit
    cmp byte [si], 0
    jne .bad
    mov [expected_crc], eax
    mov byte [expected_crc_present], 1
    clc
    ret
.bad:
    stc
    ret

arguments_finished:
    mov bx, [command_end]
.check:
    cmp si, bx
    jae .done
    lodsb
    cmp al, ' '
    je .check
    cmp al, 9
    je .check
    stc
    ret
.done:
    clc
    ret

parse_one:
.skip_space:
    lodsb
    cmp al, ' '
    je .skip_space
    cmp al, 9
    je .skip_space
    cmp al, 13
    je .missing
    mov cx, 63
.copy_character:
    stosb
    dec cx
    jz .missing
    lodsb
    cmp al, ' '
    je .finished
    cmp al, 9
    je .finished
    cmp al, 13
    je .finished
    jmp .copy_character
.finished:
    xor al, al
    stosb
    clc
    ret
.missing:
    stc
    ret

print_string:
    mov ah, 0x09
    int 0x21
    ret

usage_text db 'Usage: PWCOPY source destination CRC32', 13, 10
           db '       PWCOPY source destination -', 13, 10
           db '       PWCOPY /C file CRC32', 13, 10
           db '       PWCOPY /D file', 13, 10, '$'
error_text db 'Verified file operation failed.', 13, 10, '$'

source_handle dw 0xffff
target_handle dw 0xffff
source_attributes dw 0
source_time dw 0
source_date dw 0
verify_count dw 0
target_created db 0
close_error db 0
expected_crc_present db 0
expected_crc dd 0
crc_value dd 0xffffffff
command_end dw 0
arg1 times 64 db 0
arg2 times 64 db 0
arg3 times 64 db 0
copy_buffer times 4096 db 0
verify_source times 2048 db 0
verify_target times 2048 db 0
