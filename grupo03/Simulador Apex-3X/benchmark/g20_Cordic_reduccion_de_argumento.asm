; Reduccion de Argumento CORDIC [LC-3X]
Reduccion_Argumento
    PUSHM #x0E          ; Guarda R1, R2, R3

    ; Inicializamos la bandera
    AND R3, R3, #0

REDUCCION_POS
    LD R1, NPI_DOS
    ADD R2, R0, R1      ; R2 = tita - Pi/2
    BRnz REDUCCION_NEG
    LD R1, NPI
    ADD R0, R0, R1      ; tita = tita - Pi
    NOT R3, R3          ; Niego la bandera
    ADD R3, R3, #2      ; Alterno el estado de la bandera entre 0 y 1
    BRnzp REDUCCION_POS

REDUCCION_NEG
    LD R1, PI_DOS
    ADD R2, R0, R1      ; R2 = tita + Pi/2
    BRzp FIN
    LD R1, PI
    ADD R0, R0, R1      ; tita = tita + Pi
    NOT R3, R3          ; Niego la bandera
    ADD R3, R3, #2      ; Alterno el estado de la bandera entre 0 y 1
    BRnzp REDUCCION_NEG

FIN
    POPM #x0E           ; Restaura R1, R2, R3
    RET

; Constantes
PI      .FILL #12867
NPI     .FILL #-12867
PI_DOS  .FILL #6433
NPI_DOS .FILL #-6434

.END
