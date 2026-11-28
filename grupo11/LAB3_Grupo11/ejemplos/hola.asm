; Ejemplo minimo: imprime un saludo y el resultado de 3 + 4.
; Ensamblar y correr (desde la carpeta principal):
;     python ensamblador.py ejemplos/hola.asm -o ejemplos/hola
;     python simulador.py ejemplos/hola.hex
; Salida esperada:
;     Hola desde el simulador del grupo 11
;     3 + 4 = 7

        .ORIG x3000
        LEA  R0, SALUDO
        PUTS
        MOVI R1, #3
        MOVI R2, #4
        ADD  R3, R1, R2          ; R3 = 7
        LEA  R0, CUENTA
        PUTS
        MOVI R0, #48             ; '0'
        ADD  R0, R0, R3          ; digito del resultado
        OUT
        MOVI R0, #10             ; salto de linea
        OUT
        HALT

SALUDO: .STRINGZ "Hola desde el simulador del grupo 11\n"
CUENTA: .STRINGZ "3 + 4 = "
        .END
