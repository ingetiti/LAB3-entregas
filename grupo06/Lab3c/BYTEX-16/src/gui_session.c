#include "gui_session.h"
#include <ctype.h>
#include <stdio.h>
#include <string.h>

static int fail(AsmError *error, const char *text) {
    if (error) { memset(error, 0, sizeof *error); snprintf(error->text, sizeof error->text, "%s", text); }
    return 0;
}
static void output(void *context, unsigned char ch) {
    GuiSession *s = context;
    if (s->output_length == GUI_OUTPUT_CAPACITY) {
        size_t keep = GUI_OUTPUT_CAPACITY / 2u;
        memmove(s->output, s->output + s->output_length - keep, keep);
        s->output_length = keep; s->output_trimmed = 1;
    }
    s->output[s->output_length++] = ch ? (char)ch : ' ';
    s->output[s->output_length] = 0;
}
void gui_session_clear_output(GuiSession *s) {
    s->output_length = 0; s->output[0] = 0; s->output_trimmed = 0;
}
void gui_session_dispose(GuiSession *s) {
    lc3_image_free(&s->image); memset(s, 0, sizeof *s);
}
int gui_session_reset(GuiSession *s, AsmError *error) {
    if (!s->loaded) return fail(error, "Primero ensamble o abra un objeto.");
    if (!lc3_init(&s->machine, &s->image, error)) return 0;
    s->machine.output = output; s->machine.output_context = s;
    gui_session_clear_output(s);
    s->run_start = 0; s->run_limit = 0; s->skip_breakpoint_once = 0;
    s->program_instructions = 0; s->system_instructions = 0;
    s->state = GUI_READY; return 1;
}
static int commit(GuiSession *s, Lc3Image *image, AsmError *error) {
    /* Validate before replacing the previous, possibly still useful, program. */
    if (!lc3_init(&s->machine, image, error)) { lc3_image_free(image); return 0; }
    lc3_image_free(&s->image); s->image = *image; memset(image, 0, sizeof *image);
    memset(s->breakpoints, 0, sizeof s->breakpoints); s->loaded = 1;
    return gui_session_reset(s, error);
}
int gui_session_assemble(GuiSession *s, const char *source, const char *path,
                         const char *const *dirs, size_t count, AsmError *error) {
    Lc3Image image = {0};
    if (!lc3_assemble_project(source, path, dirs, count, &image, error)) return 0;
    return commit(s, &image, error);
}
int gui_session_object(GuiSession *s, const char *path, AsmError *error) {
    Lc3Image image = {0};
    if (!lc3_object_read(path, &image, error)) return 0;
    return commit(s, &image, error);
}
static GuiState stopped_state(const GuiSession *s) {
    return s->machine.last_exception ? GUI_FAULT : GUI_HALTED;
}
static int tracked_step(GuiSession *s) {
    uint16_t pc = s->machine.pc;
    uint64_t before = s->machine.instructions;
    int result = lc3_step(&s->machine);
    uint64_t fetched = s->machine.instructions - before;
    /* Loaded image takes precedence, including a deliberately supervisor program.
       Otherwise x3000..xFDFF is user/dynamically generated code; the remainder
       is the reserved system region. Interrupt entry alone fetches no opcode. */
    if (((size_t)pc >= s->image.origin && (size_t)pc < (size_t)s->image.origin + s->image.count) ||
        (pc >= 0x3000u && pc < 0xFE00u)) s->program_instructions += fetched;
    else s->system_instructions += fetched;
    return result;
}
int gui_session_step(GuiSession *s) {
    if (!s->loaded) return 0;
    if (!(s->machine.mcr & 0x8000u)) { s->state = stopped_state(s); return 0; }
    int done = tracked_step(s);
    s->state = !(s->machine.mcr & 0x8000u) ? stopped_state(s) : GUI_PAUSED;
    s->skip_breakpoint_once = 0; return done;
}
int gui_session_run(GuiSession *s, uint64_t limit) {
    if (!s->loaded || !limit || !(s->machine.mcr & 0x8000u)) return 0;
    s->skip_breakpoint_once = s->state == GUI_BREAKPOINT && s->machine.pc == s->breakpoint_pc;
    s->run_start = s->machine.instructions; s->run_limit = limit;
    s->state = GUI_RUNNING; return 1;
}
GuiState gui_session_slice(GuiSession *s, unsigned maximum_steps) {
    if (s->state != GUI_RUNNING && s->state != GUI_WAITING) return s->state;
    if (s->machine.waiting_for_input && !s->machine.input_count && !(s->machine.kbsr & 0x8000u)) {
        s->state = GUI_WAITING; return s->state;
    }
    s->state = GUI_RUNNING;
    for (unsigned i = 0; i < maximum_steps; ++i) {
        if (!(s->machine.mcr & 0x8000u)) { s->state = stopped_state(s); break; }
        if (s->machine.instructions - s->run_start >= s->run_limit) { s->state = GUI_LIMIT; break; }
        if (s->breakpoints[s->machine.pc] && !s->skip_breakpoint_once) {
            s->breakpoint_pc = s->machine.pc; s->state = GUI_BREAKPOINT; break;
        }
        s->skip_breakpoint_once = 0;
        tracked_step(s);
        if (s->machine.waiting_for_input && !s->machine.input_count && !(s->machine.kbsr & 0x8000u)) {
            s->state = GUI_WAITING; break;
        }
    }
    if (!(s->machine.mcr & 0x8000u)) s->state = stopped_state(s);
    else if (s->state == GUI_RUNNING && s->machine.instructions - s->run_start >= s->run_limit) s->state = GUI_LIMIT;
    return s->state;
}
int gui_session_tick(GuiSession *s, unsigned maximum_steps) {
    GuiState state = s->state;
    uint64_t instructions = s->machine.instructions, interrupts = s->machine.interrupts;
    size_t length = s->output_length;
    uint16_t pc = s->machine.pc, psr = s->machine.psr, mcr = s->machine.mcr;
    unsigned exception = s->machine.last_exception;
    gui_session_slice(s, maximum_steps);
    /* WAITING -> execute keyboard-dependent code -> WAITING is still progress.
       Testing just the state hides the new prompt/result until a manual pause. */
    return state != s->state || instructions != s->machine.instructions ||
           interrupts != s->machine.interrupts || length != s->output_length ||
           pc != s->machine.pc || psr != s->machine.psr || mcr != s->machine.mcr ||
           exception != s->machine.last_exception;
}
void gui_session_pause(GuiSession *s) {
    if (s->state == GUI_RUNNING || s->state == GUI_WAITING) s->state = GUI_PAUSED;
}
int gui_session_input(GuiSession *s, const unsigned char *bytes, size_t count) {
    if (!s->loaded || count > LC3_INPUT_SIZE - s->machine.input_count) return 0;
    for (size_t i = 0; i < count; ++i) if (!lc3_key(&s->machine, bytes[i])) return 0;
    return 1;
}
int gui_session_address(const GuiSession *s, const char *text, uint16_t *address) {
    char token[LC3_LABEL_SIZE + 1u]; size_t len = 0; long number;
    while (isspace((unsigned char)*text)) ++text;
    while (*text && !isspace((unsigned char)*text) && len < sizeof token - 1u) token[len++] = *text++;
    token[len] = 0;
    while (isspace((unsigned char)*text)) ++text;
    if (*text || !len) return 0;
    if (s->loaded && lc3_symbol(&s->image, token, address)) return 1;
    if (!lc3_number(token, &number) || number < 0 || number > 65535) return 0;
    *address = (uint16_t)number; return 1;
}
int gui_session_breakpoint(GuiSession *s, uint16_t address) {
    if (!s->loaded || address & 1u) return 0;
    s->breakpoints[address] ^= 1u; return 1;
}
