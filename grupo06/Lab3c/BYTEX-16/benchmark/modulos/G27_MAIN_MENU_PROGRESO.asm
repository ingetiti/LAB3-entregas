; Adaptacion BYTEX-16; ver ../cambios_punteros.json y ../procedencia.json.
; Compatibilidad con el nombre publicado por el simulador del Grupo 8.
.EXTERNAL MAIN_MENU_PROGRESO-MAIN_MENU
MAIN_MENU
    ST R1, COMPAT_R1
    ST R7, COMPAT_R7
    LD R1, COMPAT_MENU
    JSRR R1
    LD R1, COMPAT_R1
    LD R7, COMPAT_R7
    RET
COMPAT_R1 .FILL #0
COMPAT_R7 .FILL #0
COMPAT_MENU .FILL MAIN_MENU_PROGRESO-MAIN_MENU
.END
