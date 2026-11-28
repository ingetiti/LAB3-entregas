.ORIG x3000
INICIO:

  ; LEA R0, MENSAJE
    ;PUTS

    ; Inicializar registros
                                MOVI R1,#0                   ; Parte entera
                                MOVI R2,#0                   ; Primer decimal
                                MOVI R4,#0                   ; Estado del punto decimal

LECTURA:

                                GETC

    ; Detectar ENTER (LF)
                                ADD R3,R0,#-10
                                BRZ FIN_LECTURA

    ; Detectar ENTER (CR)
                                ADD R3,R0,#-13
                                BRZ FIN_LECTURA

                                OUT

    ; Detectar punto decimal
                                ADD R3,R0,#-14
                                ADD R3,R3,#-14
                                ADD R3,R3,#-14
                                ADD R3,R3,#-4
                                BRZ PUNTO

    ; Convertir ASCII a numero
                                LD R3,NEG48
                                ADD R0,R0,R3

    ; Validar digito
                                BRN LECTURA

                                ADD R3,R0,#-10
                                BRZP LECTURA

    ; Determinar si es parte entera o decimal
                                ADD R4,R4,#0
                                BRZ PARTE_ENTERA

                                ADD R3,R4,#-1
                                BRP LECTURA

    ; Guardar primer decimal
                                MOV R2,R0
                                ADD R4,R4,#1

                                BRNZP LECTURA

PARTE_ENTERA:

    ; R1 = R1 * 10 + digito
                                ADD R3,R1,R1
                                ADD R5,R3,R3
                                ADD R5,R5,R5
                                ADD R1,R3,R5
                                ADD R1,R1,R0

                                BRNZP LECTURA

PUNTO:

                                ADD R4,R4,#0
                                BRP LECTURA

                                ADD R4,R4,#1
                                BRNZP LECTURA


FIN_LECTURA:

    ; Convertir parte entera a decimas
                                ADD R3,R1,R1
                                ADD R5,R3,R3
                                ADD R5,R5,R5
                                ADD R1,R3,R5

    ; Sumar primer decimal
                                ADD R0,R1,R2

     ; Llamar a la subrutina
                                JSR CALCULAR_SENO

                                ST R0,RESULTADO
                                HALT

;================================
;SUBRUTINA SENO TAYLOR
;================================

;MENSAJE .STRINGZ "Ingrese angulo en grados: "
NEG48:                          .FILL #-48

                                JSR CALCULAR_SENO
                                ST R0,RESULTADO
                                HALT

ANGULO:                         .FILL #900
MULTIPLICADOR:                  .FILL #12868

LIMITE:                         .FILL #3600
LIMITE90:                       .FILL #900
LIMITE180:                      .FILL #1800
LIMITE270:                      .FILL #2700
LIMITE360:                      .FILL #3600

RESULTADO:                      .FILL #0

ENTRADA_ANGULO:                 .FILL #0

GUARDADO_R1:                    .FILL #0
GUARDADO_R2:                    .FILL #0
GUARDADO_R3:                    .FILL #0
GUARDADO_R4:                    .FILL #0
GUARDADO_R5:                    .FILL #0
GUARDADO_R7:                    .FILL #0

SIGNO_CUADRANTE:                .FILL #0

; =====================================================================
; CALCULAR_SENO (version nativa ISA-G11)
;   Entrada: R0 = angulo en decimas de grado (0..3600)
;   Salida : R0 = sen(angulo) en Q3.12   (-1 si el angulo esta fuera de rango)
;   Conserva R1-R5 y R7 (R6 no se usa).
;
; Misma aritmetica que la version LC-3 del grupo 21 (serie de Taylor hasta x^7, con los mismos
; truncamientos en cada paso), por eso el resultado es identico bit a bit en los 3601 angulos.
; Lo que cambia es el metodo: la LC-3 multiplica sumando el multiplicando tantas veces como vale el
; multiplicador y divide restando el divisor de a una vez (unas 220.000 instrucciones para 60 grados).
; Aca se usa multiplicacion por desplazamiento y suma de 32 bits (ADD/ADC, una vuelta por bit),
; division larga con restauracion (16 vueltas) y la division por 4096 es un desplazamiento.
; No hay multiplicacion ni division por hardware.
; =====================================================================
CALCULAR_SENO:
                                ST   R1,GUARDADO_R1
                                ST   R2,GUARDADO_R2
                                ST   R3,GUARDADO_R3
                                ST   R4,GUARDADO_R4
                                ST   R5,GUARDADO_R5
                                ST   R7,GUARDADO_R7

    ; ---- validar 0 <= angulo <= 3600
                                MOV  R0,R0
                                BLT  ST_ERROR
                                LD   R1,LIMITE
                                CMP  R0,R1
                                BSGT ST_ERROR

    ; ---- reducir al primer cuadrante: R2 = angulo reducido, R3 = signo
                                MOVI R3,#1
                                LD   R1,LIMITE90
                                CMP  R0,R1
                                BSLE ST_Q1
                                LD   R1,LIMITE180
                                CMP  R0,R1
                                BSGT ST_Q34
                                SUB  R2,R1,R0               ; Q2: 1800 - angulo
                                BR   ST_CONV
ST_Q34:
                                MOVI R3,#-1
                                LD   R1,LIMITE270
                                CMP  R0,R1
                                BSGT ST_Q4
                                LD   R1,LIMITE180
                                SUB  R2,R0,R1               ; Q3: angulo - 1800
                                BR   ST_CONV
ST_Q4:
                                LD   R1,LIMITE360
                                SUB  R2,R1,R0               ; Q4: 3600 - angulo
                                BR   ST_CONV
ST_Q1:
                                MOV  R2,R0
ST_CONV:
                                ST   R3,SIGNO_CUADRANTE

    ; ---- x = angulo * 12868 / 1800   (radianes en Q3.12)
                                LD   R1,MULTIPLICADOR
                                JSR  ST_UMUL
                                LD   R1,ST_C1800
                                JSR  ST_UDIV
                                ST   R4,ANGULO_Q12

    ; ---- x2 = x*x / 4096
                                MOV  R1,R4
                                MOV  R2,R4
                                JSR  ST_UMUL
                                JSR  ST_DIV4096
                                ST   R4,CUADRADO_Q12

    ; ---- x3 = x2*x / 4096 ;  T2 = -(x3 / 6)
                                MOV  R1,R4
                                LD   R2,ANGULO_Q12
                                JSR  ST_UMUL
                                JSR  ST_DIV4096
                                ST   R4,CUBO_Q12
                                MOVI R5,#0
                                MOVI R1,#6
                                JSR  ST_UDIV
                                NEG  R4,R4
                                ST   R4,T2_Q12

    ; ---- x5 = x3*x2 / 4096 (sin signo) ;  T3 = x5 / 120
                                LD   R1,CUBO_Q12
                                LD   R2,CUADRADO_Q12
                                JSR  ST_UMUL
                                JSR  ST_DIV4096
                                ST   R4,QUINTA_Q12
                                MOVI R5,#0
                                MOVI R1,#120
                                JSR  ST_UDIV
                                ST   R4,T3_Q12

    ; ---- T4 = (T3*x2 / 4096) / 42
                                MOV  R1,R4
                                LD   R2,CUADRADO_Q12
                                JSR  ST_UMUL
                                JSR  ST_DIV4096
                                MOVI R5,#0
                                MOVI R1,#42
                                JSR  ST_UDIV
                                ST   R4,T4_Q12

    ; ---- S = x + T2 + T3 - T4, con el signo del cuadrante
                                LD   R0,ANGULO_Q12
                                LD   R1,T2_Q12
                                ADD  R0,R0,R1
                                LD   R1,T3_Q12
                                ADD  R0,R0,R1
                                SUB  R0,R0,R4
                                LD   R1,SIGNO_CUADRANTE
                                BGE  ST_SIGNO_OK
                                NEG  R0,R0
ST_SIGNO_OK:
                                ST   R0,SENO_Q12
ST_FIN:
                                LD   R1,GUARDADO_R1
                                LD   R2,GUARDADO_R2
                                LD   R4,GUARDADO_R4
                                LD   R5,GUARDADO_R5
                                LD   R7,GUARDADO_R7
                                LD   R3,GUARDADO_R3
                                RET
ST_ERROR:
                                MOVI R0,#-1
                                BR   ST_FIN

; ---------------------------------------------------------------------
; ST_UMUL: R5:R4 = R1 * R2 (sin signo, 16x16 -> 32). Usa R0 y R3.
;   Recorre los bits de R2 desde el mas alto (CLZ salta los ceros de la izquierda).
; ---------------------------------------------------------------------
ST_UMUL:
                                MOVI R4,#0
                                MOVI R5,#0
                                MOV  R0,R2
                                BEQ  ST_UM_FIN
                                CLZ  R3,R0
                                LSL  R0,R0,R3               ; el bit mas alto queda en el bit 15
                                NEG  R3,R3
                                ADD  R3,R3,#15
                                ADD  R3,R3,#1               ; R3 = cantidad de bits significativos
ST_UM_LAZO:
                                ADD  R4,R4,R4               ; producto <<= 1 (32 bits)
                                ADC  R5,R5,R5
                                ADD  R0,R0,R0               ; siguiente bit del multiplicador -> C
                                BCC  ST_UM_SIG
                                ADD  R4,R4,R1               ; producto += multiplicando
                                BCC  ST_UM_SIG
                                ADD  R5,R5,#1
ST_UM_SIG:
                                ADD  R3,R3,#-1
                                BNE  ST_UM_LAZO
ST_UM_FIN:
                                RET

; ---------------------------------------------------------------------
; ST_UDIV: R4 = (R5:R4) / R1, R5 = resto (sin signo; requiere R5 < R1). Usa R3.
; ---------------------------------------------------------------------
ST_UDIV:
                                MOVI R3,#16
ST_UD_LAZO:
                                ADD  R4,R4,R4               ; (resto:cociente) <<= 1
                                ADC  R5,R5,R5
                                CMP  R5,R1
                                BCC  ST_UD_SIG              ; resto < divisor: bit 0
                                SUB  R5,R5,R1
                                ADD  R4,R4,#1               ; bit 1
ST_UD_SIG:
                                ADD  R3,R3,#-1
                                BNE  ST_UD_LAZO
                                RET

; ---------------------------------------------------------------------
; ST_DIV4096: R4 = (R5:R4) >> 12 (16 bits bajos del cociente). Usa R3.
; ---------------------------------------------------------------------
ST_DIV4096:
                                LSL  R5,R5,#4
                                MOVI R3,#12
                                LSR  R4,R4,R3
                                OR   R4,R4,R5
                                RET

T2_Q12:                         .FILL #0
T3_Q12:                         .FILL #0
T4_Q12:                         .FILL #0
ANGULO_Q12:                     .FILL #0
CUADRADO_Q12:                   .FILL #0
CUBO_Q12:                       .FILL #0
QUINTA_Q12:                     .FILL #0
SENO_Q12:                       .FILL #0
ST_C1800:                       .FILL #1800
.END
