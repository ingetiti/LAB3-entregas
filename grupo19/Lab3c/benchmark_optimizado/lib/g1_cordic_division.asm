; Modulo: cordic_division   (archivo g1_cordic_division.asm)
;=====================================================================
; Division por CORDIC (modo lineal, vectoring) en punto fijo Q15
; Adaptado y optimizado para la nueva ISA de 16 bits byte-addressable.
;
; CORDIC_DIV
;   ENTRADAS (Q15, entero con signo en complemento a 2):
;     R0 = y0  (dividendo)
;     R1 = x0  (divisor)    con x0 > 0  y  |y0| < x0
;   SALIDA:
;     R0 = y0 / x0 en Q15, rango [-1, 1)   (valor real = R0 / 32768)
;   Conserva R1-R7 (usa pila hardware SP con PUSHM/POPM).
;
; En cada paso se duplica el residuo en vez de achicar x:
;     P' = 2P + d*x        Z' = 2Z - d
;     d = +1 si P <= 0 ;  d = -1 si P > 0
;=====================================================================
CORDIC_DIV
        PUSHM {R2, R4}        ; Apilamos R2 y R4 (SUB evita guardar -x0 en R3)

        MOV   R2, R0          ; R2 = P = y0
        CLR   R0              ; R0 = Z = 0, el resultado

        ; Iteracion 0
        ADDI  R2, R2, #0      ; Actualizar flags con el signo de y0
        BRp   INI_NEG
        ADD   R2, R2, R1      ; y <= 0 : d = +1 -> P = P + x
        DEC   R0              ; z = -d = -1
        BR    INI_LOOP
INI_NEG SUB   R2, R2, R1      ; y > 0 : d = -1 -> P = P - x
        INC   R0              ; z = -d = +1

        ; Iteraciones 1 a 15
INI_LOOP MOVI R4, #15         ; R4 = 15 (ya hicimos la iteracion 0)
LOOP    ADDI  R2, R2, #0      ; Actualizar flags con el signo de P
        BRp   PPOS
        SHL   R2, R2, #1      ; P <= 0 : d = +1
        ADD   R2, R2, R1      ; P = 2P + x
        SHL   R0, R0, #1
        DEC   R0              ; z = 2z - 1
        BR    GOON
PPOS    SHL   R2, R2, #1      ; P > 0 : d = -1
        SUB   R2, R2, R1      ; P = 2P - x
        SHL   R0, R0, #1
        INC   R0              ; z = 2z + 1
GOON    DEC   R4
        BRp   LOOP

        POPM  {R2, R4}        ; Restauramos R2 y R4
        RET

        .END
