;=====================================================================
; SUBRUTINA: MAIN_MENU (ISA-G27)
;
;   -> INPUT  [R0] x0000 (modo interactivo por teclado) o
;                  puntero (dirección de palabra) a bloque de operaciones:
;                  [0] modalidad (0 = silencioso, 1 = verboso)
;                  [1..] bloques de 5 words (10 bytes):
;                        [op_idx, arg_a, arg_b, res_0, res_1]
;                        (termina con op_idx = 0 -> SALIR)
;   Conserva: R0-R7 (todos intactos, incluyendo R6).
;=====================================================================
.EXTERNAL g27_getcfiltered-GETCFILTERED
.EXTERNAL g27_fromhex-FROMHEX
.EXTERNAL g27_pause-PAUSE
.EXTERNAL g27_getval-GETVAL
.EXTERNAL g27_outval-OUTVAL

.EXTERNAL g1_cordic_division-CORDIC_DIV_Q15
.EXTERNAL g3_MultiplicacionSHIFTandADD-MUL_Q7_8_SHIFT_ADD
.EXTERNAL g4_potencia-EXP_RAPIDA
.EXTERNAL g5_Mul_Sucesiva_POW-Mul_Sucesiva_POW
.EXTERNAL g6_EXP-EXP_Q3_12
.EXTERNAL g7_mcm-MCM
.EXTERNAL g7_mcd-MCD
.EXTERNAL g9_sqrt_nr_dq16-SQRT_NR_DQ16
.EXTERNAL g10_division_larga-DIV_LONG
.EXTERNAL g11_CORDICLog-CORDIC_LOG_BASE
.EXTERNAL g12_subrutina_grupo_12-DIV_NEWTON
.EXTERNAL g14_log_borchardt_q8_7-LN_Q8_7
.EXTERNAL g15_G15_Q312_Q78-G15_Q312_Q78
.EXTERNAL g18_booth-MULT_BOOTH
.EXTERNAL g19_cordic_multiplicacion-CORDIC_MUL
.EXTERNAL g20_Cordic_reduccion_de_argumento-Reduccion_Argumento
.EXTERNAL g21_senotaylor_subrutina-CALCULAR_SENO
.EXTERNAL g22_Tabla_SIN_y_COS-SENO_TABLA
.EXTERNAL g22_Tabla_SIN_y_COS-COSENO_TABLA
.EXTERNAL g23_modulo_sqrt_nr-SQRT_NR
.EXTERNAL g24_conversor_lc3_max-SUB_BASE_HEX
.EXTERNAL g24_conversor_lc3_max-SUB_BASE_BIN
.EXTERNAL g30_seno_cheb_pade-SEN_CHEB_PADE

MAIN_MENU:
        ST      R0, mm_r0
        ST      R1, mm_r1
        ST      R2, mm_r2
        ST      R3, mm_r3
        ST      R4, mm_r4
        ST      R5, mm_r5
        ST      R7, mm_r7

        AND     R1, R1, #0
        ADD     R1, R1, #1
        ST      R1, mm_verbose

        ADD     R0, R0, #0
        BRz     main_menu_sk1

        LDR     R1, R0, #0
        ST      R1, mm_verbose
        ADD     R0, R0, #2

main_menu_sk1:
        ST      R0, mm_cursor

        LD      R0, mm_state_init_ptr
        ST      R0, mm_state
        LDR     R0, R0, #0
        JMP     R0

main_menu_swap_node:
        LSH     R0, R0, #1
        LD      R5, mm_state
        LDR     R1, R5, #3
        ADD     R1, R1, R0
        LDR     R5, R1, #0
        ST      R5, mm_state
        LDR     R0, R5, #0
        JMP     R0

main_menu_return:
        LD      R0, mm_r0
        LD      R1, mm_r1
        LD      R2, mm_r2
        LD      R3, mm_r3
        LD      R4, mm_r4
        LD      R5, mm_r5
        LD      R7, mm_r7
        RET

; --- Datos locales de MAIN_MENU / swap_node / return ---
mm_r0:                  .FILL #0
mm_r1:                  .FILL #0
mm_r2:                  .FILL #0
mm_r3:                  .FILL #0
mm_r4:                  .FILL #0
mm_r5:                  .FILL #0
mm_r7:                  .FILL #0
mm_verbose:             .FILL #0
mm_cursor:              .FILL #0
mm_state:               .FILL #0
mm_state_init_ptr:      .FILL main_menu_init

; --- Controlador: mostrar menú o despachar operación del bloque ---
main_menu_show_menu:
        LD      R1, mm_sm_cursor
        LDR     R2, R1, #0
        ADD     R2, R2, #0
        BRz     main_menu_show_menu_sk1

        LDR     R0, R2, #0
        ADD     R2, R2, #2
        STR     R2, R1, #0

        LSH     R0, R0, #1
        LD      R5, mm_sm_op_table
        ADD     R5, R5, R0
        LDR     R5, R5, #0
        LD      R1, mm_sm_state
        STR     R5, R1, #0

        LDR     R0, R5, #0
        JMP     R0

main_menu_show_menu_sk1:
        LD      R5, mm_sm_state
        LDR     R5, R5, #0
        LDR     R0, R5, #1
        PUTS

        LDR     R0, R5, #2
        LD      R1, mm_sm_getcfiltered
        JSRR    R1

        LEA     R1, mm_sm_aux0
        STRB    R0, R1, #0
        AND     R2, R2, #0
        STRB    R2, R1, #1

        ADD     R0, R1, #0
        LD      R1, mm_sm_fromhex
        JSRR    R1
        LD      R1, mm_sm_swap_node
        JMP     R1

; --- Datos locales de show_menu ---
mm_sm_cursor:           .FILL mm_cursor
mm_sm_op_table:         .FILL main_menu_op_table
mm_sm_state:            .FILL mm_state
mm_sm_aux0:             .FILL #0
mm_sm_getcfiltered:     .FILL g27_getcfiltered-GETCFILTERED
mm_sm_fromhex:          .FILL g27_fromhex-FROMHEX
mm_sm_swap_node:        .FILL main_menu_swap_node

; --- Constantes de formatos Q ---
mm_k7:                  .FILL #7
mm_k8:                  .FILL #8
mm_k9:                  .FILL #9
mm_k12:                 .FILL #12
mm_k14:                 .FILL #14
mm_k15:                 .FILL #15
mm_k16:                 .FILL #16
mm_call_ptr:            .FILL main_menu_call

; --- Controladores de aridad y formatos Q ---
main_menu_one_int_noresult:
        AND     R0, R0, #0
        AND     R1, R1, #0
        ADD     R1, R1, #-1
        ADD     R2, R1, #0
        LD      R3, mm_call_ptr
        JMP     R3

main_menu_one_int_result_q12:
        AND     R0, R0, #0
        AND     R1, R1, #0
        ADD     R1, R1, #-1
        LD      R2, mm_k12
        LD      R3, mm_call_ptr
        JMP     R3

main_menu_two_int:
        AND     R0, R0, #0
        AND     R1, R1, #0
        AND     R2, R2, #0
        LD      R3, mm_call_ptr
        JMP     R3

main_menu_one_q12:
        LD      R0, mm_k12
        AND     R1, R1, #0
        ADD     R1, R1, #-1
        ADD     R2, R0, #0
        LD      R3, mm_call_ptr
        JMP     R3

main_menu_one_q12_result_q8:
        LD      R0, mm_k12
        AND     R1, R1, #0
        ADD     R1, R1, #-1
        LD      R2, mm_k8
        LD      R3, mm_call_ptr
        JMP     R3

main_menu_one_q12_result_q14:
        LD      R0, mm_k12
        AND     R1, R1, #0
        ADD     R1, R1, #-1
        LD      R2, mm_k14
        LD      R3, mm_call_ptr
        JMP     R3

main_menu_one_q7:
        LD      R0, mm_k7
        AND     R1, R1, #0
        ADD     R1, R1, #-1
        ADD     R2, R0, #0
        LD      R3, mm_call_ptr
        JMP     R3

main_menu_one_q8:
        LD      R0, mm_k8
        AND     R1, R1, #0
        ADD     R1, R1, #-1
        ADD     R2, R0, #0
        LD      R3, mm_call_ptr
        JMP     R3

main_menu_q8_int_result_q8:
        LD      R0, mm_k8
        AND     R1, R1, #0
        ADD     R2, R0, #0
        LD      R3, mm_call_ptr
        JMP     R3

main_menu_one_q8_result_q9:
        LD      R0, mm_k8
        AND     R1, R1, #0
        ADD     R1, R1, #-1
        LD      R2, mm_k9
        LD      R3, mm_call_ptr
        JMP     R3

main_menu_two_q8:
        LD      R0, mm_k8
        ADD     R1, R0, #0
        ADD     R2, R0, #0
        LD      R3, mm_call_ptr
        JMP     R3

main_menu_two_q15:
        LD      R0, mm_k15
        ADD     R1, R0, #0
        ADD     R2, R0, #0
        LD      R3, mm_call_ptr
        JMP     R3

main_menu_one_dq16:
        LD      R0, mm_k16
        AND     R1, R1, #0
        ADD     R1, R1, #-1
        ADD     R2, R0, #0
        LD      R3, mm_call_ptr
        JMP     R3

main_menu_two_q8_result_dq16:
        LD      R0, mm_k8
        ADD     R1, R0, #0
        LD      R2, mm_k16
        LD      R3, mm_call_ptr
        JMP     R3

; --- Controlador de ejecución en modo interactivo ---
main_menu_call:
        LD      R4, mm_ic_cursor
        LDR     R4, R4, #0
        BRz     main_menu_call_inter
        LD      R3, mm_ic_call_op
        JMP     R3

main_menu_call_inter:
        ST      R0, mm_ic_aux2
        ST      R1, mm_ic_aux3
        ST      R2, mm_ic_aux4

        LD      R5, mm_ic_state
        LDR     R5, R5, #0
        LDR     R0, R5, #1
        PUTS

main_menu_call_get1:
        LD      R1, mm_ic_aux2
        BRn     main_menu_call_get2

        LSH     R1, R1, #1
        LD      R0, mm_ic_qa_vec
        ADD     R0, R0, R1
        LDR     R0, R0, #0
        PUTS

        LD      R0, mm_ic_aux2
        LD      R1, mm_ic_getval
        JSRR    R1
        ST      R0, mm_ic_aux0
        ST      R1, mm_ic_aux1

main_menu_call_get2:
        LD      R1, mm_ic_aux3
        BRn     main_menu_call_exec

        LSH     R1, R1, #1
        LD      R0, mm_ic_qb_vec
        ADD     R0, R0, R1
        LDR     R0, R0, #0
        PUTS

        LD      R0, mm_ic_aux3
        LD      R1, mm_ic_getval
        JSRR    R1
        ST      R0, mm_ic_aux1

main_menu_call_exec:
        LD      R0, mm_ic_aux0
        LD      R1, mm_ic_aux1
        LDR     R2, R5, #4
        LDR     R2, R2, #0
        JSRR    R2
        ST      R0, mm_ic_aux0
        ST      R1, mm_ic_aux1

main_menu_call_out:
        LD      R1, mm_ic_aux4
        BRn     main_menu_call_next

        LSH     R1, R1, #1
        LD      R0, mm_ic_q_vec
        ADD     R0, R0, R1
        LDR     R0, R0, #0
        PUTS

        LD      R0, mm_ic_aux0
        LD      R1, mm_ic_aux1
        LD      R2, mm_ic_aux4
        LD      R3, mm_ic_outval
        JSRR    R3

main_menu_call_next:
        LD      R0, mm_ic_pause
        JSRR    R0

        AND     R0, R0, #0
        LD      R1, mm_ic_swap_node
        JMP     R1

; --- Datos locales de call (modo interactivo) ---
mm_ic_cursor:           .FILL mm_cursor
mm_ic_state:            .FILL mm_state
mm_ic_call_op:          .FILL main_menu_call_op
mm_ic_swap_node:        .FILL main_menu_swap_node
mm_ic_qa_vec:           .FILL main_menu_prompt_qa_text_vec
mm_ic_qb_vec:           .FILL main_menu_prompt_qb_text_vec
mm_ic_q_vec:            .FILL main_menu_prompt_q_text_vec
mm_ic_getval:           .FILL g27_getval-GETVAL
mm_ic_outval:           .FILL g27_outval-OUTVAL
mm_ic_pause:            .FILL g27_pause-PAUSE
mm_ic_aux0:             .FILL #0
mm_ic_aux1:             .FILL #0
mm_ic_aux2:             .FILL #0
mm_ic_aux3:             .FILL #0
mm_ic_aux4:             .FILL #0

; --- Controlador de ejecución en modo bloque de operaciones ---
main_menu_call_op:
        ST      R0, mm_op_aux2
        ST      R1, mm_op_aux3
        ST      R2, mm_op_aux4

        LD      R1, mm_op_state
        LDR     R5, R1, #0
        LD      R1, mm_op_cursor
        LDR     R4, R1, #0

        LDR     R0, R4, #0
        ST      R0, mm_op_aux0
        LDR     R0, R4, #1
        ST      R0, mm_op_aux1

        LD      R1, mm_op_verbose
        LDR     R0, R1, #0
        BRz     main_menu_call_op_exec

        LDR     R0, R5, #1
        PUTS

main_menu_call_op_show1:
        LD      R1, mm_op_aux2
        BRn     main_menu_call_op_show2

        LSH     R1, R1, #1
        LD      R0, mm_op_q_vec
        ADD     R0, R0, R1
        LDR     R0, R0, #0
        PUTS

        LD      R0, mm_op_aux0
        LD      R1, mm_op_aux1
        LD      R2, mm_op_aux2
        LD      R3, mm_op_outval
        JSRR    R3

main_menu_call_op_show2:
        LD      R1, mm_op_aux3
        BRn     main_menu_call_op_exec

        LSH     R1, R1, #1
        LD      R0, mm_op_q_vec
        ADD     R0, R0, R1
        LDR     R0, R0, #0
        PUTS

        LD      R0, mm_op_aux1
        AND     R1, R1, #0
        LD      R2, mm_op_aux3
        LD      R3, mm_op_outval
        JSRR    R3

main_menu_call_op_exec:
        LD      R0, mm_op_aux0
        LD      R1, mm_op_aux1
        LDR     R2, R5, #4
        LDR     R2, R2, #0
        JSRR    R2
        ST      R0, mm_op_aux0
        ST      R1, mm_op_aux1

        LD      R1, mm_op_verbose
        LDR     R0, R1, #0
        BRz     main_menu_call_op_save_result

        LD      R1, mm_op_aux4
        BRn     main_menu_call_op_save_result

        LSH     R1, R1, #1
        LD      R0, mm_op_q_vec
        ADD     R0, R0, R1
        LDR     R0, R0, #0
        PUTS

        LD      R0, mm_op_aux0
        LD      R1, mm_op_aux1
        LD      R2, mm_op_aux4
        LD      R3, mm_op_outval
        JSRR    R3

main_menu_call_op_save_result:
        LD      R0, mm_op_aux4
        LD      R1, mm_op_neg16
        ADD     R0, R0, R1
        BRz     main_menu_call_op_save_sk1
        AND     R0, R0, #0
        ST      R0, mm_op_aux1

main_menu_call_op_save_sk1:
        LD      R0, mm_op_aux0
        LD      R1, mm_op_aux1
        STR     R0, R4, #2
        STR     R1, R4, #3

        LD      R1, mm_op_k8
        ADD     R4, R4, R1
        LD      R1, mm_op_cursor
        STR     R4, R1, #0

        AND     R0, R0, #0
        LD      R1, mm_op_swap_node
        JMP     R1

; --- Datos locales de call_op (modo bloque) ---
mm_op_verbose:          .FILL mm_verbose
mm_op_cursor:           .FILL mm_cursor
mm_op_state:            .FILL mm_state
mm_op_swap_node:        .FILL main_menu_swap_node
mm_op_q_vec:            .FILL main_menu_prompt_q_text_vec
mm_op_outval:           .FILL g27_outval-OUTVAL
mm_op_neg16:            .FILL #-16
mm_op_k8:               .FILL #8
mm_op_aux0:             .FILL #0
mm_op_aux1:             .FILL #0
mm_op_aux2:             .FILL #0
mm_op_aux3:             .FILL #0
mm_op_aux4:             .FILL #0

;=====================================================================
; VECTORES DE PROMPTS Y CADENAS DE 8 BITS (.STRINGZ)
;=====================================================================
main_menu_prompt_qa_text_vec:
        .FILL main_menu_prompt_q0a_text
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

main_menu_prompt_qb_text_vec:
        .FILL main_menu_prompt_q0b_text
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

main_menu_prompt_q_text_vec:
        .FILL main_menu_prompt_q0_text
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

main_menu_prompt_q0a_text:  .STRINGZ "a (int) > "
main_menu_prompt_q1a_text:  .STRINGZ "a (Q14.1) > "
main_menu_prompt_q2a_text:  .STRINGZ "a (Q13.2) > "
main_menu_prompt_q3a_text:  .STRINGZ "a (Q12.3) > "
main_menu_prompt_q4a_text:  .STRINGZ "a (Q11.4) > "
main_menu_prompt_q5a_text:  .STRINGZ "a (Q10.5) > "
main_menu_prompt_q6a_text:  .STRINGZ "a (Q9.6) > "
main_menu_prompt_q7a_text:  .STRINGZ "a (Q8.7) > "
main_menu_prompt_q8a_text:  .STRINGZ "a (Q7.8) > "
main_menu_prompt_q9a_text:  .STRINGZ "a (Q6.9) > "
main_menu_prompt_q10a_text: .STRINGZ "a (Q5.10) > "
main_menu_prompt_q11a_text: .STRINGZ "a (Q4.11) > "
main_menu_prompt_q12a_text: .STRINGZ "a (Q3.12) > "
main_menu_prompt_q13a_text: .STRINGZ "a (Q2.13) > "
main_menu_prompt_q14a_text: .STRINGZ "a (Q1.14) > "
main_menu_prompt_q15a_text: .STRINGZ "a (Q0.15) > "
main_menu_prompt_q16a_text: .STRINGZ "a (Q15.16) > "

main_menu_prompt_q0b_text:  .STRINGZ "b (int) > "
main_menu_prompt_q1b_text:  .STRINGZ "b (Q14.1) > "
main_menu_prompt_q2b_text:  .STRINGZ "b (Q13.2) > "
main_menu_prompt_q3b_text:  .STRINGZ "b (Q12.3) > "
main_menu_prompt_q4b_text:  .STRINGZ "b (Q11.4) > "
main_menu_prompt_q5b_text:  .STRINGZ "b (Q10.5) > "
main_menu_prompt_q6b_text:  .STRINGZ "b (Q9.6) > "
main_menu_prompt_q7b_text:  .STRINGZ "b (Q8.7) > "
main_menu_prompt_q8b_text:  .STRINGZ "b (Q7.8) > "
main_menu_prompt_q9b_text:  .STRINGZ "b (Q6.9) > "
main_menu_prompt_q10b_text: .STRINGZ "b (Q5.10) > "
main_menu_prompt_q11b_text: .STRINGZ "b (Q4.11) > "
main_menu_prompt_q12b_text: .STRINGZ "b (Q3.12) > "
main_menu_prompt_q13b_text: .STRINGZ "b (Q2.13) > "
main_menu_prompt_q14b_text: .STRINGZ "b (Q1.14) > "
main_menu_prompt_q15b_text: .STRINGZ "b (Q0.15) > "
main_menu_prompt_q16b_text: .STRINGZ "b (Q15.16) > "

main_menu_prompt_q0_text:   .STRINGZ "(int) "
main_menu_prompt_q1_text:   .STRINGZ "(Q14.1) "
main_menu_prompt_q2_text:   .STRINGZ "(Q13.2) "
main_menu_prompt_q3_text:   .STRINGZ "(Q12.3) "
main_menu_prompt_q4_text:   .STRINGZ "(Q11.4) "
main_menu_prompt_q5_text:   .STRINGZ "(Q10.5) "
main_menu_prompt_q6_text:   .STRINGZ "(Q9.6) "
main_menu_prompt_q7_text:   .STRINGZ "(Q8.7) "
main_menu_prompt_q8_text:   .STRINGZ "(Q7.8) "
main_menu_prompt_q9_text:   .STRINGZ "(Q6.9) "
main_menu_prompt_q10_text:  .STRINGZ "(Q5.10) "
main_menu_prompt_q11_text:  .STRINGZ "(Q4.11) "
main_menu_prompt_q12_text:  .STRINGZ "(Q3.12) "
main_menu_prompt_q13_text:  .STRINGZ "(Q2.13) "
main_menu_prompt_q14_text:  .STRINGZ "(Q1.14) "
main_menu_prompt_q15_text:  .STRINGZ "(Q0.15) "
main_menu_prompt_q16_text:  .STRINGZ "(Q15.16) "

;=====================================================================
; PUNTEROS A SUBRUTINAS EXTERNAS
;=====================================================================
sub_mult_cordic:        .FILL g19_cordic_multiplicacion-CORDIC_MUL
sub_mult_basic:         .FILL g3_MultiplicacionSHIFTandADD-MUL_Q7_8_SHIFT_ADD
sub_mult_booth:         .FILL g18_booth-MULT_BOOTH
sub_div_long:           .FILL g10_division_larga-DIV_LONG
sub_div_nr:             .FILL g12_subrutina_grupo_12-DIV_NEWTON
sub_div_cordic:         .FILL g1_cordic_division-CORDIC_DIV_Q15
sub_log_borch:          .FILL g14_log_borchardt_q8_7-LN_Q8_7
sub_log_cordic:         .FILL g11_CORDICLog-CORDIC_LOG_BASE
sub_sqrt_nonres:        .FILL g23_modulo_sqrt_nr-SQRT_NR
sub_sqrt_nr:            .FILL g9_sqrt_nr_dq16-SQRT_NR_DQ16
sub_exp:                .FILL g6_EXP-EXP_Q3_12
sub_pow_mults:          .FILL g5_Mul_Sucesiva_POW-Mul_Sucesiva_POW
sub_pow_expbin:         .FILL g4_potencia-EXP_RAPIDA
sub_sin_taylor:         .FILL g21_senotaylor_subrutina-CALCULAR_SENO
sub_sin_table:          .FILL g22_Tabla_SIN_y_COS-SENO_TABLA
sub_sin_cheb:           .FILL g30_seno_cheb_pade-SEN_CHEB_PADE
sub_cos:                .FILL g22_Tabla_SIN_y_COS-COSENO_TABLA
sub_base_hex:           .FILL g24_conversor_lc3_max-SUB_BASE_HEX
sub_base_bin:           .FILL g24_conversor_lc3_max-SUB_BASE_BIN
sub_mcd:                .FILL g7_mcd-MCD
sub_mcm:                .FILL g7_mcm-MCM
sub_argrd:              .FILL g20_Cordic_reduccion_de_argumento-Reduccion_Argumento
sub_qtoq:               .FILL g15_G15_Q312_Q78-G15_Q312_Q78

;=====================================================================
; TABLA DEL VECTOR DE OPERACIONES (0..23)
;=====================================================================
main_menu_op_table:
        .FILL main_menu_end
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

;=====================================================================
; DEFINICIÓN DE NODOS DE LA MÁQUINA DE ESTADOS
;=====================================================================
main_menu_init:
        .FILL main_menu_show_menu
        .FILL main_menu_init_text
        .FILL main_menu_init_filter
        .FILL main_menu_init_next
        .FILL #0
main_menu_init_text:    .STRINGZ "\n\n==CALCULADORA ARQUITECTURA 2026==\n[7] x      [8] /      [9] Log    [a] MCD\n[4] sqrt   [5] exp    [6] pow    [b] MCM\n[1] sin    [2] cos    [3] base   [c] Q3.12 -> Q7.8\n[0] Reduccion de argumento       [d] (salir)\n"
main_menu_init_filter:  .STRINGZ "09adAD"
main_menu_init_next:
        .FILL main_menu_argrd
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

main_menu_end:
        .FILL main_menu_return

main_menu_argrd:
        .FILL main_menu_one_q12
        .FILL main_menu_argrd_text
        .FILL #0
        .FILL main_menu_argrd_next
        .FILL sub_argrd
main_menu_argrd_text:   .STRINGZ "\n\n==REDUCCION DE ARGUMENTO (CORDIC)==\n"
main_menu_argrd_next:   .FILL main_menu_init

main_menu_sin:
        .FILL main_menu_show_menu
        .FILL main_menu_sin_text
        .FILL main_menu_sin_filter
        .FILL main_menu_sin_next
        .FILL #0
main_menu_sin_text:     .STRINGZ "\n\n==SENO TRIGONOMETRICO==\n[0] TAYLOR\n[1] TABLE\n[2] CHEBYSHEV-PADE\n"
main_menu_sin_filter:   .STRINGZ "02"
main_menu_sin_next:
        .FILL main_menu_sin_taylor
        .FILL main_menu_sin_table
        .FILL main_menu_sin_cheb

main_menu_sin_taylor:
        .FILL main_menu_one_int_result_q12
        .FILL main_menu_sin_taylor_text
        .FILL #0
        .FILL main_menu_sin_taylor_next
        .FILL sub_sin_taylor
main_menu_sin_taylor_text:  .STRINGZ "\n\n==SENO TRIGONOMETRICO (TAYLOR)==\n"
main_menu_sin_taylor_next:  .FILL main_menu_init

main_menu_sin_table:
        .FILL main_menu_one_q12_result_q14
        .FILL main_menu_sin_table_text
        .FILL #0
        .FILL main_menu_sin_table_next
        .FILL sub_sin_table
main_menu_sin_table_text:   .STRINGZ "\n\n==SENO TRIGONOMETRICO (TABLE)==\n"
main_menu_sin_table_next:   .FILL main_menu_init

main_menu_sin_cheb:
        .FILL main_menu_one_q12_result_q14
        .FILL main_menu_sin_cheb_text
        .FILL #0
        .FILL main_menu_sin_cheb_next
        .FILL sub_sin_cheb
main_menu_sin_cheb_text:    .STRINGZ "\n\n==SENO TRIGONOMETRICO (CHEVYSHEV-PADE)==\n"
main_menu_sin_cheb_next:    .FILL main_menu_init

main_menu_cos:
        .FILL main_menu_one_q12_result_q14
        .FILL main_menu_cos_text
        .FILL #0
        .FILL main_menu_cos_next
        .FILL sub_cos
main_menu_cos_text:     .STRINGZ "\n\n==COSENO TRIGONOMETRICO (TABLE)==\n"
main_menu_cos_next:     .FILL main_menu_init

main_menu_base:
        .FILL main_menu_show_menu
        .FILL main_menu_base_text
        .FILL main_menu_base_filter
        .FILL main_menu_base_next
        .FILL #0
main_menu_base_text:    .STRINGZ "\n\n==EXPRESION CON BASE==\n[0] HEX\n[1] BIN\n"
main_menu_base_filter:  .STRINGZ "01"
main_menu_base_next:
        .FILL main_menu_base_hex
        .FILL main_menu_base_bin

main_menu_base_hex:
        .FILL main_menu_one_int_noresult
        .FILL main_menu_base_hex_text
        .FILL #0
        .FILL main_menu_base_hex_next
        .FILL sub_base_hex
main_menu_base_hex_text:    .STRINGZ "\n\n==EXPRESION CON BASE (HEX)==\n"
main_menu_base_hex_next:    .FILL main_menu_init

main_menu_base_bin:
        .FILL main_menu_one_int_noresult
        .FILL main_menu_base_bin_text
        .FILL #0
        .FILL main_menu_base_bin_next
        .FILL sub_base_bin
main_menu_base_bin_text:    .STRINGZ "\n\n==EXPRESION CON BASE (BIN)==\n"
main_menu_base_bin_next:    .FILL main_menu_init

main_menu_sqrt:
        .FILL main_menu_show_menu
        .FILL main_menu_sqrt_text
        .FILL main_menu_sqrt_filter
        .FILL main_menu_sqrt_next
        .FILL #0
main_menu_sqrt_text:    .STRINGZ "\n\n==RAIZ CUADRADA==\n[0] NON RESTORING\n[1] NEWTON-RAPHSON\n"
main_menu_sqrt_filter:  .STRINGZ "01"
main_menu_sqrt_next:
        .FILL main_menu_sqrt_nonres
        .FILL main_menu_sqrt_nr

main_menu_sqrt_nonres:
        .FILL main_menu_one_q8_result_q9
        .FILL main_menu_sqrt_nonres_text
        .FILL #0
        .FILL main_menu_sqrt_nonres_next
        .FILL sub_sqrt_nonres
main_menu_sqrt_nonres_text: .STRINGZ "\n\n==RAIZ CUADRADA (NON RESTORING)==\n"
main_menu_sqrt_nonres_next: .FILL main_menu_init

main_menu_sqrt_nr:
        .FILL main_menu_one_dq16
        .FILL main_menu_sqrt_nr_text
        .FILL #0
        .FILL main_menu_sqrt_nr_next
        .FILL sub_sqrt_nr
main_menu_sqrt_nr_text:     .STRINGZ "\n\n==RAIZ CUADRADA (NEWTON-RAPHSON)==\n"
main_menu_sqrt_nr_next:     .FILL main_menu_init

main_menu_exp:
        .FILL main_menu_one_q12_result_q8
        .FILL main_menu_exp_text
        .FILL #0
        .FILL main_menu_exp_next
        .FILL sub_exp
main_menu_exp_text:     .STRINGZ "\n\n==EXPONENCIACION==\n"
main_menu_exp_next:     .FILL main_menu_init

main_menu_pow:
        .FILL main_menu_show_menu
        .FILL main_menu_pow_text
        .FILL main_menu_pow_filter
        .FILL main_menu_pow_next
        .FILL #0
main_menu_pow_text:     .STRINGZ "\n\n==POTENCIACION==\n[0] MULTIPLICACIONES SUCESIVAS\n[1] EXP BINARIA\n"
main_menu_pow_filter:   .STRINGZ "01"
main_menu_pow_next:
        .FILL main_menu_pow_mults
        .FILL main_menu_pow_expbin

main_menu_pow_mults:
        .FILL main_menu_q8_int_result_q8
        .FILL main_menu_pow_mults_text
        .FILL #0
        .FILL main_menu_pow_mults_next
        .FILL sub_pow_mults
main_menu_pow_mults_text:   .STRINGZ "\n\n==POTENCIACION (MULTIPLICACIONES SUCESIVAS)==\n"
main_menu_pow_mults_next:   .FILL main_menu_init

main_menu_pow_expbin:
        .FILL main_menu_two_int
        .FILL main_menu_pow_expbin_text
        .FILL #0
        .FILL main_menu_pow_expbin_next
        .FILL sub_pow_expbin
main_menu_pow_expbin_text:  .STRINGZ "\n\n==POTENCIACION (EXPONENCIACION BINARIA)==\n"
main_menu_pow_expbin_next:  .FILL main_menu_init

main_menu_mult:
        .FILL main_menu_show_menu
        .FILL main_menu_mult_text
        .FILL main_menu_mult_filter
        .FILL main_menu_mult_next
        .FILL #0
main_menu_mult_text:    .STRINGZ "\n\n==MULTIPLICACION==\n[0] CORDIC\n[1] BASIC\n[2] BOOTH\n"
main_menu_mult_filter:  .STRINGZ "02"
main_menu_mult_next:
        .FILL main_menu_mult_cordic
        .FILL main_menu_mult_basic
        .FILL main_menu_mult_booth

main_menu_mult_cordic:
        .FILL main_menu_two_q8
        .FILL main_menu_mult_cordic_text
        .FILL #0
        .FILL main_menu_mult_cordic_next
        .FILL sub_mult_cordic
main_menu_mult_cordic_text: .STRINGZ "\n\n==MULTIPLICACION (CORDIC)==\n"
main_menu_mult_cordic_next: .FILL main_menu_init

main_menu_mult_basic:
        .FILL main_menu_two_q8_result_dq16
        .FILL main_menu_mult_basic_text
        .FILL #0
        .FILL main_menu_mult_basic_next
        .FILL sub_mult_basic
main_menu_mult_basic_text:  .STRINGZ "\n\n==MULTIPLICACION (BASIC)==\n"
main_menu_mult_basic_next:  .FILL main_menu_init

main_menu_mult_booth:
        .FILL main_menu_two_q8
        .FILL main_menu_mult_booth_text
        .FILL #0
        .FILL main_menu_mult_booth_next
        .FILL sub_mult_booth
main_menu_mult_booth_text:  .STRINGZ "\n\n==MULTIPLICACION (BOOTH)==\n"
main_menu_mult_booth_next:  .FILL main_menu_init

main_menu_div:
        .FILL main_menu_show_menu
        .FILL main_menu_div_text
        .FILL main_menu_div_filter
        .FILL main_menu_div_next
        .FILL #0
main_menu_div_text:     .STRINGZ "\n\n==DIVISION==\n[0] LONG DIVISION\n[1] NEWTON-RAPHSON\n[2] CORDIC\n"
main_menu_div_filter:   .STRINGZ "02"
main_menu_div_next:
        .FILL main_menu_div_long
        .FILL main_menu_div_nr
        .FILL main_menu_div_cordic

main_menu_div_long:
        .FILL main_menu_two_q8
        .FILL main_menu_div_long_text
        .FILL #0
        .FILL main_menu_div_long_next
        .FILL sub_div_long
main_menu_div_long_text:    .STRINGZ "\n\n==DIVISION (LONG DIVISION)==\n"
main_menu_div_long_next:    .FILL main_menu_init

main_menu_div_nr:
        .FILL main_menu_two_q8
        .FILL main_menu_div_nr_text
        .FILL #0
        .FILL main_menu_div_nr_next
        .FILL sub_div_nr
main_menu_div_nr_text:      .STRINGZ "\n\n==DIVISION (NEWTON-RAPHSON)==\n"
main_menu_div_nr_next:      .FILL main_menu_init

main_menu_div_cordic:
        .FILL main_menu_two_q15
        .FILL main_menu_div_cordic_text
        .FILL #0
        .FILL main_menu_div_cordic_next
        .FILL sub_div_cordic
main_menu_div_cordic_text:  .STRINGZ "\n\n==DIVISION (CORDIC)==\n"
main_menu_div_cordic_next:  .FILL main_menu_init

main_menu_log:
        .FILL main_menu_show_menu
        .FILL main_menu_log_text
        .FILL main_menu_log_filter
        .FILL main_menu_log_next
        .FILL #0
main_menu_log_text:     .STRINGZ "\n\n==LOGARITMO==\n[0] BORCHARDT\n[1] CORDIC\n"
main_menu_log_filter:   .STRINGZ "01"
main_menu_log_next:
        .FILL main_menu_log_borch
        .FILL main_menu_log_cordic

main_menu_log_borch:
        .FILL main_menu_one_q7
        .FILL main_menu_log_borch_text
        .FILL #0
        .FILL main_menu_log_borch_next
        .FILL sub_log_borch
main_menu_log_borch_text:   .STRINGZ "\n\n==LOGARITMO== (BORCHARDT)\n"
main_menu_log_borch_next:   .FILL main_menu_init

main_menu_log_cordic:
        .FILL main_menu_one_q12
        .FILL main_menu_log_cordic_text
        .FILL #0
        .FILL main_menu_log_cordic_next
        .FILL sub_log_cordic
main_menu_log_cordic_text:  .STRINGZ "\n\n==LOGARITMO== (CORDIC)\n"
main_menu_log_cordic_next:  .FILL main_menu_init

main_menu_mcd:
        .FILL main_menu_two_int
        .FILL main_menu_mcd_text
        .FILL #0
        .FILL main_menu_mcd_next
        .FILL sub_mcd
main_menu_mcd_text:     .STRINGZ "\n\n==MAXIMO COMUN DIVISOR==\n"
main_menu_mcd_next:     .FILL main_menu_init

main_menu_mcm:
        .FILL main_menu_two_int
        .FILL main_menu_mcm_text
        .FILL #0
        .FILL main_menu_mcm_next
        .FILL sub_mcm
main_menu_mcm_text:     .STRINGZ "\n\n==MINIMO COMUN MULTIPLO==\n"
main_menu_mcm_next:     .FILL main_menu_init

main_menu_qtoq:
        .FILL main_menu_one_q12_result_q8
        .FILL main_menu_qtoq_text
        .FILL #0
        .FILL main_menu_qtoq_next
        .FILL sub_qtoq
main_menu_qtoq_text:    .STRINGZ "\n\n==Q3.12 -> Q7.8==\n"
main_menu_qtoq_next:    .FILL main_menu_init

.END