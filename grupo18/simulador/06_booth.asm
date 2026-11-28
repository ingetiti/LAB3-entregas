.ORIG x3000

; ============================================================
; 06_BOOTH.ASM
; Multiplicacion Booth de 16 bits con operandos Q7.8.
;
; El archivo tiene dos partes separadas:
;   1. HARNESS (desde INICIO): programa de autocontrol que
;      llama a MUL_Q78 con cada caso de la tabla TESTS y
;      compara las cuatro salidas con los valores esperados.
;   2. RUTINA MUL_Q78 (+ nucleo BOOTH): la implementacion
;      reutilizable. Para usarla en otro programa se copia el
;      bloque desde MUL_Q78 hasta el JMP R7 final de la rutina.
;
; Contrato de MUL_Q78 (ver el detalle junto a la rutina):
;   Entrada: R0 = M, R1 = Q          (Q7.8 con signo)
;   Salida:  R0 = PH, R1 = PL         (producto P en Q15.16)
;            R2 = RES = P[23:8]       (P >> 8 aritmetico, Q7.8)
;            R3 = OVF                 (1 si PH fuera de [-128, 127])
;
; Prueba: 18 casos (tabla TESTS, al final del programa). Los
; valores esperados se calcularon fuera del algoritmo, con
; multiplicacion entera exacta de Python (no con Booth).
; Cualquier diferencia en PH, PL, RES u OVF
; imprime un mensaje de error especifico; el mensaje OK solo
; se imprime si los 18 casos pasaron los 4 controles.
; ============================================================

; Saltear los datos iniciales.
BRnzp INICIO

; La tabla TESTS esta al final del programa: con 18 casos
; (216 bytes) queda fuera del alcance de LEA (-128..+127 bytes),
; por eso se accede mediante este puntero.
TESTS_ADDR:
    .FILL TESTS

REMAIN:
    .FILL #18         ; contador persistente de casos (= casos en TESTS)

INICIO:
    LEA R6, TESTS_ADDR
    LDW R6, R6, #0      ; R6 = direccion de TESTS

TEST_LOOP:
    ; Cargar M y Q del caso actual.
    ; Los offsets de LDW son en BYTES y cada .FILL ocupa 2 bytes:
    ; M=#0, Q=#2, PH=#4, PL=#6, RES=#8, OVF=#10.
    LDW R0, R6, #0      ; R0 = M
    LDW R1, R6, #2      ; R1 = Q

    ; Multiplicar: R0 = PH, R1 = PL, R2 = RES, R3 = OVF.
    ; (Destruye R4, R5 y R7; conserva R6 = puntero al caso.)
    JSR MUL_Q78

    ; Comparar las cuatro salidas con los valores esperados.
    LDW R5, R6, #4
    CMP R0, R5
    BRnp ERROR_PH

    LDW R5, R6, #6
    CMP R1, R5
    BRnp ERROR_PL

    LDW R5, R6, #8
    CMP R2, R5
    BRnp ERROR_RES

    LDW R5, R6, #10
    CMP R3, R5
    BRnp ERROR_OVF

    ; Avanzar al siguiente caso: 6 palabras = 12 bytes.
    AND R5, R5, #0
    ADD R5, R5, #7
    ADD R5, R5, #5
    ADD R6, R6, R5

    ; El contador de casos se guarda en memoria porque MUL_Q78
    ; destruye R4 (contador interno de sus 16 iteraciones).
    LEA R4, REMAIN
    LDW R5, R4, #0
    SUB R5, R5, #1
    STW R5, R4, #0
    CMP R5, #0
    BRp TEST_LOOP

    LEA R0, MSG_OK
    TRAP x22
    HALT

; ------------------------------------------------------------
; Mensajes de error. Cada error identifica qué campo fallo.
; ------------------------------------------------------------

ERROR_PH:
    LEA R0, MSG_PH
    TRAP x22
    HALT

ERROR_PL:
    LEA R0, MSG_PL
    TRAP x22
    HALT

ERROR_RES:
    LEA R0, MSG_RES
    TRAP x22
    HALT

ERROR_OVF:
    LEA R0, MSG_OVF
    TRAP x22
    HALT

MSG_OK:
    .STRINGZ "OK: BOOTH Q7.8 - 18 CASOS"

MSG_PH:
    .STRINGZ "ERROR BOOTH: PH"

MSG_PL:
    .STRINGZ "ERROR BOOTH: PL"

MSG_RES:
    .STRINGZ "ERROR BOOTH: RES"

MSG_OVF:
    .STRINGZ "ERROR BOOTH: OVF"

; ============================================================
; RUTINA MUL_Q78 - multiplicacion Q7.8 x Q7.8 (Booth radix-2)
; ============================================================
; Entrada:
;   R0 = M   primer operando, Q7.8 con signo (valor = raw/256)
;   R1 = Q   segundo operando, Q7.8 con signo
; Salida:
;   R0 = PH  mitad alta del producto exacto P = M*Q (32 bits,
;   R1 = PL  mitad baja   complemento a dos, formato Q15.16)
;   R2 = RES P[23:8] = P >> 8 aritmetico: resultado en Q7.8.
;            Trunca hacia -infinito (no redondea).
;   R3 = OVF 1 si PH no pertenece a [-128, 127] (P no entra en
;            24 bits con signo); 0 si RES es el producto exacto
;            truncado. Con OVF = 1 NO hay saturacion: RES
;            conserva los 16 bits bajos de P >> 8 y NO
;            representa un resultado valido.
; Registros:
;   R4, R5   se destruyen.
;   R6       se conserva (la rutina no lo usa).
;   R7       no se modifica: la rutina no llama a otras
;            subrutinas y retorna con JMP R7. El llamador lo
;            escribe con JSR/JSRR, asi que si necesita su propio
;            R7 debe guardarlo antes de llamar.
; Flags NZP al retornar: reflejan R3. Z si OVF = 0, P si
;   OVF = 1 (ultimo CMP o ADD del epilogo). El llamador puede
;   hacer BRp directamente tras la llamada.
; Costo (medido en el simulador): 55 instrucciones = 110 bytes
;   (1 de entrada + 41 del nucleo + 13 del epilogo). En los 18
;   casos de prueba ejecuta de 241 a 327 instrucciones por
;   llamada (promedio 271,1), JMP R7 incluido.
; ============================================================

MUL_Q78:
    ADD R2, R1, #0       ; el nucleo espera Q en R2
                         ; (sigue directamente en BOOTH)

; ------------------------------------------------------------
; Nucleo Booth radix-2, 16 iteraciones (uso interno de MUL_Q78;
; se entra por caida desde MUL_Q78, no con JSR).
;
; Registros:
;   R0 = M (multiplicando, no se modifica)
;   R1 = A (acumulador / mitad alta del producto)
;   R2 = Q (multiplicador / mitad baja del producto)
;   R3 = Q-1; durante el desplazamiento, mascara de correccion
;   R4 = contador
;   R5 = temporal
;   R6 = preservado
;   R7 = direccion de retorno
;
; En cada iteracion:
;   Q0,Q-1 = 01 -> A = A + M
;   Q0,Q-1 = 10 -> A = A - M
;   Q0,Q-1 = 00 o 11 -> A no cambia
; Luego desplazamiento aritmetico a la derecha de A:Q:Q-1.
;
; Correccion de overflow (necesaria para M = -32768):
;   Booth radix-2 necesita un acumulador de n+1 = 17 bits. Con
;   16 bits, A - M puede desbordarse: con M = -32768, A - M =
;   A + 32768, y si A >= 0 el resultado no entra en 16 bits con
;   signo. El bit 15 queda con el signo equivocado y el SAR lo
;   propaga, arruinando PH y PL. (Para M != -32768 el algoritmo
;   nunca desborda; se verifico con 3157 pares.)
;   Solucion: se detecta el overflow V de la suma/resta
;     suma:  V = ~(A ^ M) & (A ^ R)   (bit 15)
;     resta: V =  (A ^ M) & (A ^ R)   (bit 15)
;   y se deja en R3 la mascara V<<15 (x0000 o x8000). Tras el
;   SAR, el bit 15 de A debe ser el signo REAL (el bit 16 del
;   acumulador de 17 bits) = bit15 XOR V, asi que basta con
;   A = A XOR mascara. Es exactamente un acumulador de 17 bits
;   desplazado una posicion. Q-1 no se necesita en ese momento:
;   se vuelve a calcular a partir de Q0 justo despues.
; ------------------------------------------------------------

BOOTH:
    AND R1, R1, #0       ; A = 0
    AND R3, R3, #0       ; Q-1 = 0

    ; Contador = 16 (7 + 7 + 2).
    AND R4, R4, #0
    ADD R4, R4, #7
    ADD R4, R4, #7
    ADD R4, R4, #2

BOOTH_LOOP:
    ; Examinar el par (Q0, Q-1).
    AND R5, R2, #1
    CMP R5, R3
    BRz BOOTH_NOP       ; 00 o 11: no operar

    CMP R5, #0
    BRz BOOTH_ADD       ; 01: A = A + M

    ; 10: A = A - M, con V = (A ^ M) & (A ^ R).
    XOR R3, R1, R0       ; R3 = A ^ M
    ADD R5, R1, #0       ; R5 = A anterior
    SUB R1, R1, R0       ; A = A - M (16 bits)
    XOR R5, R5, R1       ; R5 = A ^ R
    AND R3, R3, R5       ; bit 15 de R3 = V
    BRnzp BOOTH_VMASK

BOOTH_ADD:
    ; 01: A = A + M, con V = ~(A ^ M) & (A ^ R).
    XOR R3, R1, R0       ; R3 = A ^ M
    NOT R3, R3           ; R3 = ~(A ^ M)
    ADD R5, R1, #0       ; R5 = A anterior
    ADD R1, R1, R0       ; A = A + M (16 bits)
    XOR R5, R5, R1       ; R5 = A ^ R
    AND R3, R3, R5       ; bit 15 de R3 = V

BOOTH_VMASK:
    ; R3 = V << 15: x8000 si hubo overflow, x0000 si no.
    SHR R3, R3, #15
    SHL R3, R3, #15
    BRnzp BOOTH_SHIFT

BOOTH_NOP:
    AND R3, R3, #0       ; sin suma/resta no hay overflow

BOOTH_SHIFT:
    ; Guardar A0 (el overflow no lo afecta: solo cambia el signo).
    AND R5, R1, #1

    ; Desplazamiento aritmetico de A y correccion del signo real.
    SAR R1, R1, #1
    XOR R1, R1, R3

    ; Transferir Q0 a Q-1 y desplazar Q (logico).
    AND R3, R2, #1
    SHR R2, R2, #1

    ; El antiguo A0 pasa a ser el nuevo Q15.
    CMP R5, #0
    BRz BOOTH_NO_HIGH_BIT

    AND R5, R5, #0
    ADD R5, R5, #1
    SHL R5, R5, #15
    OR R2, R2, R5

BOOTH_NO_HIGH_BIT:
    SUB R4, R4, #1
    CMP R4, #0
    BRp BOOTH_LOOP

; ------------------------------------------------------------
; Epilogo de MUL_Q78: al terminar el nucleo, R1 = PH, R2 = PL
; y R0 = M (ya no se necesita). Se arma el contrato de salida.
; ------------------------------------------------------------
BOOTH_DONE:
    ADD R0, R1, #0       ; R0 = PH
    ADD R1, R2, #0       ; R1 = PL

    ; RES = P[23:8] = (PH[7:0] << 8) | (PL >> 8).
    ; SHL descarta PH[15:8]; SHR es logico: entra 0 por la izquierda.
    SHL R2, R0, #8
    SHR R5, R1, #8
    OR R2, R2, R5

    ; OVF: PH esta en [-128, 127] si y solo si sus bits 15..7 son
    ; todos iguales, es decir, si PH >> 7 (aritmetico) vale 0 o -1.
    SAR R4, R0, #7
    AND R3, R3, #0       ; OVF = 0
    CMP R4, #0
    BRz MUL_Q78_END
    CMP R4, #-1
    BRz MUL_Q78_END
    ADD R3, R3, #1       ; OVF = 1

MUL_Q78_END:
    JMP R7

; ------------------------------------------------------------
; Casos de prueba: M, Q, PH, PL, RES y OVF esperados (6 palabras
; = 12 bytes por caso). Valores calculados con multiplicacion
; entera exacta, independiente del algoritmo probado.
; ------------------------------------------------------------
TESTS:
    ; Caso 1: 1.0 * 1.0 (pos x pos)
    ;   1 * 1 = 1
    .FILL x0100    ; M
    .FILL x0100    ; Q
    .FILL x0001    ; PH
    .FILL x0000    ; PL
    .FILL x0100    ; RES
    .FILL x0000    ; OVF

    ; Caso 2: 1.5 * 2.0 (pos x pos)
    ;   1.5 * 2 = 3
    .FILL x0180    ; M
    .FILL x0200    ; Q
    .FILL x0003    ; PH
    .FILL x0000    ; PL
    .FILL x0300    ; RES
    .FILL x0000    ; OVF

    ; Caso 3: -2.5 * 1.25 (neg x pos)
    ;   -2.5 * 1.25 = -3.125
    .FILL xFD80    ; M
    .FILL x0140    ; Q
    .FILL xFFFC    ; PH
    .FILL xE000    ; PL
    .FILL xFCE0    ; RES
    .FILL x0000    ; OVF

    ; Caso 4: max * max (overflow positivo)
    ;   127.996 * 127.996 = 16383
    .FILL x7FFF    ; M
    .FILL x7FFF    ; Q
    .FILL x3FFF    ; PH
    .FILL x0001    ; PL
    .FILL xFF00    ; RES
    .FILL x0001    ; OVF

    ; Caso 5: 2.5 * -1.0 (pos x neg)
    ;   2.5 * -1 = -2.5
    .FILL x0280    ; M
    .FILL xFF00    ; Q
    .FILL xFFFD    ; PH
    .FILL x8000    ; PL
    .FILL xFD80    ; RES
    .FILL x0000    ; OVF

    ; Caso 6: -2.0 * -3.0 (neg x neg)
    ;   -2 * -3 = 6
    .FILL xFE00    ; M
    .FILL xFD00    ; Q
    .FILL x0006    ; PH
    .FILL x0000    ; PL
    .FILL x0600    ; RES
    .FILL x0000    ; OVF

    ; Caso 7: 0 * 18.2 (cero como M)
    ;   0 * 18.2031 = 0
    .FILL x0000    ; M
    .FILL x1234    ; Q
    .FILL x0000    ; PH
    .FILL x0000    ; PL
    .FILL x0000    ; RES
    .FILL x0000    ; OVF

    ; Caso 8: 86.47 * 0 (cero como Q)
    ;   86.4688 * 0 = 0
    .FILL x5678    ; M
    .FILL x0000    ; Q
    .FILL x0000    ; PH
    .FILL x0000    ; PL
    .FILL x0000    ; RES
    .FILL x0000    ; OVF

    ; Caso 9: 2^-8 * 2^-8 (pequeno: RES=0, PL=1)
    ;   0.00390625 * 0.00390625 = 1.52588e-05
    .FILL x0001    ; M
    .FILL x0001    ; Q
    .FILL x0000    ; PH
    .FILL x0001    ; PL
    .FILL x0000    ; RES
    .FILL x0000    ; OVF

    ; Caso 10: -2^-8 * 2^-8 (pequeno negativo: RES=-1/256 por truncamiento)
    ;   -0.00390625 * 0.00390625 = -1.52588e-05
    .FILL xFFFF    ; M
    .FILL x0001    ; Q
    .FILL xFFFF    ; PH
    .FILL xFFFF    ; PL
    .FILL xFFFF    ; RES
    .FILL x0000    ; OVF

    ; Caso 11: 127 * 1 (limite superior sin overflow)
    ;   127 * 1 = 127
    .FILL x7F00    ; M
    .FILL x0100    ; Q
    .FILL x007F    ; PH
    .FILL x0000    ; PL
    .FILL x7F00    ; RES
    .FILL x0000    ; OVF

    ; Caso 12: 64 * 2 = 128 (apenas overflow positivo)
    ;   64 * 2 = 128
    .FILL x4000    ; M
    .FILL x0200    ; Q
    .FILL x0080    ; PH
    .FILL x0000    ; PL
    .FILL x8000    ; RES
    .FILL x0001    ; OVF

    ; Caso 13: -128 * 1 (M=-32768, limite inferior sin overflow)
    ;   -128 * 1 = -128
    .FILL x8000    ; M
    .FILL x0100    ; Q
    .FILL xFF80    ; PH
    .FILL x0000    ; PL
    .FILL x8000    ; RES
    .FILL x0000    ; OVF

    ; Caso 14: -128 * -1 = 128 (M=-32768, overflow)
    ;   -128 * -1 = 128
    .FILL x8000    ; M
    .FILL xFF00    ; Q
    .FILL x0080    ; PH
    .FILL x0000    ; PL
    .FILL x8000    ; RES
    .FILL x0001    ; OVF

    ; Caso 15: -128 * 2^-8 (M=-32768, Q pequeno)
    ;   -128 * 0.00390625 = -0.5
    .FILL x8000    ; M
    .FILL x0001    ; Q
    .FILL xFFFF    ; PH
    .FILL x8000    ; PL
    .FILL xFF80    ; RES
    .FILL x0000    ; OVF

    ; Caso 16: -128 * -128 (M=-32768 y Q=-32768, overflow)
    ;   -128 * -128 = 16384
    .FILL x8000    ; M
    .FILL x8000    ; Q
    .FILL x4000    ; PH
    .FILL x0000    ; PL
    .FILL x0000    ; RES
    .FILL x0001    ; OVF

    ; Caso 17: max * -128 (Q=-32768, overflow negativo)
    ;   127.996 * -128 = -16383.5
    .FILL x7FFF    ; M
    .FILL x8000    ; Q
    .FILL xC000    ; PH
    .FILL x8000    ; PL
    .FILL x0080    ; RES
    .FILL x0001    ; OVF

    ; Caso 18: -64 * 2.0039 (overflow negativo, apenas)
    ;   -64 * 2.00391 = -128.25
    .FILL xC000    ; M
    .FILL x0201    ; Q
    .FILL xFF7F    ; PH
    .FILL xC000    ; PL
    .FILL x7FC0    ; RES
    .FILL x0001    ; OVF

.END