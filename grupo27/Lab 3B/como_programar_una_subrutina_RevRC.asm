

;   COMO PROGRAMAR UNA SUBRUTINA:
;   *****************************

;   Conceptos importantes a tener en cuenta:
;   -   Pueden usar (no es necesario) .EXTERNAL para importar SIMBOLOS desde otros archivos (ver documentacion grupo 8).
;   -   NO UTILIZAR (o utilizar responsablemente) el Registro 6 (R6), ya que interfiere con el sistema de pilas para las
;   interrupciones del simulador (ver documentacion grupo 8). 
;   -   Tener en cuenta que Todo registro tiene que volver de la subrutina, tal y como se lo entrego (responsabilidad
;   callee/caller de la LC3 para subrutinas) (se debe guardar y restaurar los registros). CUIDADO con el Registro 7, que
;   si utilizan una subrutina dentro de la subrutina, este se modifica (lo tienen que guardar para restaurarlo igual que
;   los demas registros usados).
;   -   Como aclaracion peculiar, no es necesario que pongan .ORIG al adjuntar el programa en el simulador del grupo 8
;   (pero si el .END) ya que este solo se necesita en el programa de entrada (programa principal) (ver documentacion grupo 8).



MI_SUBRUTINA                        ;   <-- SIMBOLO (nombre) de la subrutina

                                    ;   AQUI Ya tendriamos cargado en R0, R1, ... la ENTRADA, argumentos de la subrutina
                                    ;   (En nuestro caso, R0 y R1 tendrian los valores requeridos para la operacion en
                                    ;   en sus respectivos formatos Q)

                                    ;   Guardamos el estado inicial de todos los registros que vamos a utilizar
                                    ;   (incluyendo el R7 si se usaran subrutinas dentro de esta subrutina)
                                    ;   (el R0, como sera la SALIDA del resultado, no hace falta que lo guardemos)
    ST R1 guardado_r1               ;
    ST R2 guardado_r2               ;
;   ...

;   ...
;   ...                             ;   AQUI VA EL PROGRAMA DE LA SUBRUTINA...
;   ...

    LD R0 resultado                 ;   Cargamos el resultado en R0 (si es que devolvemos un resultado)

                                    ;   Restauramos los registros que utilizamos a sus estados iniciales
    LD R1 guardado_r1
    LD R2 guardado_r2
;   ...
    RET


                                    ;   ZONA DE DATOS (variables y demas)
resultado       .FILL #0
guardado_r1     .FILL #0
guardado_r2     .FILL #0
; ...           

.END                                ;   IMPORTANTE no olvidarse del .END