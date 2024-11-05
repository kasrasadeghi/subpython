.equ SYS_kill, 37
.equ SYS_getpid, 20
.equ SIGSTOP, 17

.section    __TEXT,__text,regular,pure_instructions
    .build_version macos, 14, 0    sdk_version 14, 2
    
    .section    __DATA,__data
str1:    .asciz    "Debug point 1\n"
str2:    .asciz    "Debug point 2\n"
str3:    .asciz    "Debug point 3\n"
    
    .section    __TEXT,__text
    .globl    _main                           
    .p2align    2
_main:                                  
    sub    sp, sp, #16
    stp    x29, x30, [sp]             
    mov    x29, sp

    ; First debug point
    adrp    x0, str1@PAGE
    add     x0, x0, str1@PAGEOFF
    bl      _printf
    
    mov    x17, #0xbeef   ; set beef or other funny hex value
    str x17, [sp, #-16]!

    mov x16, #SYS_getpid         // getpid() system call
    svc #0x80                    // Make system call
    mov x1, x0                   // Save PID for kill() call

    mov x0, x1                   // PID to send to (our own)
    mov x1, #SIGSTOP             // Signal to send
    mov x16, #SYS_kill           // kill() system call
    svc #0x80                    // Make system call

    ; Second debug point
    adrp    x0, str2@PAGE
    add     x0, x0, str2@PAGEOFF
    bl      _printf

    ldr x0, [sp], #16  ; return beef

    mov    sp, x29
    ldp    x29, x30, [sp]             
    add    sp, sp, #16
    
    ret
.subsections_via_symbols