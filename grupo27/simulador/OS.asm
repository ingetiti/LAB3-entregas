;==========================================================================
;   SISTEMA OPERATIVO - ISA-G27 - INSTRUCCIONES ESPECIALES PARA GETC OUT
;==========================================================================

    .ORIG x0000

    .BLKW #32

    .FILL os_getc               ;   x20
    .FILL os_out                ;   x21
    .FILL os_puts               ;   x22
    .FILL os_in                 ;   x23
    .FILL os_putsw              ;   x24
    .FILL os_halt               ;   x25

    .BLKW #218


os_getc:
    .FILL x8001                 ;   GETC_INTERNO del simulador (RTI obteniendo un caracter en R0)


os_out:
    .FILL x8002                 ;   OUT_INTERNO del simulador (RTI mostrando un caracter de R0)


os_puts:
    ADD R2, R0, #0
os_puts_loop:
    LDRB R1, R2, #0
    BRz os_puts_rti
    ADD R0, R1, #0
    OUT
    ADD R2, R2, #1
    BR os_puts_loop
os_puts_rti:
    RTI


os_in:
    GETC
    OUT
    RTI


os_putsw:
    ADD R2, R0, #0
os_putsw_loop:
    LDR R1, R2, #0
    BRz os_putsw_rti
    ADD R0, R1, #0
    OUT
    ADD R2, R2, #2
    BR os_putsw_loop
os_putsw_rti
    RTI


os_halt:
    BR #-1


    .END