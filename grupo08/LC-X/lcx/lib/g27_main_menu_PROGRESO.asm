.EXTERNAL g27_getval-GETVAL
.EXTERNAL g27_outval-OUTVAL
.EXTERNAL g27_pause-PAUSE
;   El enlazador ubica los modulos en el orden de los .EXTERNAL (a lo ancho):
;   declarar aca las subrutinas que usan GETVAL y OUTVAL las deja todas
;   justo despues del menu, al alcance de JSR.
.EXTERNAL g27_todec-TODEC
.EXTERNAL g27_getline-GETLINE
.EXTERNAL g27_fromdec-FROMDEC
.EXTERNAL g27_to_qm_n-TO_QM_N
.EXTERNAL g27_from_qm_n-FROM_QM_N
.EXTERNAL g27_circlsh-CIRCLSH
.EXTERNAL g27_getval_buffer-BUFFER

;   ============================================================================
;   Subrutina: MAIN_MENU (LC-X)
;       Interfaz que permite seleccionar las funciones de la calculadora asi
;       como sus operandos, y llama a las subrutinas de dichas funciones.
;
;       Maquina de estados que recorre NODOS. Hay dos clases de nodo:
;       - Menu: 1 palabra (s * 16 + maximo) y el texto del menu (.STRINGP),
;         que MM_TEXTO imprime expandiendo tres marcas (ver MM_TEXTO).
;         Las opciones validas son las teclas hexadecimales 0..maximo (en
;         minuscula o mayuscula), y la opcion v lleva al nodo MM_TABLA[s + v].
;       - Hoja (operacion): la direccion de la subrutina, los formatos y el
;         titulo (.STRINGP). Formatos: bits 0-4 = n + 1 del operando a,
;         bits 5-9 = n + 1 del operando b, bits 10-14 = n + 1 del resultado
;         (n de Qm.n; 0 = no hay).
;       Un nodo 0 es salir. Una hoja se reconoce por su primera palabra (una
;       direccion de x0200 en adelante); la de un menu es menor que x0200.
;
;   -> INPUT  [R0] nullptr (x0000) o puntero a vector de operaciones.
;
;       Si la entrada es nullptr, se ejecutara el menu con las entradas por teclado con
;       normalidad.
;       Un vector de operaciones consiste de datos de memoria que se ejecutaran como
;       opearaciones del menu (seleccionar operacion, dato_a, dato_b, etc...).
;       Se espera que el primer dato sea la bandera de verbosidad (0, para modo silencioso
;       y 1 para modo verboso).
;   Conserva todos los registros.
;
;   El codigo esta al final del archivo, junto a GETVAL, OUTVAL y PAUSE.
;   ============================================================================

.EXTERNAL g1_cordic_division-CORDIC_DIV                         ; DIV CORDIC (Q15, Q15 -> Q15)
.EXTERNAL g3_MultiplicacionSHIFTandADD-MULTIPLICARSHIFTANDADD   ; MULT SHIFT ADD (Q8, Q8 -> DQ16)
.EXTERNAL g4_potencia-EXP_RAPIDA                                ; POW EXPBIN (int, int -> int)
.EXTERNAL g5_Mul_Sucesiva_POW-Mul_Sucesiva_POW                  ; POW MULTS (Q8, int -> Q8)
.EXTERNAL g6_EXP-EXP_Q3_12                                      ; EXP (Q12 -> Q8)
.EXTERNAL g7_mcm-MCM                                            ; MCM (int, int -> int)
.EXTERNAL g7_mcd-MCD                                            ; MCD (int, int -> int)
.EXTERNAL g9_sqrt_nr_dq16-SQRT_NR_DQ16                          ; SQRT NEWTONRAPHSON (DQ16 -> DQ16)
.EXTERNAL g10_division_larga-DIV_LONG                           ; DIV LONG (Q8, Q8 -> Q8)
.EXTERNAL g11_CORDICLog-CORDIC_LOG_BASE                         ; LOG CORDIC (Q12 -> Q12)
.EXTERNAL g12_subrutina_grupo_12-DIV_NEWTON                     ; DIV NEWTONRAPHSON (Q8, Q8 -> Q8)
.EXTERNAL g14_log_borchardt_q8_7-LN_GENERAL_Q8_7                ; LOG BORCHARDT (Q7 -> Q7)
.EXTERNAL g15_G15_Q312_Q78-G15_Q312_Q78                         ; Q3.12 to Q7.8 (Q12 -> Q8)
.EXTERNAL g18_booth-MULT_BOOTH                                  ; MULT BOOTH (Q8, Q8 -> Q8)
.EXTERNAL g19_cordic_multiplicacion-CORDIC_MUL                  ; MULT CORDIC (Q8, Q8 -> Q8)
.EXTERNAL g20_Cordic_reduccion_de_argumento-Reduccion_Argumento ; REDUCCION DE ARGUMENTO (CORDIC) (Q12 -> Q12)
.EXTERNAL g21_senotaylor_subrutina-CALCULAR_SENO                ; SIN TAYLOR (int -> Q12)
.EXTERNAL g22_Tabla_SIN_y_COS-SENO_TABLA                        ; SIN TABLE (Q12 -> Q14)
.EXTERNAL g22_Tabla_SIN_y_COS-COSENO_TABLA                      ; COS TABLE (Q12 -> Q14)
.EXTERNAL g23_modulo_sqrt_nr-SQRT_NR                            ; SQRT NONRES (Q8 -> Q9)
.EXTERNAL g24_conversor_lc3_max-SUB_BASE_HEX                    ; BASE HEX (int -> noresult)
.EXTERNAL g24_conversor_lc3_max-SUB_BASE_BIN                    ; BASE BIN (int -> noresult)
.EXTERNAL g30_seno_cheb_pade-SEN_CHEB_PADE                      ; SIN CHEBYSHEV-PADE (Q12 -> Q14)


;   ==- Formatos de las hojas (n + 1 de a, b y resultado) -=====================
;   x0001 int -> nada          x3401 int -> Q3.12        x0421 int, int -> int
;   x340D Q3.12 -> Q3.12       x240D Q3.12 -> Q7.8       x3C0D Q3.12 -> Q1.14
;   x2008 Q8.7 -> Q8.7         x2429 Q7.8, int -> Q7.8   x2809 Q7.8 -> Q6.9
;   x2529 Q7.8, Q7.8 -> Q7.8   x4210 Q0.15 x2 -> Q0.15   x4411 Q15.16 -> Q15.16
;   x4529 Q7.8, Q7.8 -> Q15.16

;   ==- NODOS -=================================================================
MM_ARGRD        .FILL g20_Cordic_reduccion_de_argumento-Reduccion_Argumento
                .FILL x340D
                .STRINGP "\n\n==REDUCCION DE ARGUMENTO (CORDIC)==\n"

MM_SIN          .FILL x0022         ; s = 2, maximo = 2
                .STRINGP "$C==#%C#%D#CHEBYSHEV-PADE\n"
MM_SIN_TAYLOR   .FILL g21_senotaylor_subrutina-CALCULAR_SENO
                .FILL x3401
                .STRINGP "\n\n==SENO TRIGONOMETRICO (TAYLOR)==\n"
MM_SIN_TABLE    .FILL g22_Tabla_SIN_y_COS-SENO_TABLA
                .FILL x3C0D
                .STRINGP "\n\n==SENO TRIGONOMETRICO (TABLE)==\n"
MM_SIN_CHEB     .FILL g30_seno_cheb_pade-SEN_CHEB_PADE
                .FILL x3C0D
                .STRINGP "\n\n==SENO TRIGONOMETRICO (CHEVYSHEV-PADE)==\n"

MM_COS          .FILL g22_Tabla_SIN_y_COS-COSENO_TABLA
                .FILL x3C0D
                .STRINGP "\n\n==COSENO TRIGONOMETRICO (TABLE)==\n"

MM_BASE         .FILL x0061         ; s = 6, maximo = 1
                .STRINGP "$G==#%G#%H\n"
MM_BASE_HEX     .FILL g24_conversor_lc3_max-SUB_BASE_HEX
                .FILL x0001
                .STRINGP "\n\n==EXPRESION CON BASE (HEX)==\n"
MM_BASE_BIN     .FILL g24_conversor_lc3_max-SUB_BASE_BIN
                .FILL x0001
                .STRINGP "\n\n==EXPRESION CON BASE (BIN)==\n"

MM_SQRT         .FILL x0081         ; s = 8, maximo = 1
                .STRINGP "$I==#%I#%J\n"
MM_SQRT_NONRES  .FILL g23_modulo_sqrt_nr-SQRT_NR
                .FILL x2809
                .STRINGP "\n\n==RAIZ CUADRADA (NON RESTORING)==\n"
MM_SQRT_NR      .FILL g9_sqrt_nr_dq16-SQRT_NR_DQ16
                .FILL x4411
                .STRINGP "\n\n==RAIZ CUADRADA (NEWTON-RAPHSON)==\n"

MM_EXP          .FILL g6_EXP-EXP_Q3_12
                .FILL x240D
                .STRINGP "\n\n==EXPONENCIACION==\n"

MM_POW          .FILL x00B1         ; s = 11, maximo = 1
                .STRINGP "$L==#%L#EXP BINARIA\n"
MM_POW_MULTS    .FILL g5_Mul_Sucesiva_POW-Mul_Sucesiva_POW
                .FILL x2429
                .STRINGP "\n\n==POTENCIACION (MULTIPLICACIONES SUCESIVAS)==\n"
MM_POW_EXPBIN   .FILL g4_potencia-EXP_RAPIDA
                .FILL x0421
                .STRINGP "\n\n==POTENCIACION (EXPONENCIACION BINARIA)==\n"

MM_MULT         .FILL x00D2         ; s = 13, maximo = 2
                .STRINGP "$N==#%N#%O#%P\n"
MM_MULT_CORDIC  .FILL g19_cordic_multiplicacion-CORDIC_MUL
                .FILL x2529
                .STRINGP "\n\n==MULTIPLICACION (CORDIC)==\n"
MM_MULT_BASIC   .FILL g3_MultiplicacionSHIFTandADD-MULTIPLICARSHIFTANDADD
                .FILL x4529
                .STRINGP "\n\n==MULTIPLICACION (BASIC)==\n"
MM_MULT_BOOTH   .FILL g18_booth-MULT_BOOTH
                .FILL x2529
                .STRINGP "\n\n==MULTIPLICACION (BOOTH)==\n"

MM_DIV          .FILL x0102         ; s = 16, maximo = 2
                .STRINGP "$Q==#%Q#%R#%S\n"
MM_DIV_LONG     .FILL g10_division_larga-DIV_LONG
                .FILL x2529
                .STRINGP "\n\n==DIVISION (LONG DIVISION)==\n"
MM_DIV_NR       .FILL g12_subrutina_grupo_12-DIV_NEWTON
                .FILL x2529
                .STRINGP "\n\n==DIVISION (NEWTON-RAPHSON)==\n"
MM_DIV_CORDIC   .FILL g1_cordic_division-CORDIC_DIV
                .FILL x4210
                .STRINGP "\n\n==DIVISION (CORDIC)==\n"

MM_LOG          .FILL x0131         ; s = 19, maximo = 1
                .STRINGP "$T#%T#%U\n"
MM_LOG_BORCH    .FILL g14_log_borchardt_q8_7-LN_GENERAL_Q8_7
                .FILL x2008
                .STRINGP "\n\n==LOGARITMO== (BORCHARDT)\n"
MM_LOG_CORDIC   .FILL g11_CORDICLog-CORDIC_LOG_BASE
                .FILL x340D
                .STRINGP "\n\n==LOGARITMO== (CORDIC)\n"

MM_MCD          .FILL g7_mcd-MCD
                .FILL x0421
                .STRINGP "\n\n==MAXIMO COMUN DIVISOR==\n"

MM_MCM          .FILL g7_mcm-MCM
                .FILL x0421
                .STRINGP "\n\n==MINIMO COMUN MULTIPLO==\n"

MM_QTOQ         .FILL g15_G15_Q312_Q78-G15_Q312_Q78
                .FILL x240D
                .STRINGP "\n\n==Q3.12 -> Q7.8==\n"

;   Los textos de los submenus usan marcas que MM_TEXTO expande; la letra
;   que sigue a $ o % elige el nodo MM_TABLA[letra - 65] (C = 2, ..., U = 20).
;   Solo el modo interactivo imprime menus.

;   ==- Nodo inicial -==========================================================
MM_INICIO   .FILL x018D             ; s = 24, maximo = 13
            .STRINGP "\n\n==CALCULADORA ARQUITECTURA 2026==\n[7] x      [8] /      [9] Log    [a] MCD\n[4] sqrt   [5] exp    [6] pow    [b] MCM\n[1] sin    [2] cos    [3] base   [c] Q3.12 -> Q7.8\n[0] Reduccion de argumento       [d] (salir)\n"


;   ==- Tabla de nodos -========================================================
;   0-23: el vector de operaciones (indice de operacion); cada submenu usa
;   una parte de ella. 24-37: las opciones del menu inicial.
            .FILL MM_INICIO         ; (el nodo inicial)
MM_TABLA    .FILL #0                ; 0 salir
            .FILL MM_ARGRD          ; 1
            .FILL MM_SIN_TAYLOR     ; 2  (submenu seno: 2-4)
            .FILL MM_SIN_TABLE      ; 3
            .FILL MM_SIN_CHEB       ; 4
            .FILL MM_COS            ; 5
            .FILL MM_BASE_HEX       ; 6  (submenu base: 6-7)
            .FILL MM_BASE_BIN       ; 7
            .FILL MM_SQRT_NONRES    ; 8  (submenu raiz: 8-9)
            .FILL MM_SQRT_NR        ; 9
            .FILL MM_EXP            ; 10
            .FILL MM_POW_MULTS      ; 11 (submenu potencia: 11-12)
            .FILL MM_POW_EXPBIN     ; 12
            .FILL MM_MULT_CORDIC    ; 13 (submenu multiplicacion: 13-15)
            .FILL MM_MULT_BASIC     ; 14
            .FILL MM_MULT_BOOTH     ; 15
            .FILL MM_DIV_LONG       ; 16 (submenu division: 16-18)
            .FILL MM_DIV_NR         ; 17
            .FILL MM_DIV_CORDIC     ; 18
            .FILL MM_LOG_BORCH      ; 19 (submenu logaritmo: 19-20)
            .FILL MM_LOG_CORDIC     ; 20
            .FILL MM_MCD            ; 21
            .FILL MM_MCM            ; 22
            .FILL MM_QTOQ           ; 23
            .FILL MM_ARGRD          ; 24 menu inicial: [0]
            .FILL MM_SIN            ; [1]
            .FILL MM_COS            ; [2]
            .FILL MM_BASE           ; [3]
            .FILL MM_SQRT           ; [4]
            .FILL MM_EXP            ; [5]
            .FILL MM_POW            ; [6]
            .FILL MM_MULT           ; [7]
            .FILL MM_DIV            ; [8]
            .FILL MM_LOG            ; [9]
            .FILL MM_MCD            ; [a]
            .FILL MM_MCM            ; [b]
            .FILL MM_QTOQ           ; [c]
            .FILL #0                ; [d] salir

MAIN_MENU
        PUSH                    ; R0-R5 y R7
        MOVI  R1, #1            ; verbose = 1
        ADD   R4, R0, #0        ; R4 = cursor_de_op
        BRz   MM_LOCAL
        LDR   R1, R4, #0        ; verbose = cursor.peek()
        ADD   R4, R4, #2
MM_LOCAL
        PUSH  R1                ; [R6] = verbose
        ADD   R4, R4, #0
        BRz   MM_INTERACTIVO

;   ==- Modo automatico: una operacion por vuelta -=============================
MM_AUTO LDR   R0, R4, #0        ; indice de operacion
        LEA   R5, MM_TABLA
        LDRX  R5, R5, R0        ; R5 = hoja = tabla[indice]
        BRz   MM_FIN            ; 0: salir
        LDR   R3, R6, #0        ; verbose
        BRz   MM_AUTO_AB
        ADD   R0, R5, #4
        PUTSP                   ; print(hoja.titulo)
        LDR   R0, R4, #1
        LDR   R1, R4, #2
        LDR   R2, R5, #1        ; formato de a en los bits 0-4
        JSR   MM_MUESTRA        ; print("(Qm.n) " + a)
        ADD   R0, R1, #0
        AND   R1, R1, #0        ; (b, 0): b nunca es Q15.16
        RSHFL R2, R2, #5        ; formato de b
        JSR   MM_MUESTRA        ; print("(Qm.n) " + b)
MM_AUTO_AB
        LDR   R0, R4, #1        ; a
        LDR   R1, R4, #2        ; b

;   ==- Llamada a la subrutina de la hoja R5, con [R0, R1] = (a, b) -===========
MM_EJECUTA
        PUSH  R5
        LDR   R5, R5, #0
        JSRR  R5                ; [R0, R1] = hoja.subrutina(a, b)
        POP   R5
        LDR   R2, R5, #1
        RSHFL R2, R2, #10       ; formato del resultado
        LDR   R3, R6, #0        ; verbose (1 en modo interactivo)
        BRz   MM_GUARDA
        JSR   MM_MUESTRA        ; print("(Qm.n) " + resultado)
MM_GUARDA
        ADD   R4, R4, #0
        BRz   MM_PAUSA          ; modo interactivo
        CMP   R2, #17
        BRz   MM_GUARDA_DQ      ; Q15.16: se guardan las dos palabras
        AND   R1, R1, #0
MM_GUARDA_DQ
        STR   R0, R4, #3
        STR   R1, R4, #4
        ADD   R4, R4, #10       ; siguiente operacion (5 palabras)
        BR    MM_AUTO

;   ==- Modo interactivo -======================================================
MM_PAUSA
        JSR   g27_pause-PAUSE
MM_INTERACTIVO
        LEA   R5, MM_TABLA
        LDR   R5, R5, #-1       ; nodo = inicio
MM_MENU                         ; R5 = nodo de menu
        ADD   R0, R5, #2
        JSR   MM_TEXTO          ; print(nodo.texto)
        LDR   R3, R5, #0        ; s * 16 + maximo
MM_TECLA
        GETC                    ; [R0] tecla (sin eco)
        MOVI  R1, #-48
        ADD   R1, R0, R1        ; valor = tecla - '0'
        CMP   R1, #10
        BRNC  MM_TECLA_RANGO    ; '0'-'9'
        MOVI  R2, #32
        OR    R0, R0, R2        ; a minuscula
        MOVI  R1, #-87
        ADD   R1, R0, R1        ; valor = tecla - 'a' + 10
        SUB   R2, R1, #10
        CMP   R2, #6
        BRC   MM_TECLA          ; no es 'a'-'f'
MM_TECLA_RANGO
        AND   R2, R3, #15       ; maximo
        CMP   R2, R1
        BRNC  MM_TECLA          ; valor > maximo
        RSHFL R2, R3, #4
        ADD   R2, R2, R1        ; s + valor
        LEA   R1, MM_TABLA
        LDRX  R5, R1, R2        ; nodo = tabla[s + valor]
        BRz   MM_FIN            ; salir
        LDR   R3, R5, #0
        RSHFL R3, R3, #9
        BRz   MM_MENU           ; otro menu
        ADD   R0, R5, #4        ; hoja:
        PUTSP                   ; print(hoja.titulo)
        LDR   R3, R5, #1        ; formatos
        LEA   R0, MM_A
        ADD   R2, R3, #0
        JSR   MM_PIDE           ; [R0, R1] = a (siempre hay a)
        RSHFL R2, R3, #5
        LSHF  R7, R2, #11
        BRz   MM_EJECUTA        ; no hay b
        PUSH  R0
        LEA   R0, MM_B
        JSR   MM_PIDE
        ADD   R1, R0, #0        ; b
        POP   R0
        BR    MM_EJECUTA

MM_FIN  POP   R1                ; descarta verbose
        POPR                    ; restaura R0-R5 y R7, y vuelve

;   ==- MM_MUESTRA: print("(Qm.n) ") y outval([R0, R1], n) -====================
;   R2[4:0] = n + 1 (0: no muestra nada). Conserva todos los registros.
MM_MUESTRA
        PUSH  R0, R2, R7
        LSHF  R2, R2, #11
        RSHFL R2, R2, #11       ; n + 1
        BRz   MM_MUESTRA_FIN
        SUB   R2, R2, #1        ; n
        LEA   R0, MM_PROMPTS
        LDRX  R0, R0, R2
        PUTSP                   ; print("(Qm.n) ")
        LDR   R0, R6, #0        ; R0 de entrada
        JSR   g27_outval-OUTVAL
MM_MUESTRA_FIN
        POPR  R0, R2, R7

;   ==- MM_PIDE: print(R0 + "(Qm.n) > ") y [R0, R1] = getval(n) -===============
;   R2[4:0] = n + 1 (distinto de 0). Conserva R2-R5.
MM_PIDE
        PUSH  R2, R7
        PUTSP                   ; print("a ") o print("b ")
        LSHF  R2, R2, #11
        RSHFL R2, R2, #11
        SUB   R2, R2, #1        ; n
        LEA   R0, MM_PROMPTS
        LDRX  R0, R0, R2
        PUTSP                   ; print("(Qm.n) ")
        LEA   R0, MM_MAYOR
        PUTSP                   ; print("> ")
        ADD   R0, R2, #0
        JSR   g27_getval-GETVAL
        POPR  R2, R7

;   ==- MM_TEXTO: imprime el texto de un menu -=================================
;   R0 = texto. Copia cada caracter con OUT, salvo tres marcas:
;     #   la proxima opcion: salto de linea, [0], [1], ... y un espacio
;     $X  el titulo de la hoja X hasta antes del parentesis: "==SENO TRIGONOMETRICO"
;     %X  lo que esta entre parentesis en el titulo de la hoja X: "TAYLOR"
;   Usa R0-R3; conserva R4-R7.
MM_TEXTO
        PUSH  R4, R7
        ADD   R1, R0, #0
        MOVI  R2, #48           ; el digito de la proxima opcion
TX_LOOP LDBI  R0, R1
        BRz   TX_FIN
        CMP   R0, #35
        BRz   TX_OPCION         ; #
        BRn   TX_CHAR
        CMP   R0, #37
        BRp   TX_CHAR
        LDBI  R4, R1            ; $ o %: la letra del nodo
        MOVI  R3, #-65
        ADD   R4, R4, R3
        LD    R3, TX_TABLA
        LDRX  R4, R3, R4
        ADD   R4, R4, #4        ; R4 = titulo de la hoja
        CMP   R0, #36
        BRz   TX_NOMBRE
TX_SALTA
        LDBI  R0, R4            ; %: hasta pasar el parentesis
        CMP   R0, #40
        BRnp  TX_SALTA
TX_VARIANTE
        LDBI  R0, R4
        CMP   R0, #41
        BRz   TX_LOOP           ; hasta que se cierra
        OUT
        BR    TX_VARIANTE
TX_NOMBRE
        LDBI  R0, R4            ; $: hasta el espacio antes del parentesis
        LDB   R3, R4, #0
        CMP   R3, #40
        BRz   TX_LOOP
        OUT
        BR    TX_NOMBRE
TX_OPCION
        LEA   R0, MM_OPCION
        STB   R2, R0, #2        ; el numero de la opcion
        ADD   R2, R2, #1
        PUTSP
        BR    TX_LOOP
TX_CHAR OUT
        BR    TX_LOOP
TX_FIN  POPR  R4, R7
TX_TABLA    .FILL MM_TABLA
MM_OPCION   .STRINGP "\n[0] "

;   ==- Prompts, por n -========================================================
;   Las entradas de los n que ningun nodo usa guardan otras cadenas.
MM_PROMPTS  .FILL MM_P0             ; n = 0
MM_P0       .STRINGP "(int) "       ; (n = 1-4)
MM_A        .STRINGP "a "           ; (n = 5-6)
            .FILL MM_P7             ; n = 7
            .FILL MM_P8             ; n = 8
            .FILL MM_P9             ; n = 9
MM_B        .STRINGP "b "           ; (n = 10-11)
            .FILL MM_P12            ; n = 12
            .FILL #0                ; (n = 13)
            .FILL MM_P14            ; n = 14
            .FILL MM_P15            ; n = 15
            .FILL MM_P16            ; n = 16
MM_P7       .STRINGP "(Q8.7) "
MM_P8       .STRINGP "(Q7.8) "
MM_P9       .STRINGP "(Q6.9) "
MM_P12      .STRINGP "(Q3.12) "
MM_P14      .STRINGP "(Q1.14) "
MM_P15      .STRINGP "(Q0.15) "
MM_P16      .STRINGP "(Q15.16) "
MM_MAYOR    .STRINGP "> "

.END
