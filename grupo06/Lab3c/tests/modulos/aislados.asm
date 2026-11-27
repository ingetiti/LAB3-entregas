.ORIG x3000
.EXTERNAL izquierdo-CALC
.EXTERNAL izquierdo-CALC
.EXTERNAL derecho-CALC
.EXTERNAL circulo_a-A
    LD R3,TABLA
    JSRR R3
    LD R3,OTRO
    JSRR R3
    ADD R2,R0,R1
    HALT
TABLA .FILL izquierdo-CALC
    .FILL izquierdo-CALC
OTRO .FILL derecho-CALC
.END
