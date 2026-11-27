; Reduccion de argumento CORDIC (Grupo 20, OPTIMIZADA)
; Reduce R0 (Q3.12) al intervalo [-pi/2, pi/2] restando/sumando pi.

Reduccion_Argumento
        PUSHM {R1, R2, R3}
        MOVI R3, #0
        LD   R1, PI_DOS_LIM     ; 6434
        LD   R2, PI             ; 12867

REDUCCION_POS
        CMP  R0, R1             ; tita > 6434?
        BRnz REDUCCION_NEG_INIT
        SUB  R0, R0, R2         ; tita -= pi
        XOR  R3, R3, #1
        BRnzp REDUCCION_POS

REDUCCION_NEG_INIT
        LD   R1, NEG_PI_DOS     ; -6433
REDUCCION_NEG
        CMP  R0, R1             ; tita < -6433?
        BRzp FIN
        ADD  R0, R0, R2         ; tita += pi
        XOR  R3, R3, #1
        BRnzp REDUCCION_NEG

FIN
        POPM {R1, R2, R3}
        RET

PI          .FILL #12867
PI_DOS_LIM  .FILL #6434
NEG_PI_DOS  .FILL #-6433

        .END
