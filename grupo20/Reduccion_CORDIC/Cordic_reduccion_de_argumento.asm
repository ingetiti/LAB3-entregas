Reduccion_Argumento
;Guardamos los registros auxiliares
ST R1, GUARDADO_R1
ST R2, GUARDADO_R2

;Inicializamos la bandera
AND R3, R3, #0

REDUCCION_POS
LD R1, NPI_DOS
ADD R2, R0, R1 ;R2 = tita - Pi/2
BRnz REDUCCION_NEG
LD R1, NPI
ADD R0, R0, R1 ;tita = tita - Pi
NOT R3, R3 ;Niego la bandera
ADD R3, R3, #2  ;Alterno el estado de la bandera entre 0 y 1 (negativo y positivo)
BRnzp REDUCCION_POS

REDUCCION_NEG
LD R1, PI_DOS
ADD R2, R0, R1 ;R2 = tita + Pi/2
BRzp FIN
LD R1, PI
ADD R0, R0, R1 ;tita = tita + Pi
NOT R3, R3 ;Niego la bandera
ADD R3, R3, #2 ;Alterno el estado de la bandera entre 0 y 1 (negativo y positivo)
BRnzp REDUCCION_NEG

FIN
;Restauramos los registros auxiliares
LD R1, GUARDADO_R1
LD R2, GUARDADO_R2

RET ;Regresa al programa principal (a la instruccion despues del JSR)

;Constantes
TITA .FILL #25081 ;6.12 rad (Resta Pi dos veces -> R0=-653, R3=0)
PI .FILL #12867
NPI .FILL #-12867
PI_DOS .FILL #6433
NPI_DOS .FILL #-6434

GUARDADO_R1 .FILL #0
GUARDADO_R2 .FILL #0

.END
