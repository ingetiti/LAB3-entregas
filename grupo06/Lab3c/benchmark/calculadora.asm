; ISA3C local. Ensamblar con -I benchmark/modulos y ejecutar el .obj con simulador.
; Los comentarios historicos siguientes pertenecen al archivo de origen del Grupo 27.
; Adaptacion ISA3C; ver ../cambios_punteros.json y ../procedencia.json.

.ORIG x3000
BR main

;   ============================================================================
;       Programa de ENTRADA para pruebas del menu
;       *****************************************
;   ============================================================================
;
;   Metodologia:
;       Se puede probar el menu, de ditintas maneras:
;       -   Prueba de unicamente la interfaz (SIN SUBRUTINAS EXTERNAS).
;       -   Prueba de unicamente la interfaz en modo automatico (SIN SUBRUTINAS EXTERNAS).
;       -   Prueba con subrutinas externas.
;       -   Prueba con subrutinas externas en modo automatico.
;      
;
;   (!) Para que se carguen correctamente las SUBRUTINAS EXTERNAS, tiene que estar *logeado*
;   con alguna cuenta (ya sea de grupo o administrador) y darle a *Ensamblar*.
;
;   (!) Para cambiar entre prueba SIN y CON SUBRUTINAS EXTERNAS, comente y descomente las
;   siguientes lineas:

; .EXTERNAL MAIN_MENU-MAIN_MENU                               ; <- Pruebas unicamente la interfaz.
; sub_main_menu       .FILL MAIN_MENU-MAIN_MENU               ; <- *

.EXTERNAL MAIN_MENU_PROGRESO-MAIN_MENU                      ; <- Pruebas con subrutinas externas.
sub_main_menu       .FILL MAIN_MENU_PROGRESO-MAIN_MENU      ; <- * 


;   (!) Para cambiar entre modo Mostrar interfaz, y modo Automatico, comente y descomente las
;   siguientes lineas:

main
    AND R0 R0 #0                    ; <- 0 es nullptr (osea mostrar el menu normalmente)
    ; LEA R0 programa_del_menu        ; <- ptr (es para que automaticamente corra el programa de abajo)

    LD R1 sub_main_menu
    JSRR R1
    HALT


;   (i) Bloque de Operaciones para correr AUTOMATICAMENTE en el menu:
;   (vea archivo 'como_programar_bloque_automatizacion.asm' el grupo 27 para mas info).

programa_del_menu
    .FILL   #1      ;   modo verboso (muestra todos los valores por consola)
    
    .FILL   #7      ;   MULTIPLICACION
    .FILL   #2      ;   MULTIPLICACION BOOTH
    .FILL   x0500   ;   (Q7.8) valor a (5)
    .FILL   xF400   ;   (Q7.8) valor b (-12)
    .FILL   #0      ;   (Q7.8) espacio para el resultado.
    
    .FILL   #4      ;   SQRT
    .FILL   #1      ;   SQRT NEWTONRAPHSON
    .FILL   x0002   ;   
    .FILL   x0000   ;   (Q15.16 usa 2 WORD) valor a (2.0)
    .FILL   #0      ;   
    .FILL   #0      ;   (Q15.16 usa 2 WORD) espacio para resultado.

    .FILL   #2      ;   COS TABLE
    .FILL   x1921   ;   (Q3.12) valor a (1.5708)
    .FILL   #0      ;   (Q1.14) espacio para el resultado.

    .FILL   #13     ;   SALIR



.END
