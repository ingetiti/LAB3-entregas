#ifndef ISA_GUI_SESSION_H
#define ISA_GUI_SESSION_H
#include "lc3.h"

#define GUI_OUTPUT_CAPACITY (1024u * 1024u)
typedef enum {
    GUI_EMPTY, GUI_READY, GUI_PAUSED, GUI_RUNNING, GUI_WAITING,
    GUI_BREAKPOINT, GUI_LIMIT, GUI_HALTED, GUI_FAULT
} GuiState;

/* A frontend session owns an image, a CPU and debugger state; the ISA stays in lc3.c. */
typedef struct {
    Lc3 machine;
    Lc3Image image;
    unsigned char breakpoints[ISA_MEMORY_BYTES];
    char output[GUI_OUTPUT_CAPACITY + 1u];
    size_t output_length;
    uint64_t run_start, run_limit;
    uint64_t program_instructions, system_instructions;
    uint16_t breakpoint_pc;
    int loaded, skip_breakpoint_once, output_trimmed;
    GuiState state;
} GuiSession;

void gui_session_dispose(GuiSession *session);
int gui_session_assemble(GuiSession *session, const char *source, const char *path,
                         const char *const *dirs, size_t count, AsmError *error);
int gui_session_object(GuiSession *session, const char *path, AsmError *error);
int gui_session_reset(GuiSession *session, AsmError *error);
int gui_session_step(GuiSession *session);
int gui_session_run(GuiSession *session, uint64_t limit);
GuiState gui_session_slice(GuiSession *session, unsigned maximum_steps);
/* Advance a slice; true also when keyboard processing returns to WAITING. */
int gui_session_tick(GuiSession *session, unsigned maximum_steps);
void gui_session_pause(GuiSession *session);
int gui_session_input(GuiSession *session, const unsigned char *bytes, size_t count);
int gui_session_address(const GuiSession *session, const char *text, uint16_t *address);
int gui_session_breakpoint(GuiSession *session, uint16_t address);
void gui_session_clear_output(GuiSession *session);
#endif
