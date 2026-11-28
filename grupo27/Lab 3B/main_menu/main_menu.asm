

.EXTERNAL GETCFILTERED-GETCFILTERED
.EXTERNAL FROMHEX-FROMHEX
.EXTERNAL PAUSE-PAUSE

.EXTERNAL FROM_QM_N-FROM_QM_N

.EXTERNAL GETVAL-GETVAL         
.EXTERNAL OUTVAL-OUTVAL


;   Como es un programa muy extenso, las variables estan en un punto medio para aprovechar el PCoffset



;   ============================================================================
;   Subrutina: MAIN_MENU
;       Interfaz que permite seleccionar las funciones de la calculadora asi
;       como sus operandos, y llama a las subrutinas de dichas funciones.
;
;       Implementa una maquina de estados, que recorre NODOS los cuales tienen
;       toda la informacion relevante para ejecutarce (interactuar con un menu,
;       obtener datos y llamar a subrutina, entre otros).
; 
;       La estructura interna de cada NODO es la siguiente:
;       0 - Puntero al controlador (funcion que se encarga de procesar el nodo).
;       1 - Puntero al Texto (Titulo y menu a mostrar).
;       2 - Puntero al Filtro (Teclas validas en las opciones del menu).
;       3 - Puntero al Vector de nodos Siguientes (Corresponde con la opcion del menu).
;       4 - Puntero a Direccion de la Subrutina (Subrutina a llamar).
;
;       (No todos los controladores utilizan todos los datos, por ejemplo el
;       controlador de menus utiliza todos menos la Subrutina, el de obtener un decimal
;       y llamar a subrutina utiliza todos menos el filtro, etc.)
;
;   -> INPUT  [R0] nullptr (x0000) o puntero a vector de operaciones.
;
;       Si la entrada es nullptr, se ejecutara el menu con las entradas por teclado con
;       normalidad.
;       Un vector de operaciones consiste de datos de memoria que se ejecutaran como
;       opearaciones del menu (seleccionar operacion, dato_a, dato_b, etc...).
;       Se espera que el primer dato sea la bandera de verbosidad (0, para modo silencioso
;       y 1 para modo verboso).
;
;   ============================================================================

MAIN_MENU                               ;
    ST R0 main_menu_r0                  ;
    ST R1 main_menu_r1                  ;
    ST R2 main_menu_r2                  ;
    ST R3 main_menu_r3                  ;
    ST R4 main_menu_r4                  ;
    ST R5 main_menu_r5                  ;
    ST R7 main_menu_r7                  ;

    AND R1 R1 #0                        ;
    ADD R1 R1 #1                        ;
    ST R1 main_menu_op_verbose          ;   [verbose_op] = 1
    
    ADD R0 R0 #0                        ;
    BRz main_menu_sk1                   ;   if cursor_de_op:
    LDR R1 R0 #0                        ;       
    ST R1 main_menu_op_verbose          ;       [verbose_op] = cursor_de_op.peek()
    ADD R0 R0 #1                        ;       cursor_de_op.incr()

main_menu_sk1
    ST R0 main_menu_op_cursor           ;   [cursor_de_op] = cursor_de_op

    LD R0 main_menu_state_initial       ;   
    ST R0 main_menu_state               ;   [estado] = init
    LDR R0 R0 #0                        ;
    JMP R0                              ;   goto init.controlador


;   ==- Cambio de estado al siguiente nodo -====================================
;   !! ANTES DE SALTAR AQUI, [R0] next_offset
main_menu_swap_node                     ;  
    LD R5 main_menu_state               ;   [R5] nodo = [estado]
    LDR R1 R5 #3                        ;
    ADD R1 R1 R0                        ;   
    LDR R5 R1 #0                        ;   nodo = (nodo.next).peek(next_offset)
    ST R5 main_menu_state               ;   [estado] = nodo
    LDR R0 R5 #0                        ;
    JMP R0                              ;   goto nodo.controlador


;   ==- Return -================================================================
main_menu_return                        ;
    LD R0 main_menu_r0                  ;
    LD R1 main_menu_r1                  ;
    LD R2 main_menu_r2                  ;
    LD R3 main_menu_r3                  ;
    LD R4 main_menu_r4                  ;
    LD R5 main_menu_r5                  ;
    LD R7 main_menu_r7                  ;
    RET                                 ;


;   ==- Controlador para mostrar menus -========================================
main_menu_show_menu                     ;
    LD R1 main_menu_op_cursor           ;
    BRz main_menu_show_menu_sk1         ;   if [cursor_de_op]:
    LDR R0 R1 #0                        ;       [R0] indice
    ADD R1 R1 #1                        ;
    ST R1 main_menu_op_cursor           ;       [cursor_de_op].incr()
    
    LD R5 main_menu_op_table_ads        ;
    ADD R5 R5 R0                        ;
    LDR R5 R5 #0                        ;
    ST R5 main_menu_state               ;       [estado] = tabla_de_nodos.peek(indice)

    LDR R0 R5 #0                        ;
    JMP R0                              ;       goto nodo.controlador

main_menu_show_menu_sk1
    LD R5 main_menu_state               ;   [R5] nodo = [estado]
    LDR R0 R5 #1                        ;  
    PUTS                                ;   print(nodo.texto)

    LDR R0 R5 #2                        ;
    LD R1 sub_getcfiltered              ;
    JSRR R1                             ;   [R0] char = getcfiltered(nodo.filtro)

    LEA R1 main_menu_aux_0              ;
    STR R0 R1 #0                        ;
    AND R0 R0 #0                        ;
    STR R0 R1 #1                        ;
    ADD R0 R1 #0                        ;   [R0] buffer = char + '\0'
    LD R1 sub_fromhex                   ;
    JSRR R1                             ;   [R0] valor = fromhex(buffer) # (tambien cambia [R5] banderas de error)

    BR main_menu_swap_node              ;   # Cambio de nodo (offset = valor)


;   ==- Controlador subrutinas de un entero (no muestra resultado) -============
main_menu_one_int_noresult
    LD R0 main_menu_0
    LD R1 main_menu_neg_1
    LD R2 main_menu_neg_1
    BR main_menu_call

;   ==- Controlador subrutinas de un entero resultado en Q3.12 -================
main_menu_one_int_result_q12
    LD R0 main_menu_0
    LD R1 main_menu_neg_1
    LD R2 main_menu_12
    BR main_menu_call

;   ==- Controlador subrutinas de dos enteros  -================================
main_menu_two_int
    LD R0 main_menu_0
    LD R1 main_menu_0
    LD R2 main_menu_0
    BR main_menu_call

;   ==- Controlador subrutinas de un Q3.12 -====================================
main_menu_one_q12
    LD R0 main_menu_12
    LD R1 main_menu_neg_1
    LD R2 main_menu_12
    BR main_menu_call

;   ==- Controlador subrutinas de un Q3.12 con resultado en Q7.8 -==============
main_menu_one_q12_result_q8
    LD R0 main_menu_12
    LD R1 main_menu_neg_1
    LD R2 main_menu_8
    BR main_menu_call

;   ==- Controlador subrutinas de un Q3.12 con resultado en Q1.14 -=============
main_menu_one_q12_result_q14
    LD R0 main_menu_12
    LD R1 main_menu_neg_1
    LD R2 main_menu_14
    BR main_menu_call

;   ==- Controlador subrutinas de un Q8.7 -=====================================
main_menu_one_q7
    LD R0 main_menu_7
    LD R1 main_menu_neg_1
    LD R2 main_menu_7
    BR main_menu_call

;   ==- Controlador subrutinas de un Q7.8 -=====================================
main_menu_one_q8
    LD R0 main_menu_8
    LD R1 main_menu_neg_1
    LD R2 main_menu_8
    BR main_menu_call

;   ==- Controlador subrutinas de un Q7.8 un int resultado en Q7.8 -============
main_menu_q8_int_result_q8
    LD R0 main_menu_8
    LD R1 main_menu_0
    LD R2 main_menu_8
    BR main_menu_call

;   ==- Controlador subrutinas de un Q7.8 con resultado en Q6.9 -===============
main_menu_one_q8_result_q9
    LD R0 main_menu_8
    LD R1 main_menu_neg_1
    LD R2 main_menu_9
    BR main_menu_call

;   ==- Controlador subrutinas de dos Q7.8 -====================================
main_menu_two_q8
    LD R0 main_menu_8
    LD R1 main_menu_8
    LD R2 main_menu_8
    BR main_menu_call

;   ==- Controlador subrutinas de dos Q0.15 -===================================
main_menu_two_q15
    LD R0 main_menu_15
    LD R1 main_menu_15
    LD R2 main_menu_15
    BR main_menu_call

;   ==- Controlador subrutinas de un DQ15.16 -==================================
main_menu_one_dq16
    LD R0 main_menu_16
    LD R1 main_menu_neg_1
    LD R2 main_menu_16
    BR main_menu_call

;   ==- Controlador subrutinas de dor Q7.8 con resultado DQ15.16 -==============
main_menu_two_q8_result_dq16
    LD R0 main_menu_8
    LD R1 main_menu_8
    LD R2 main_menu_16
    BR main_menu_call


;   ==- Controlador subrutinas -===============================================
main_menu_call
;   [R0] n entrada1 (o -1 para saltar)
;   [R1] n entrada2 (o -1 para saltar)
;   [R2] n salida   (o -1 para saltar)

    LD R4 main_menu_op_cursor           ;   if [cursor_de_op]:
    BRnp main_menu_call_op              ;       goto main_menu_call_op

    ST R0 main_menu_aux_2               ;   [aux_2] = n_entrada1
    ST R1 main_menu_aux_3               ;   [aux_3] = n_entrada2
    ST R2 main_menu_aux_4               ;   [aux_4] = n_salida

    LD R5 main_menu_state               ;   [R5] nodo = [estado]

    LDR R0 R5 #1                        ;
    PUTS                                ;   print(nodo.texto)

main_menu_call_get1                     ;
    LD R0 main_menu_aux_2               ;
    BRn main_menu_call_get2             ;

    LD R0 main_menu_prompt_qa_vec       ;
    LD R1 main_menu_aux_2               ;
    ADD R0 R0 R1                        ;
    LDR R0 R0 #0                        ;
    PUTS                                ;   print("a (Q3.12) > ")

    LD R0 main_menu_aux_2               ;
    LD R1 sub_getval                    ;   
    JSRR R1                             ;   [R0, R1] getval(aux_2)
    ST R0 main_menu_aux_0               ;
    ST R1 main_menu_aux_1               ;   [aux_0, aux_1] = getval(n)

main_menu_call_get2
    LD R0 main_menu_aux_3               ;
    BRn main_menu_call_exec             ;

    LD R0 main_menu_prompt_qb_vec       ;
    LD R1 main_menu_aux_3               ;
    ADD R0 R0 R1                        ;
    LDR R0 R0 #0                        ;
    PUTS                                ;   print("a (Q3.12) > ")

    LD R0 main_menu_aux_3               ;
    LD R1 sub_getval                    ;
    JSRR R1                             ;   [R0, R1] = getval(aux_3)
    ST R0 main_menu_aux_1               ;

main_menu_call_exec
    LD R0 main_menu_aux_0               ;
    LD R1 main_menu_aux_1               ;
    LDR R2 R5 #4                        ;
    LDR R2 R2 #0                        ;
    JSRR R2                             ;   
    ST R0 main_menu_aux_0               ;
    ST R1 main_menu_aux_1               ;   [aux_0, aux_1] result = node.subrutina(value_a, value_b)

main_menu_call_out                      ;
    LD R0 main_menu_aux_4               ;
    BRn main_menu_call_next             ;

    LD R0 main_menu_prompt_q_vec        ;
    LD R1 main_menu_aux_4               ;
    ADD R0 R0 R1                        ;
    LDR R0 R0 #0                        ;
    PUTS                                ;   print("(Q3.12) ")
    
    LD R0 main_menu_aux_0               ;
    LD R1 main_menu_aux_1               ;   [R0, R1] (entero, fraccion)
    LD R2 main_menu_aux_4               ;   [R2] n_salida
    LD R3 sub_outval                    ;
    JSRR R3                             ;   outval(entero, fraccion, n)

main_menu_call_next
    LD R0 sub_pause                     ;
    JSRR R0                             ;   pause()

    AND R0 R0 #0                        ;
    BR main_menu_swap_node              ;   # Cambio de nodo (offset = 0)


;   ============================================================================
;   ==- Variables -=============================================================

main_menu_r0                .FILL #0
main_menu_r1                .FILL #0
main_menu_r2                .FILL #0
main_menu_r3                .FILL #0
main_menu_r4                .FILL #0
main_menu_r5                .FILL #0
main_menu_r7                .FILL #0
main_menu_op_verbose        .FILL #0
main_menu_op_cursor         .FILL #0
main_menu_state_initial     .FILL main_menu_init
main_menu_state             .FILL #0
main_menu_prompt_qa_vec     .FILL main_menu_prompt_qa_text_vec 
main_menu_prompt_qb_vec     .FILL main_menu_prompt_qb_text_vec 
main_menu_prompt_q_vec      .FILL main_menu_prompt_q_text_vec  
main_menu_neg_1             .FILL #-1
main_menu_0                 .FILL #0
main_menu_7                 .FILL #7
main_menu_8                 .FILL #8
main_menu_9                 .FILL #9
main_menu_12                .FILL #12
main_menu_14                .FILL #14
main_menu_15                .FILL #15
main_menu_16                .FILL #16
main_menu_aux_0             .FILL #0
main_menu_aux_1             .FILL #0
main_menu_aux_2             .FILL #0
main_menu_aux_3             .FILL #0
main_menu_aux_4             .FILL #0

main_menu_swap_node_ads     .FILL main_menu_swap_node
main_menu_op_table_ads      .FILL main_menu_op_table

sub_getcfiltered            .FILL GETCFILTERED-GETCFILTERED
sub_fromhex                 .FILL FROMHEX-FROMHEX
sub_pause                   .FILL PAUSE-PAUSE

sub_from_qm_n               .FILL FROM_QM_N-FROM_QM_N

sub_getval                  .FILL GETVAL-GETVAL
sub_outval                  .FILL OUTVAL-OUTVAL


;   ==- Controlador subrutinas OPERACION -=====================================
main_menu_call_op
;   [R0] n entrada1 (o -1 para saltar)
;   [R1] n entrada2 (o -1 para saltar)
;   [R2] n salida   (o -1 para saltar)

    ST R0 main_menu_aux_2               ;   [aux_2] = n_entrada1
    ST R1 main_menu_aux_3               ;   [aux_3] = n_entrada2
    ST R2 main_menu_aux_4               ;   [aux_4] = n_salida

    LD R5 main_menu_state               ;   [R5] nodo = [estado]

    LD R4 main_menu_op_cursor           ;   [R4] cursor_de_op
    LDR R0 R4 #0                        ;
    ST R0 main_menu_aux_0               ;   [aux_0] = var_a
    LDR R0 R4 #1                        ;
    ST R0 main_menu_aux_1               ;   [aux_1] = var_b     # o basura si es que tomaba solo 1 argumento

    LD R0 main_menu_op_verbose          ;
    BRz main_menu_call_op_exec          ;

main_menu_call_op_show_title            ;
    LDR R0 R5 #1                        ;
    PUTS                                ;   print(nodo.texto)

main_menu_call_op_show1                 ;
    LD R0 main_menu_aux_2               ;
    BRn main_menu_call_op_show2         ;

    LD R0 main_menu_prompt_q_vec        ;
    LD R1 main_menu_aux_2               ;
    ADD R0 R0 R1                        ;
    LDR R0 R0 #0                        ;
    PUTS                                ;   print("(Q3.12) ")
    
    LD R0 main_menu_aux_0               ;
    LD R1 main_menu_aux_1               ;   [R0, R1] (entero, fraccion)
    LD R2 main_menu_aux_2               ;   [R2] n_entrada1
    LD R3 sub_outval                    ;
    JSRR R3                             ;   outval(entero, fraccion, n)

main_menu_call_op_show2                 ;
    LD R0 main_menu_aux_3               ;
    BRn main_menu_call_op_exec          ;

    LD R0 main_menu_prompt_q_vec        ;
    LD R1 main_menu_aux_3               ;
    ADD R0 R0 R1                        ;
    LDR R0 R0 #0                        ;
    PUTS                                ;   print("(Q3.12) ")
    
    LD R0 main_menu_aux_1               ;
    AND R1 R1 #0                        ;   [R0, R1] (entero, 0)    # el value_b nunca puede ser Q15.16
    LD R2 main_menu_aux_3               ;   [R2] n_entrada1
    LD R3 sub_outval                    ;
    JSRR R3                             ;   outval(entero, 0, n)

main_menu_call_op_exec
    LD R0 main_menu_aux_0               ;
    LD R1 main_menu_aux_1               ;
    LDR R2 R5 #4                        ;
    LDR R2 R2 #0                        ;
    JSRR R2                             ;   
    ST R0 main_menu_aux_0               ;
    ST R1 main_menu_aux_1               ;   [aux_0, aux_1] result = node.subrutina(value_a, value_b)

    LD R0 main_menu_op_verbose          ;
    BRz main_menu_call_op_save_result   ;

main_menu_call_op_show_res              ;
    LD R0 main_menu_aux_4               ;
    BRn main_menu_call_op_save_result   ;

    LD R0 main_menu_prompt_q_vec        ;
    LD R1 main_menu_aux_4               ;
    ADD R0 R0 R1                        ;
    LDR R0 R0 #0                        ;
    PUTS                                ;   print("(Q3.12) ")
    
    LD R0 main_menu_aux_0               ;
    LD R1 main_menu_aux_1               ;   [R0, R1] resultado      # R1 puede ser basura
    LD R2 main_menu_aux_4               ;   [R2] n_salida
    LD R3 sub_outval                    ;
    JSRR R3                             ;   outval(resultado, n_salida)

main_menu_call_op_save_result           ;
    LD R0 main_menu_aux_4               ;
    ADD R0 R0 #-16                      ;
    BRz main_menu_call_op_save_sk1     ;
    AND R0 R0 #0                        ;
    ST R0 main_menu_aux_1               ;

main_menu_call_op_save_sk1              ;
    LD R0 main_menu_aux_0               ;
    LD R1 main_menu_aux_1               ;
    STR R0 R4 #2                        ;
    STR R1 R4 #3                        ;

    ADD R4 R4 #4                        ;  
    ST R4 main_menu_op_cursor           ;   cursor_de_op.incr(4)

    AND R0 R0 #0                        ;
    LD R1 main_menu_swap_node_ads       ; 
    JMP R1                              ;   # Cambio de nodo (offset = 0)


;   ============================================================================
;   ==- Prompt texts -==========================================================


main_menu_prompt_qa_text_vec    .FILL main_menu_prompt_q0a_text
                                .FILL main_menu_prompt_q1a_text
                                .FILL main_menu_prompt_q2a_text
                                .FILL main_menu_prompt_q3a_text
                                .FILL main_menu_prompt_q4a_text
                                .FILL main_menu_prompt_q5a_text
                                .FILL main_menu_prompt_q6a_text
                                .FILL main_menu_prompt_q7a_text
                                .FILL main_menu_prompt_q8a_text
                                .FILL main_menu_prompt_q9a_text
                                .FILL main_menu_prompt_q10a_text
                                .FILL main_menu_prompt_q11a_text
                                .FILL main_menu_prompt_q12a_text
                                .FILL main_menu_prompt_q13a_text
                                .FILL main_menu_prompt_q14a_text
                                .FILL main_menu_prompt_q15a_text
                                .FILL main_menu_prompt_q16a_text
main_menu_prompt_qb_text_vec    .FILL main_menu_prompt_q0b_text
                                .FILL main_menu_prompt_q1b_text
                                .FILL main_menu_prompt_q2b_text
                                .FILL main_menu_prompt_q3b_text
                                .FILL main_menu_prompt_q4b_text
                                .FILL main_menu_prompt_q5b_text
                                .FILL main_menu_prompt_q6b_text
                                .FILL main_menu_prompt_q7b_text
                                .FILL main_menu_prompt_q8b_text
                                .FILL main_menu_prompt_q9b_text
                                .FILL main_menu_prompt_q10b_text
                                .FILL main_menu_prompt_q11b_text
                                .FILL main_menu_prompt_q12b_text
                                .FILL main_menu_prompt_q13b_text
                                .FILL main_menu_prompt_q14b_text
                                .FILL main_menu_prompt_q15b_text
                                .FILL main_menu_prompt_q16b_text
main_menu_prompt_q_text_vec     .FILL main_menu_prompt_q0_text
                                .FILL main_menu_prompt_q1_text
                                .FILL main_menu_prompt_q2_text
                                .FILL main_menu_prompt_q3_text
                                .FILL main_menu_prompt_q4_text
                                .FILL main_menu_prompt_q5_text
                                .FILL main_menu_prompt_q6_text
                                .FILL main_menu_prompt_q7_text
                                .FILL main_menu_prompt_q8_text
                                .FILL main_menu_prompt_q9_text
                                .FILL main_menu_prompt_q10_text
                                .FILL main_menu_prompt_q11_text
                                .FILL main_menu_prompt_q12_text
                                .FILL main_menu_prompt_q13_text
                                .FILL main_menu_prompt_q14_text
                                .FILL main_menu_prompt_q15_text
                                .FILL main_menu_prompt_q16_text

main_menu_prompt_q0a_text       .STRINGZ "a (int) > "
main_menu_prompt_q1a_text       .STRINGZ "a (Q14.1) > "
main_menu_prompt_q2a_text       .STRINGZ "a (Q13.2) > "
main_menu_prompt_q3a_text       .STRINGZ "a (Q12.3) > "
main_menu_prompt_q4a_text       .STRINGZ "a (Q11.4) > "
main_menu_prompt_q5a_text       .STRINGZ "a (Q10.5) > "
main_menu_prompt_q6a_text       .STRINGZ "a (Q9.6) > "
main_menu_prompt_q7a_text       .STRINGZ "a (Q8.7) > "
main_menu_prompt_q8a_text       .STRINGZ "a (Q7.8) > "
main_menu_prompt_q9a_text       .STRINGZ "a (Q6.9) > "
main_menu_prompt_q10a_text      .STRINGZ "a (Q5.10) > "
main_menu_prompt_q11a_text      .STRINGZ "a (Q4.11) > "
main_menu_prompt_q12a_text      .STRINGZ "a (Q3.12) > "
main_menu_prompt_q13a_text      .STRINGZ "a (Q2.13) > "
main_menu_prompt_q14a_text      .STRINGZ "a (Q1.14) > "
main_menu_prompt_q15a_text      .STRINGZ "a (Q0.15) > "
main_menu_prompt_q16a_text      .STRINGZ "a (Q15.16) > "
main_menu_prompt_q0b_text       .STRINGZ "b (int) > "   
main_menu_prompt_q1b_text       .STRINGZ "b (Q14.1) > "
main_menu_prompt_q2b_text       .STRINGZ "b (Q13.2) > "
main_menu_prompt_q3b_text       .STRINGZ "b (Q12.3) > "
main_menu_prompt_q4b_text       .STRINGZ "b (Q11.4) > "
main_menu_prompt_q5b_text       .STRINGZ "b (Q10.5) > "
main_menu_prompt_q6b_text       .STRINGZ "b (Q9.6) > "
main_menu_prompt_q7b_text       .STRINGZ "b (Q8.7) > "
main_menu_prompt_q8b_text       .STRINGZ "b (Q7.8) > "
main_menu_prompt_q9b_text       .STRINGZ "b (Q6.9) > "
main_menu_prompt_q10b_text      .STRINGZ "b (Q5.10) > "
main_menu_prompt_q11b_text      .STRINGZ "b (Q4.11) > "
main_menu_prompt_q12b_text      .STRINGZ "b (Q3.12) > "
main_menu_prompt_q13b_text      .STRINGZ "b (Q2.13) > "
main_menu_prompt_q14b_text      .STRINGZ "b (Q1.14) > "
main_menu_prompt_q15b_text      .STRINGZ "b (Q0.15) > "
main_menu_prompt_q16b_text      .STRINGZ "b (Q15.16) > "
main_menu_prompt_q0_text        .STRINGZ "(int) " 
main_menu_prompt_q1_text        .STRINGZ "(Q14.1) "
main_menu_prompt_q2_text        .STRINGZ "(Q13.2) "
main_menu_prompt_q3_text        .STRINGZ "(Q12.3) "
main_menu_prompt_q4_text        .STRINGZ "(Q11.4) "
main_menu_prompt_q5_text        .STRINGZ "(Q10.5) "
main_menu_prompt_q6_text        .STRINGZ "(Q9.6) "
main_menu_prompt_q7_text        .STRINGZ "(Q8.7) "
main_menu_prompt_q8_text        .STRINGZ "(Q7.8) "
main_menu_prompt_q9_text        .STRINGZ "(Q6.9) "
main_menu_prompt_q10_text       .STRINGZ "(Q5.10) "
main_menu_prompt_q11_text       .STRINGZ "(Q4.11) "
main_menu_prompt_q12_text       .STRINGZ "(Q3.12) "
main_menu_prompt_q13_text       .STRINGZ "(Q2.13) "
main_menu_prompt_q14_text       .STRINGZ "(Q1.14) "
main_menu_prompt_q15_text       .STRINGZ "(Q0.15) "
main_menu_prompt_q16_text       .STRINGZ "(Q15.16) "

;   ============================================================================
;   ==- TABLA DEL VECTOR DE OPERACIONES -=======================================
main_menu_op_table          .FILL main_menu_end
                            .FILL main_menu_argrd
                            .FILL main_menu_sin_taylor
                            .FILL main_menu_sin_table
                            .FILL main_menu_sin_cheb
                            .FILL main_menu_cos
                            .FILL main_menu_base_hex
                            .FILL main_menu_base_bin
                            .FILL main_menu_sqrt_nonres
                            .FILL main_menu_sqrt_nr
                            .FILL main_menu_exp
                            .FILL main_menu_pow_mults
                            .FILL main_menu_pow_expbin
                            .FILL main_menu_mult_cordic
                            .FILL main_menu_mult_basic
                            .FILL main_menu_mult_booth
                            .FILL main_menu_div_long
                            .FILL main_menu_div_nr
                            .FILL main_menu_div_cordic
                            .FILL main_menu_log_borch
                            .FILL main_menu_log_cordic
                            .FILL main_menu_mcd
                            .FILL main_menu_mcm
                            .FILL main_menu_qtoq

;   ============================================================================
;   ==- NODOS -=================================================================

main_menu_init              .FILL main_menu_show_menu
                            .FILL main_menu_init_text
                            .FILL main_menu_init_filter
                            .FILL main_menu_init_next
                            .FILL #0
main_menu_init_text         .STRINGZ "\n\n==CALCULADORA ARQUITECTURA 2026==\n[7] x      [8] /      [9] Log    [a] MCD\n[4] sqrt   [5] exp    [6] pow    [b] MCM\n[1] sin    [2] cos    [3] base   [c] Q3.12 -> Q7.8\n[0] Reduccion de argumento       [d] (salir)\n"
main_menu_init_filter       .STRINGZ "09adAD"
main_menu_init_next         .FILL main_menu_argrd
                            .FILL main_menu_sin
                            .FILL main_menu_cos
                            .FILL main_menu_base
                            .FILL main_menu_sqrt
                            .FILL main_menu_exp
                            .FILL main_menu_pow
                            .FILL main_menu_mult
                            .FILL main_menu_div
                            .FILL main_menu_log
                            .FILL main_menu_mcd
                            .FILL main_menu_mcm
                            .FILL main_menu_qtoq
                            .FILL main_menu_end

;   ============================================================================
main_menu_end               .FILL main_menu_return
                            ; #0 #0 #0 #0 (no es necesario en este caso por que
                            ; el controlador simplemente es continuar en return).

;   ============================================================================
main_menu_argrd             .FILL main_menu_one_q12
                            .FILL main_menu_argrd_text
                            .FILL #0
                            .FILL main_menu_argrd_next
                            .FILL main_menu_sub_argrd
main_menu_argrd_text        .STRINGZ "\n\n==REDUCCION DE ARGUMENTO (CORDIC)==\n"
main_menu_argrd_next        .FILL main_menu_init

;   ============================================================================
main_menu_sin               .FILL main_menu_show_menu
                            .FILL main_menu_sin_text
                            .FILL main_menu_sin_filter
                            .FILL main_menu_sin_next
                            .FILL #0
main_menu_sin_text          .STRINGZ "\n\n==SENO TRIGONOMETRICO==\n[0] TAYLOR\n[1] TABLE\n[2] CHEBYSHEV-PADE\n"
main_menu_sin_filter        .STRINGZ "02"
main_menu_sin_next          .FILL main_menu_sin_taylor
                            .FILL main_menu_sin_table
                            .FILL main_menu_sin_cheb
;   ----------------------------------------------------------------------------
main_menu_sin_taylor        .FILL main_menu_one_int_result_q12
                            .FILL main_menu_sin_taylor_text
                            .FILL #0
                            .FILL main_menu_sin_taylor_next
                            .FILL main_menu_sub_sin_taylor
main_menu_sin_taylor_text   .STRINGZ "\n\n==SENO TRIGONOMETRICO (TAYLOR)==\n"
main_menu_sin_taylor_next   .FILL main_menu_init
;   ----------------------------------------------------------------------------
main_menu_sin_table         .FILL main_menu_one_q12_result_q14
                            .FILL main_menu_sin_table_text
                            .FILL #0
                            .FILL main_menu_sin_table_next
                            .FILL main_menu_sub_sin_table
main_menu_sin_table_text    .STRINGZ "\n\n==SENO TRIGONOMETRICO (TABLE)==\n"
main_menu_sin_table_next    .FILL main_menu_init
;   ----------------------------------------------------------------------------
main_menu_sin_cheb          .FILL main_menu_one_q12_result_q14
                            .FILL main_menu_sin_cheb_text
                            .FILL #0
                            .FILL main_menu_sin_cheb_next
                            .FILL main_menu_sub_sin_cheb
main_menu_sin_cheb_text     .STRINGZ "\n\n==SENO TRIGONOMETRICO (CHEVYSHEV-PADE)==\n"
main_menu_sin_cheb_next     .FILL main_menu_init

;   ============================================================================
main_menu_cos               .FILL main_menu_one_q12_result_q14
                            .FILL main_menu_cos_text
                            .FILL #0
                            .FILL main_menu_cos_next
                            .FILL main_menu_sub_cos
main_menu_cos_text          .STRINGZ "\n\n==COSENO TRIGONOMETRICO (TABLE)==\n"
main_menu_cos_next          .FILL main_menu_init

;   ============================================================================
main_menu_base              .FILL main_menu_show_menu
                            .FILL main_menu_base_text
                            .FILL main_menu_base_filter
                            .FILL main_menu_base_next
                            .FILL #0
main_menu_base_text         .STRINGZ "\n\n==EXPRESION CON BASE==\n[0] HEX\n[1] BIN\n"
main_menu_base_filter       .STRINGZ "01"
main_menu_base_next         .FILL main_menu_base_hex
                            .FILL main_menu_base_bin
;   ----------------------------------------------------------------------------
main_menu_base_hex          .FILL main_menu_one_int_noresult
                            .FILL main_menu_base_hex_text
                            .FILL #0
                            .FILL main_menu_base_hex_next
                            .FILL main_menu_sub_base_hex
main_menu_base_hex_text     .STRINGZ "\n\n==EXPRESION CON BASE (HEX)==\n"
main_menu_base_hex_next     .FILL main_menu_init
;   ----------------------------------------------------------------------------
main_menu_base_bin          .FILL main_menu_one_int_noresult
                            .FILL main_menu_base_bin_text
                            .FILL #0
                            .FILL main_menu_base_bin_next
                            .FILL main_menu_sub_base_bin
main_menu_base_bin_text     .STRINGZ "\n\n==EXPRESION CON BASE (BIN)==\n"
main_menu_base_bin_next     .FILL main_menu_init

;   ============================================================================
main_menu_sqrt              .FILL main_menu_show_menu
                            .FILL main_menu_sqrt_text
                            .FILL main_menu_sqrt_filter
                            .FILL main_menu_sqrt_next
                            .FILL #0
main_menu_sqrt_text         .STRINGZ "\n\n==RAIZ CUADRADA==\n[0] NON RESTORING\n[1] NEWTON-RAPHSON\n"
main_menu_sqrt_filter       .STRINGZ "01"
main_menu_sqrt_next         .FILL main_menu_sqrt_nonres
                            .FILL main_menu_sqrt_nr
;   ----------------------------------------------------------------------------
main_menu_sqrt_nonres       .FILL main_menu_one_q8_result_q9
                            .FILL main_menu_sqrt_nonres_text
                            .FILL #0
                            .FILL main_menu_sqrt_nonres_next
                            .FILL main_menu_sub_sqrt_nonres
main_menu_sqrt_nonres_text  .STRINGZ "\n\n==RAIZ CUADRADA (NON RESTORING)==\n"
main_menu_sqrt_nonres_next  .FILL main_menu_init
;   ----------------------------------------------------------------------------
main_menu_sqrt_nr           .FILL main_menu_one_dq16
                            .FILL main_menu_sqrt_nr_text
                            .FILL #0
                            .FILL main_menu_sqrt_nr_next
                            .FILL main_menu_sub_sqrt_nr
main_menu_sqrt_nr_text      .STRINGZ "\n\n==RAIZ CUADRADA (NEWTON-RAPHSON)==\n"
main_menu_sqrt_nr_next      .FILL main_menu_init

;   ============================================================================
main_menu_exp               .FILL main_menu_one_q12_result_q8
                            .FILL main_menu_exp_text
                            .FILL #0
                            .FILL main_menu_exp_next
                            .FILL main_menu_sub_exp
main_menu_exp_text          .STRINGZ "\n\n==EXPONENCIACION==\n"
main_menu_exp_next          .FILL main_menu_init

;   ============================================================================
main_menu_pow               .FILL main_menu_show_menu
                            .FILL main_menu_pow_text
                            .FILL main_menu_pow_filter
                            .FILL main_menu_pow_next
                            .FILL #0
main_menu_pow_text          .STRINGZ "\n\n==POTENCIACION==\n[0] MULTIPLICACIONES SUCESIVAS\n[1] EXP BINARIA\n"
main_menu_pow_filter        .STRINGZ "01"
main_menu_pow_next          .FILL main_menu_pow_mults
                            .FILL main_menu_pow_expbin
;   ----------------------------------------------------------------------------
main_menu_pow_mults         .FILL main_menu_q8_int_result_q8
                            .FILL main_menu_pow_mults_text
                            .FILL #0
                            .FILL main_menu_pow_mults_next
                            .FILL main_menu_sub_pow_mults
main_menu_pow_mults_text    .STRINGZ "\n\n==POTENCIACION (MULTIPLICACIONES SUCESIVAS)==\n"
main_menu_pow_mults_next    .FILL main_menu_init
;   ----------------------------------------------------------------------------
main_menu_pow_expbin        .FILL main_menu_two_int
                            .FILL main_menu_pow_expbin_text
                            .FILL #0
                            .FILL main_menu_pow_expbin_next
                            .FILL main_menu_sub_pow_expbin
main_menu_pow_expbin_text   .STRINGZ "\n\n==POTENCIACION (EXPONENCIACION BINARIA)==\n"
main_menu_pow_expbin_next   .FILL main_menu_init

;   ============================================================================
main_menu_mult              .FILL main_menu_show_menu
                            .FILL main_menu_mult_text
                            .FILL main_menu_mult_filter
                            .FILL main_menu_mult_next
                            .FILL #0
main_menu_mult_text         .STRINGZ "\n\n==MULTIPLICACION==\n[0] CORDIC\n[1] BASIC\n[2] BOOTH\n"
main_menu_mult_filter       .STRINGZ "02"
main_menu_mult_next         .FILL main_menu_mult_cordic
                            .FILL main_menu_mult_basic
                            .FILL main_menu_mult_booth
;   ----------------------------------------------------------------------------
main_menu_mult_cordic       .FILL main_menu_two_q8
                            .FILL main_menu_mult_cordic_text
                            .FILL #0
                            .FILL main_menu_mult_cordic_next
                            .FILL main_menu_sub_mult_cordic
main_menu_mult_cordic_text  .STRINGZ "\n\n==MULTIPLICACION (CORDIC)==\n"
main_menu_mult_cordic_next  .FILL main_menu_init
;   ----------------------------------------------------------------------------
main_menu_mult_basic        .FILL main_menu_two_q8_result_dq16
                            .FILL main_menu_mult_basic_text
                            .FILL #0
                            .FILL main_menu_mult_basic_next
                            .FILL main_menu_sub_mult_basic
main_menu_mult_basic_text   .STRINGZ "\n\n==MULTIPLICACION (BASIC)==\n"
main_menu_mult_basic_next   .FILL main_menu_init
;   ----------------------------------------------------------------------------
main_menu_mult_booth        .FILL main_menu_two_q8
                            .FILL main_menu_mult_booth_text
                            .FILL #0
                            .FILL main_menu_mult_booth_next
                            .FILL main_menu_sub_mult_booth
main_menu_mult_booth_text   .STRINGZ "\n\n==MULTIPLICACION (BOOTH)==\n"
main_menu_mult_booth_next   .FILL main_menu_init

;   ============================================================================
main_menu_div               .FILL main_menu_show_menu
                            .FILL main_menu_div_text
                            .FILL main_menu_div_filter
                            .FILL main_menu_div_next
                            .FILL #0
main_menu_div_text          .STRINGZ "\n\n==DIVISION==\n[0] LONG DIVISION\n[1] NEWTON-RAPHSON\n[2] CORDIC\n"
main_menu_div_filter        .STRINGZ "02"
main_menu_div_next          .FILL main_menu_div_long
                            .FILL main_menu_div_nr
                            .FILL main_menu_div_cordic
;   ----------------------------------------------------------------------------
main_menu_div_long          .FILL main_menu_two_q8
                            .FILL main_menu_div_long_text
                            .FILL #0
                            .FILL main_menu_div_long_next
                            .FILL main_menu_sub_div_long
main_menu_div_long_text     .STRINGZ "\n\n==DIVISION (LONG DIVISION)==\n"
main_menu_div_long_next     .FILL main_menu_init
;   ----------------------------------------------------------------------------
main_menu_div_nr            .FILL main_menu_two_q8
                            .FILL main_menu_div_nr_text
                            .FILL #0
                            .FILL main_menu_div_nr_next
                            .FILL main_menu_sub_div_nr
main_menu_div_nr_text       .STRINGZ "\n\n==DIVISION (NEWTON-RAPHSON)==\n"
main_menu_div_nr_next       .FILL main_menu_init
;   ----------------------------------------------------------------------------
main_menu_div_cordic        .FILL main_menu_two_q15
                            .FILL main_menu_div_cordic_text
                            .FILL #0
                            .FILL main_menu_div_cordic_next
                            .FILL main_menu_sub_div_cordic
main_menu_div_cordic_text   .STRINGZ "\n\n==DIVISION (CORDIC)==\n"
main_menu_div_cordic_next   .FILL main_menu_init

;   ============================================================================
main_menu_log               .FILL main_menu_show_menu
                            .FILL main_menu_log_text
                            .FILL main_menu_log_filter
                            .FILL main_menu_log_next
                            .FILL #0
main_menu_log_text          .STRINGZ "\n\n==LOGARITMO==\n[0] BORCHARDT\n[1] CORDIC\n"
main_menu_log_filter        .STRINGZ "01"
main_menu_log_next          .FILL main_menu_log_borch
                            .FILL main_menu_log_cordic
;   ----------------------------------------------------------------------------
main_menu_log_borch         .FILL main_menu_one_q7
                            .FILL main_menu_log_borch_text
                            .FILL #0
                            .FILL main_menu_log_borch_next
                            .FILL main_menu_sub_log_borch
main_menu_log_borch_text    .STRINGZ "\n\n==LOGARITMO== (BORCHARDT)\n"
main_menu_log_borch_next    .FILL main_menu_init
;   ----------------------------------------------------------------------------
main_menu_log_cordic        .FILL main_menu_one_q12
                            .FILL main_menu_log_cordic_text
                            .FILL #0
                            .FILL main_menu_log_cordic_next
                            .FILL main_menu_sub_log_cordic
main_menu_log_cordic_text   .STRINGZ "\n\n==LOGARITMO== (CORDIC)\n"
main_menu_log_cordic_next   .FILL main_menu_init

;   ============================================================================
main_menu_mcd               .FILL main_menu_two_int
                            .FILL main_menu_mcd_text
                            .FILL #0
                            .FILL main_menu_mcd_next
                            .FILL main_menu_sub_mcd
main_menu_mcd_text          .STRINGZ "\n\n==MAXIMO COMUN DIVISOR==\n"
main_menu_mcd_next          .FILL main_menu_init

;   ============================================================================
main_menu_mcm               .FILL main_menu_two_int
                            .FILL main_menu_mcm_text
                            .FILL #0
                            .FILL main_menu_mcm_next
                            .FILL main_menu_sub_mcm
main_menu_mcm_text          .STRINGZ "\n\n==MINIMO COMUN MULTIPLO==\n"
main_menu_mcm_next          .FILL main_menu_init

;   ============================================================================
main_menu_qtoq              .FILL main_menu_one_q12_result_q8
                            .FILL main_menu_qtoq_text
                            .FILL #0
                            .FILL main_menu_qtoq_next
                            .FILL main_menu_sub_qtoq
main_menu_qtoq_text         .STRINGZ "\n\n==Q3.12 -> Q7.8==\n"
main_menu_qtoq_next         .FILL main_menu_init



;   ============================================================================
;   ==- SUBRUTINAS de las Funciones de la calculadora -=========================

main_menu_sub_mult_cordic   .FILL NULL_SUBRUTINE
main_menu_sub_mult_basic    .FILL NULL_SUBRUTINE
main_menu_sub_mult_booth    .FILL NULL_SUBRUTINE
main_menu_sub_div_long      .FILL NULL_SUBRUTINE
main_menu_sub_div_nr        .FILL NULL_SUBRUTINE
main_menu_sub_div_cordic    .FILL NULL_SUBRUTINE
main_menu_sub_log_borch     .FILL NULL_SUBRUTINE
main_menu_sub_log_cordic    .FILL NULL_SUBRUTINE
main_menu_sub_sqrt_nonres   .FILL NULL_SUBRUTINE
main_menu_sub_sqrt_nr       .FILL NULL_SUBRUTINE
main_menu_sub_exp           .FILL NULL_SUBRUTINE
main_menu_sub_pow_mults     .FILL NULL_SUBRUTINE
main_menu_sub_pow_expbin    .FILL NULL_SUBRUTINE
main_menu_sub_sin_taylor    .FILL NULL_SUBRUTINE
main_menu_sub_sin_table     .FILL NULL_SUBRUTINE
main_menu_sub_sin_cheb      .FILL NULL_SUBRUTINE
main_menu_sub_cos           .FILL NULL_SUBRUTINE
main_menu_sub_base_hex      .FILL NULL_SUBRUTINE
main_menu_sub_base_bin      .FILL NULL_SUBRUTINE
main_menu_sub_mcd           .FILL NULL_SUBRUTINE
main_menu_sub_mcm           .FILL NULL_SUBRUTINE
main_menu_sub_argrd         .FILL NULL_SUBRUTINE
main_menu_sub_qtoq          .FILL NULL_SUBRUTINE


; (subrutina valida, pero que no hace nada...)
NULL_SUBRUTINE
    ST R0 null_subrutine_r0
    ST R7 null_subrutine_r7
    LEA R0 null_subrutine_text
    PUTS
    LD R0 null_subrutine_r0
    LD R7 null_subrutine_r7
    RET
null_subrutine_r0   .FILL #0
null_subrutine_r7   .FILL #0
null_subrutine_text .STRINGZ "(se ejecutaria una subrutina...)\n"

.END
