#include "gui_session.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks, failures;
#define CHECK(c) do { ++checks; if (!(c)) { ++failures; fprintf(stderr, "FALLO linea %d: %s\n", __LINE__, #c); } } while (0)
static GuiSession *s;
static AsmError error;
static const char sum[] = ".ORIG x3000\nLD R1,A\nLD R2,B\nADD R0,R1,R2\nST R0,RESULTADO\nHALT\nA .FILL #15\nB .FILL #27\nRESULTADO .BLKW #1\n.END\n";
static GuiState finish(void) {
    for (unsigned i = 0; i < 1000u && (s->state == GUI_RUNNING || s->state == GUI_WAITING); ++i) {
        if (gui_session_slice(s, 1000u) == GUI_WAITING) break;
    }
    return s->state;
}
static void sum_and_breakpoints(void) {
    uint16_t address = 0; uint64_t reads;
    CHECK(gui_session_assemble(s, sum, "suma.asm", NULL, 0, &error));
    CHECK(s->state == GUI_READY && s->machine.pc == 0x3000u);
    CHECK(gui_session_address(s, " RESULTADO ", &address) && address == 0x300Eu);
    CHECK(!gui_session_address(s, "x10000", &address));
    CHECK(!gui_session_address(s, "x3000 basura", &address));
    CHECK(gui_session_address(s, "xFFFF", &address) && address == 65535u);
    CHECK(!gui_session_breakpoint(s, 0x3001));
    CHECK(gui_session_breakpoint(s, 0x3006));
    CHECK(gui_session_run(s, 1000)); CHECK(finish() == GUI_BREAKPOINT);
    CHECK(s->machine.instructions == 3 && s->machine.r[0] == 42);
    CHECK(lc3_peek(&s->machine, 0x300E) == 0);
    CHECK(gui_session_step(s)); CHECK(lc3_peek(&s->machine, 0x300E) == 42);
    CHECK(gui_session_run(s, 1000)); CHECK(finish() == GUI_HALTED);
    CHECK(s->machine.instructions == 108 && strstr(s->output, "HALT"));
    CHECK(s->program_instructions == 5 && s->system_instructions == 103);
    CHECK(s->program_instructions + s->system_instructions == s->machine.instructions);
    reads = s->machine.memory_read_bytes;
    (void)lc3_peek(&s->machine, 0x300E);
    CHECK(s->machine.memory_read_bytes == reads);
    CHECK(gui_session_reset(s, &error));
    CHECK(s->breakpoints[0x3006] && s->machine.instructions == 0 && !s->output_length);
    CHECK(s->program_instructions == 0 && s->system_instructions == 0);
    CHECK(gui_session_run(s, 1000)); CHECK(finish() == GUI_BREAKPOINT);
    CHECK(gui_session_run(s, 1000)); CHECK(finish() == GUI_HALTED);
    CHECK(lc3_peek(&s->machine, 0x300E) == 42);
    CHECK(!gui_session_run(s, 1000));
    CHECK(!gui_session_assemble(s, ".ORIG x3000\nADD R0,R0,#20\n.END", "error.asm", NULL, 0, &error));
    CHECK(s->loaded && s->image.origin == 0x3000 && error.line == 2);
}
static void waiting_and_limits(void) {
    unsigned char big[LC3_INPUT_SIZE + 1u] = {0};
    const unsigned char letter = 'A'; uint64_t count;
    CHECK(gui_session_assemble(s, ".ORIG x3000\nGETC\nOUT\nHALT\n.END", "teclado.asm", NULL, 0, &error));
    CHECK(!gui_session_input(s, big, sizeof big) && s->machine.input_count == 0);
    CHECK(gui_session_run(s, 1000)); CHECK(finish() == GUI_WAITING);
    count = s->machine.instructions;
    CHECK(gui_session_slice(s, 10000) == GUI_WAITING && s->machine.instructions == count);
    CHECK(gui_session_input(s, &letter, 1)); CHECK(finish() == GUI_HALTED);
    CHECK(s->machine.r[0] == 'A' && strstr(s->output, "A"));
    CHECK(gui_session_assemble(s, ".ORIG x3000\nLAZO BR LAZO\n.END", "bucle.asm", NULL, 0, &error));
    CHECK(gui_session_run(s, 5)); CHECK(finish() == GUI_LIMIT && s->machine.instructions == 5);
    CHECK(gui_session_run(s, 7)); CHECK(finish() == GUI_LIMIT && s->machine.instructions == 12);
    CHECK(gui_session_run(s, 1000)); CHECK(gui_session_slice(s, 10) == GUI_RUNNING);
    gui_session_pause(s); CHECK(s->state == GUI_PAUSED && s->machine.instructions == 22);
    CHECK(gui_session_reset(s, &error) && s->machine.instructions == 0);
}
static void object_and_fault(const char *path) {
    CHECK(gui_session_assemble(s, sum, "suma.asm", NULL, 0, &error));
    CHECK(lc3_object_write(path, &s->image, &error));
    CHECK(gui_session_object(s, path, &error) && s->image.symbol_count == 0);
    CHECK(gui_session_run(s, 1000)); CHECK(finish() == GUI_HALTED && s->machine.r[0] == 42);
    CHECK(gui_session_assemble(s, ".ORIG x3000\nRTI\n.END", "fallo.asm", NULL, 0, &error));
    CHECK(gui_session_run(s, 1000)); CHECK(finish() == GUI_FAULT && s->machine.last_exception == 0x100);
}
static void external_exp(const char *project) {
    char path[2048], dir[2048]; const char *dirs[1] = {dir};
    snprintf(path, sizeof path, "%s/ejemplos/exp_isa3c.asm", project);
    snprintf(dir, sizeof dir, "%s/benchmark/modulos", project);
    FILE *f = fopen(path, "rb"); CHECK(f != NULL); if (!f) return;
    char source[16384]; size_t n = fread(source, 1, sizeof source - 1u, f); fclose(f); source[n] = 0;
    CHECK(gui_session_assemble(s, source, path, dirs, 1, &error));
    CHECK(gui_session_breakpoint(s, 0x3004)); CHECK(gui_session_breakpoint(s, 0x3006));
    CHECK(gui_session_run(s, 100000)); CHECK(finish() == GUI_BREAKPOINT);
    CHECK(s->machine.pc == 0x3004 && s->program_instructions == 2);
    CHECK(gui_session_run(s, 100000)); CHECK(finish() == GUI_BREAKPOINT);
    CHECK(s->machine.pc == 0x3006 && s->program_instructions == 1758 && s->system_instructions == 0);
    CHECK(gui_session_run(s, 100000)); CHECK(finish() == GUI_HALTED);
    CHECK(s->machine.r[0] == 5142 && strstr(s->output, "x1416"));
    CHECK(s->machine.instructions == 2204);
    CHECK(s->program_instructions + s->system_instructions == 2204);
}
static void counter_regions(void) {
    /* Supervisor mode alone does not make a loaded user image a system routine. */
    CHECK(gui_session_assemble(s, ".ORIG x0200\nHALT\n.END", "supervisor.asm", NULL, 0, &error));
    CHECK(gui_session_run(s, 1000)); CHECK(finish() == GUI_HALTED);
    CHECK(s->program_instructions == 1 && s->system_instructions > 0);
    CHECK(s->program_instructions + s->system_instructions == s->machine.instructions);
    /* Dynamically generated code in normal user memory still belongs to the program. */
    CHECK(gui_session_assemble(s, ".ORIG x3000\nLD R1,DEST\nJMP R1\nDEST .FILL x4000\n.END", "dinamico.asm", NULL, 0, &error));
    lc3_poke(&s->machine, 0x4000, (uint16_t)((OP_TRAP << 11u) | 0x25u));
    CHECK(gui_session_run(s, 1000)); CHECK(finish() == GUI_HALTED);
    CHECK(s->program_instructions == 3 && s->system_instructions > 0);
    CHECK(s->program_instructions + s->system_instructions == s->machine.instructions);
    /* Interrupt entry is a CPU event, not a fetched instruction. */
    CHECK(gui_session_assemble(s, sum, "interrupcion.asm", NULL, 0, &error));
    s->machine.kbsr |= 0x4000u;
    CHECK(lc3_key(&s->machine, 'A'));
    CHECK(gui_session_step(s));
    CHECK(s->machine.interrupts == 1 && s->machine.instructions == 0);
    CHECK(s->program_instructions == 0 && s->system_instructions == 0);
    CHECK(gui_session_step(s));
    CHECK(s->machine.instructions == 1 && s->system_instructions == 1);
}
static void consecutive_keyboard_prompts(void) {
    const unsigned char a = 'A', b = 'B'; uint64_t before;
    CHECK(gui_session_assemble(s, ".ORIG x3000\nGETC\nOUT\nGETC\nOUT\nHALT\n.END", "dos_entradas.asm", NULL, 0, &error));
    CHECK(gui_session_run(s, 10000));
    CHECK(gui_session_tick(s, 10000) && s->state == GUI_WAITING);
    before = s->machine.instructions;
    CHECK(!gui_session_tick(s, 10000) && s->machine.instructions == before);
    CHECK(gui_session_input(s, &a, 1));
    CHECK(gui_session_tick(s, 10000));
    CHECK(s->state == GUI_WAITING && !strcmp(s->output, "A"));
    CHECK(s->machine.instructions > before);
    CHECK(!gui_session_tick(s, 10000));
    CHECK(gui_session_input(s, &b, 1));
    CHECK(gui_session_tick(s, 10000) && s->state == GUI_HALTED);
    CHECK(strstr(s->output, "AB") && s->program_instructions + s->system_instructions == s->machine.instructions);
    CHECK(!gui_session_tick(s, 10000));
}
static void calculator_without_pause(const char *project, const char *object_path) {
    char path[2048]; const unsigned char option = '5', exponent[] = {'3', '\n'}, next = ' ', leave = 'd';
    snprintf(path, sizeof path, "%s/build/calculadora.obj", project);
    CHECK(gui_session_object(s, object_path ? object_path : path, &error));
    CHECK(gui_session_run(s, 1000000));
    CHECK(gui_session_tick(s, 20000) && s->state == GUI_WAITING);
    CHECK(strstr(s->output, "CALCULADORA") != NULL);
    CHECK(!gui_session_tick(s, 20000));
    CHECK(gui_session_input(s, &option, 1));
    CHECK(gui_session_tick(s, 20000) && s->state == GUI_WAITING);
    CHECK(strstr(s->output, "EXPONENCIACION") != NULL);
    CHECK(!gui_session_tick(s, 20000));
    CHECK(gui_session_input(s, exponent, sizeof exponent));
    CHECK(gui_session_tick(s, 20000) && s->state == GUI_WAITING);
    CHECK(strstr(s->output, "20.0859375") != NULL);
    CHECK(s->program_instructions + s->system_instructions == s->machine.instructions);
    CHECK(!gui_session_tick(s, 20000));
    size_t previous_length = s->output_length;
    CHECK(gui_session_input(s, &next, 1));
    CHECK(gui_session_tick(s, 20000) && s->state == GUI_WAITING);
    CHECK(s->output_length > previous_length && strstr(s->output + previous_length, "CALCULADORA"));
    CHECK(gui_session_input(s, &leave, 1));
    CHECK(gui_session_tick(s, 20000) && s->state == GUI_HALTED);
    CHECK(s->machine.last_exception == 0);
}
int main(int argc, char **argv) {
    if (argc != 3 && argc != 4) { fprintf(stderr, "Uso: test_gui_session proyecto objeto_temporal [calculadora.obj]\n"); return 2; }
    s = calloc(1, sizeof *s); if (!s) return 2;
    sum_and_breakpoints(); waiting_and_limits(); object_and_fault(argv[2]); external_exp(argv[1]); counter_regions();
    consecutive_keyboard_prompts(); calculator_without_pause(argv[1], argc == 4 ? argv[3] : NULL);
    gui_session_dispose(s); free(s); lc3_os_free();
    printf("Interfaz: %u comprobaciones, %u fallos.\n", checks, failures);
    return failures ? 1 : 0;
}
