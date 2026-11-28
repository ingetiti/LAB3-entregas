; Grupo 09 - Rutinas auxiliares optimizadas para el SQRT independiente (Nueva ISA 16 bits).
; Entrada de SQ9_ROTL32: R0=palabra alta, R1=palabra baja, R2=n (0..31).
; Salida: (R0:R1) rotado 32 bits n posiciones hacia la izquierda.
; Conserva R2,R3,R7.
SQ9_ROTL32
    ADD R2, R2, #0
    BRnz SQH_DONE
    PUSHM {R2, R3}
    ADDI R3, R2, #-16       ; Si n >= 16, intercambiar palabras ahorra 16 pasos
    BRn SQH_LOOP_PREP
    MOV R2, R3
    MOV R3, R0
    MOV R0, R1
    MOV R1, R3
    ADD R2, R2, #0
    BRz SQH_POP
SQH_LOOP_PREP
    CLR R3                  ; R3 = 0 para sumar solo el acarreo con ADC
SQH_LOOP
    SHL R1, R1, #1          ; C = bit 15 de R1, R1[0] = 0
    RLC R0, R0              ; R0[0] = viejo R1[15], C = viejo R0[15]
    ADC R1, R1, R3          ; R1[0] = viejo R0[15]
    DEC R2
    BRp SQH_LOOP
SQH_POP
    POPM {R2, R3}
SQH_DONE
    RET

; Conversor Q15.16 (R0:R1) -> Q7.8 (R0), redondeo a 8 bits.
; Conserva R1..R7.
SQ9_DQ16_TO_Q8
    PUSHM {R1, R2}
    SHL R0, R0, #8          ; parte entera baja a bits 15..8
    LSR R2, R1, #8          ; 8 bits altos de la fraccion a bits 7..0
    OR  R0, R0, R2          ; R0 = Q7.8 truncado
    SHL R2, R1, #8          ; bit 7 de R1 (bit de redondeo) al bit de signo
    BRzp SQH_CIN_OK
    INC R0                  ; redondeo al mas cercano
SQH_CIN_OK
    POPM {R1, R2}
    RET

; Conversor Q7.8 (R0) -> Q15.16 (R0:R1).
; Conserva R2..R7.
SQ9_Q8_TO_DQ16
    SHL R1, R0, #8          ; parte fraccionaria en bits 15..8 de R1
    ASR R0, R0, #8          ; parte entera con extension de signo en R0
    RET
.END
