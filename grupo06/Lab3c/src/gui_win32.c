/* Native Windows frontend. All execution/assembly is delegated to the existing C core. */
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0601
#endif
#include <windows.h>
#include <windowsx.h>
#include <commctrl.h>
#include <commdlg.h>
#include <shellapi.h>
#include <shlobj.h>
#include <dwmapi.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#include <errno.h>
#include "gui_session.h"
#include "gui_editor.h"

enum {
    ID_NEW = 101, ID_OPEN, ID_SAVE, ID_BUILD, ID_RUN, ID_PAUSE, ID_STEP, ID_RESET,
    ID_SAVE_AS, ID_EXPORT, ID_EXIT, ID_LIBRARY, ID_HELP, ID_CLEAR, ID_THEME,
    ID_EX_SUM = 140, ID_EX_HELLO, ID_EX_EXP, ID_EX_ALU, ID_EX_KEY, ID_EX_CALC,
    ID_CODE = 201, ID_GUTTER, ID_CONSOLE, ID_INPUT, ID_SEND, ID_SEND_RAW,
    ID_ADDRESS, ID_GO, ID_PC, ID_BP, ID_MEMORY, ID_INCLUDE_SYSTEM, ID_LIMIT,
    ID_REG0 = 300
};
#define PATH_CAP 32768u
typedef struct {
    COLORREF background, surface, ink, muted, accent, border, registers, alternate, current_pc;
    COLORREF button, primary, run, disabled, disabled_text, pause, pause_text, pause_border, breakpoint;
} Palette;
static Palette palette;
#define BG (palette.background)
#define INK (palette.ink)
#define MUTED (palette.muted)
#define BLUE (palette.accent)
#define LINE (palette.border)
#define GREEN (palette.run)

typedef struct {
    HINSTANCE instance; HWND window, code, gutter, console, input, memory, address, limit, include_system;
    HWND title, subtitle, theme, file_title, file_path, cpu_title, cpu_meta, counter, breakdown, memory_title, memory_hint;
    HWND console_title, input_hint, status, selection, limit_title, registers[8], buttons[8], send, raw, go, pc, bp;
    HFONT ui_font, small_font, heading_font, mono_font, register_font, count_font;
    HBRUSH background, white, console_brush;
    GuiSession *session;
    wchar_t project[PATH_CAP], path[PATH_CAP], library[PATH_CAP];
    wchar_t status_text[1024];
    uint16_t memory_base;
    size_t shown_output;
    int disk_dirty, build_dirty, object_mode, suppress_change, dpi, timer_active, dark_mode;
    ULONGLONG last_refresh;
    RECT left_card, right_card;
} Gui;
static Gui app;
static const char initial_source[] =
    ".ORIG x3000\n    LD R1,NUMERO_A\n    LD R2,NUMERO_B\n    ADD R0,R1,R2\n"
    "    ST R0,RESULTADO\n    HALT\nNUMERO_A .FILL #15\nNUMERO_B .FILL #27\nRESULTADO .BLKW #1\n.END\n";

static int px(int value) { return MulDiv(value, app.dpi, 96); }
static int active(void) { return app.session->state == GUI_RUNNING || app.session->state == GUI_WAITING; }
static void refresh(void);
static void layout(void);
static int assemble(void);
static int load_file(const wchar_t *path);
static void command(unsigned id);
static void rounded(HDC dc, RECT rect, COLORREF fill, COLORREF border);
static void set_palette(int dark) {
    if (dark) palette = (Palette){
        RGB(15,23,34), RGB(24,35,49), RGB(231,239,249), RGB(165,183,205), RGB(126,185,255), RGB(54,74,97),
        RGB(31,46,63), RGB(29,43,59), RGB(32,76,119), RGB(37,54,73), RGB(34,91,166), RGB(20,112,78),
        RGB(33,44,58), RGB(116,136,159), RGB(76,55,27), RGB(255,210,143), RGB(132,100,56), RGB(255,145,157)
    };
    else palette = (Palette){
        RGB(238,243,248), RGB(255,255,255), RGB(27,43,62), RGB(83,103,125), RGB(29,91,176), RGB(213,223,233),
        RGB(245,248,252), RGB(247,250,253), RGB(217,236,255), RGB(255,255,255), RGB(29,91,176), RGB(19,113,80),
        RGB(230,236,242), RGB(134,147,161), RGB(255,242,218), RGB(130,77,9), RGB(239,209,159), RGB(172,38,53)
    };
}
static void apply_theme(int dark) {
    HBRUSH previous_bg = app.background, previous_surface = app.white;
    app.dark_mode = dark; set_palette(dark);
    app.background = CreateSolidBrush(BG); app.white = CreateSolidBrush(palette.surface);
    SetClassLongPtrW(app.window, GCLP_HBRBACKGROUND, (LONG_PTR)app.background);
    ListView_SetBkColor(app.memory, palette.surface); ListView_SetTextBkColor(app.memory, palette.surface); ListView_SetTextColor(app.memory, INK);
    ListView_SetExtendedListViewStyleEx(app.memory, LVS_EX_GRIDLINES, dark ? 0u : LVS_EX_GRIDLINES);
    SetWindowTextW(app.theme, dark ? L"Modo claro" : L"Modo oscuro");
    BOOL dark_title = dark ? TRUE : FALSE;
    /* Attribute 20 is DWMWA_USE_IMMERSIVE_DARK_MODE; unsupported Windows ignore it. */
    DwmSetWindowAttribute(app.window, 20, &dark_title, sizeof dark_title);
    if (previous_bg) DeleteObject(previous_bg);
    if (previous_surface) DeleteObject(previous_surface);
    RedrawWindow(app.window, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_FRAME | RDW_ALLCHILDREN);
}
static void show_error(const wchar_t *text) { MessageBoxW(app.window, text, L"ISA3C · Revisá este dato", MB_OK | MB_ICONWARNING); }
static wchar_t *to_wide(const char *text) {
    int n = MultiByteToWideChar(CP_UTF8, 0, text, -1, NULL, 0);
    if (!n) return NULL;
    wchar_t *out = malloc((size_t)n * sizeof *out);
    if (out) MultiByteToWideChar(CP_UTF8, 0, text, -1, out, n);
    return out;
}
static char *to_utf8(const wchar_t *text) {
    int n = WideCharToMultiByte(CP_UTF8, 0, text, -1, NULL, 0, NULL, NULL);
    if (!n) return NULL;
    char *out = malloc((size_t)n);
    if (out) WideCharToMultiByte(CP_UTF8, 0, text, -1, out, n, NULL, NULL);
    return out;
}
static wchar_t *control_text(HWND control) {
    int n = GetWindowTextLengthW(control);
    wchar_t *text = calloc((size_t)n + 1u, sizeof *text);
    if (text) GetWindowTextW(control, text, n + 1);
    return text;
}
static char *source_text(void) {
    wchar_t *text = control_text(app.code);
    if (!text) return NULL;
    size_t dst = 0;
    for (size_t src = 0; text[src]; ++src) {
        if (text[src] == L'\r') { text[dst++] = L'\n'; if (text[src + 1u] == L'\n') ++src; }
        else text[dst++] = text[src];
    }
    text[dst] = 0;
    char *out = to_utf8(text); free(text); return out;
}
static void message(const wchar_t *text) {
    wcsncpy(app.status_text, text, 1023u); app.status_text[1023] = 0;
    if (app.status) SetWindowTextW(app.status, app.status_text);
}
static void report_asm_error(const AsmError *error) {
    wchar_t *detail = to_wide(error->text), *path = to_wide(error->path);
    wchar_t text[2300];
    if (error->line) swprintf(text, 2300, L"No se pudo ensamblar. Línea %u.\n\n%ls\n\n%ls", error->line, detail ? detail : L"Error", path ? path : L"");
    else swprintf(text, 2300, L"%ls\n\n%ls", detail ? detail : L"No se pudo cargar el programa.", path ? path : L"");
    message(L"Hay un error: corregí el fuente y volvé a ensamblar.");
    show_error(text); free(detail); free(path);
    if (error->line && !app.object_mode) {
        LRESULT start = SendMessageW(app.code, EM_LINEINDEX, (WPARAM)(error->line - 1u), 0);
        if (start >= 0) { SendMessageW(app.code, EM_SETSEL, (WPARAM)start, start); SendMessageW(app.code, EM_SCROLLCARET, 0, 0); SetFocus(app.code); }
    }
}
static void stop_execution(void) {
    KillTimer(app.window, 1); app.timer_active = 0;
    gui_session_pause(app.session);
    SendMessageW(app.code, EM_SETREADONLY, (WPARAM)app.object_mode, 0);
}
static void update_title(void) {
    wchar_t text[1100]; const wchar_t *name = wcsrchr(app.path, L'\\');
    if (!name) name = wcsrchr(app.path, L'/');
    name = name ? name + 1 : app.path;
    swprintf(text, 1100, L"ISA Grupo 6 · %ls%ls", *name ? name : L"Sin título", app.disk_dirty ? L" *" : L"");
    SetWindowTextW(app.window, text);
    SetWindowTextW(app.file_path, *app.path ? app.path : L"Nuevo programa · guardalo como .asm cuando quieras conservarlo");
}
static void memory_origin(uint16_t origin) {
    wchar_t value[20]; app.memory_base = origin;
    swprintf(value, 20, L"x%04X", (unsigned)origin); SetWindowTextW(app.address, value);
    ListView_DeleteAllItems(app.memory);
}
static void set_source(const wchar_t *text, int object_mode) {
    app.suppress_change = 1; app.object_mode = object_mode;
    SendMessageW(app.code, EM_SETREADONLY, FALSE, 0);
    wchar_t *crlf = gui_editor_crlf(text);
    if (crlf) { SetWindowTextW(app.code, crlf); free(crlf); }
    SendMessageW(app.code, EM_EMPTYUNDOBUFFER, 0, 0);
    SendMessageW(app.code, EM_SETREADONLY, (WPARAM)object_mode, 0);
    app.suppress_change = 0; app.disk_dirty = 0; app.build_dirty = !object_mode;
    InvalidateRect(app.gutter, NULL, TRUE); update_title();
}
static int save_source(int save_as) {
    if (app.object_mode) { show_error(L"Este archivo es un objeto binario. Usá Archivo > Exportar objeto, o abrí su fuente .asm para editarlo."); return 0; }
    wchar_t path[PATH_CAP]; wcsncpy(path, app.path, PATH_CAP - 1u); path[PATH_CAP - 1u] = 0;
    if (save_as || !*path) {
        if (!*path) wcscpy(path, L"mi_programa.asm");
        OPENFILENAMEW dialog = {0}; dialog.lStructSize = sizeof dialog; dialog.hwndOwner = app.window;
        dialog.lpstrFilter = L"Assembly ISA3C (*.asm)\0*.asm\0Todos los archivos\0*.*\0";
        dialog.lpstrFile = path; dialog.nMaxFile = PATH_CAP; dialog.lpstrDefExt = L"asm";
        dialog.lpstrInitialDir = app.project; dialog.Flags = OFN_OVERWRITEPROMPT | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR;
        if (!GetSaveFileNameW(&dialog)) return 0;
    }
    char *text = source_text(); if (!text) { show_error(L"No hay memoria suficiente para guardar el fuente."); return 0; }
    FILE *file = _wfopen(path, L"wb"); size_t n = strlen(text); int ok = 0;
    if (file) { ok = fwrite(text, 1, n, file) == n; if (fclose(file)) ok = 0; }
    free(text);
    if (!ok) { show_error(L"No se pudo guardar el archivo. Revisá la carpeta y sus permisos."); return 0; }
    if (wcscmp(app.path, path)) app.build_dirty = 1;
    wcscpy(app.path, path); app.disk_dirty = 0; update_title(); message(L"Fuente guardado en UTF-8."); refresh(); return 1;
}
static int may_replace(void) {
    stop_execution();
    if (!app.disk_dirty) return 1;
    int answer = MessageBoxW(app.window, L"Hay cambios en el código que todavía no guardaste.\n\n¿Querés guardarlos antes de continuar?", L"Conservar el trabajo", MB_YESNOCANCEL | MB_ICONQUESTION);
    return answer == IDYES ? save_source(0) : answer == IDNO;
}
static int load_file(const wchar_t *path) {
    AsmError error = {0}; const wchar_t *ext = wcsrchr(path, L'.');
    stop_execution();
    if (ext && !_wcsicmp(ext, L".obj")) {
        char *name = to_utf8(path);
        int ok = name && gui_session_object(app.session, name, &error); free(name);
        if (!ok) { report_asm_error(&error); return 0; }
        wcscpy(app.path, path);
        set_source(L"; Objeto binario ISA3C cargado.\r\n; Podés ejecutarlo, avanzar paso a paso y revisar la memoria.\r\n; Para editar el programa, abrí su archivo fuente .asm.\r\n; Las etiquetas no se conservan dentro de un .obj.\r\n", 1);
        memory_origin(app.session->image.origin);
        message(L"Objeto cargado. Ya podés ejecutar o avanzar paso a paso."); refresh(); return 1;
    }
    FILE *file = _wfopen(path, L"rb");
    if (!file) { show_error(L"No se pudo abrir el archivo fuente."); return 0; }
    if (fseek(file, 0, SEEK_END)) { fclose(file); return 0; }
    long length = ftell(file);
    if (length < 0 || (unsigned long)length > LC3_MAX_SOURCE || fseek(file, 0, SEEK_SET)) {
        fclose(file); show_error(L"El fuente supera 1 MiB o no se pudo leer."); return 0;
    }
    char *bytes = calloc((size_t)length + 3u, 1u); if (!bytes) { fclose(file); return 0; }
    size_t n = fread(bytes, 1, (size_t)length, file); int ok = !ferror(file); fclose(file);
    if (!ok) { free(bytes); show_error(L"No se pudo leer todo el archivo."); return 0; }
    wchar_t *text = NULL;
    if (n >= 2u && (unsigned char)bytes[0] == 0xFFu && (unsigned char)bytes[1] == 0xFEu) {
        text = calloc(n / 2u + 1u, sizeof *text);
        if (text) for (size_t i = 2; i + 1u < n; i += 2u) text[(i - 2u) / 2u] = (wchar_t)((unsigned char)bytes[i] | (unsigned)(unsigned char)bytes[i + 1u] << 8u);
    } else {
        const char *start = bytes;
        if (n >= 3u && !memcmp(bytes, "\xEF\xBB\xBF", 3)) start += 3;
        int count = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, start, -1, NULL, 0);
        UINT cp = count ? CP_UTF8 : 1252u;
        count = MultiByteToWideChar(cp, 0, start, -1, NULL, 0);
        text = count ? malloc((size_t)count * sizeof *text) : NULL;
        if (text) MultiByteToWideChar(cp, 0, start, -1, text, count);
    }
    free(bytes); if (!text) { show_error(L"No se pudo decodificar el texto."); return 0; }
    wcscpy(app.path, path); set_source(text, 0); free(text);
    gui_session_dispose(app.session); memory_origin(0x3000); app.shown_output = (size_t)-1;
    message(L"Fuente abierto. Ensamblá con F7; F5 también ensambla si hace falta."); refresh(); return 1;
}
static void open_dialog(void) {
    if (!may_replace()) return;
    wchar_t path[PATH_CAP] = L"";
    OPENFILENAMEW dialog = {0}; dialog.lStructSize = sizeof dialog; dialog.hwndOwner = app.window;
    dialog.lpstrFilter = L"Assembly y objetos (*.asm;*.obj)\0*.asm;*.obj\0Todos los archivos\0*.*\0";
    dialog.lpstrFile = path; dialog.nMaxFile = PATH_CAP; dialog.lpstrInitialDir = app.project;
    dialog.Flags = OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR;
    if (GetOpenFileNameW(&dialog)) load_file(path);
}
static int assemble(void) {
    if (app.object_mode) return app.session->loaded;
    stop_execution();
    char *source = source_text(), *path = NULL, *default_dir = NULL, *custom_dir = NULL;
    wchar_t wide_path[PATH_CAP], wide_dir[PATH_CAP];
    if (*app.path) wcscpy(wide_path, app.path);
    else swprintf(wide_path, PATH_CAP, L"%ls\\sin_titulo.asm", app.project);
    swprintf(wide_dir, PATH_CAP, L"%ls\\benchmark\\modulos", app.project);
    path = to_utf8(wide_path); default_dir = to_utf8(wide_dir); custom_dir = to_utf8(app.library);
    const char *dirs[2] = {default_dir, custom_dir};
    AsmError error = {0};
    int ok = source && path && default_dir && custom_dir && strlen(source) <= LC3_MAX_SOURCE &&
             gui_session_assemble(app.session, source, path, dirs, *app.library ? 2u : 1u, &error);
    free(source); free(path); free(default_dir); free(custom_dir);
    if (!ok) { if (!*error.text) strcpy(error.text, "Fuente demasiado grande o sin memoria."); app.build_dirty = 1; report_asm_error(&error); refresh(); return 0; }
    app.build_dirty = 0; memory_origin(app.session->image.origin); app.shown_output = (size_t)-1;
    wchar_t text[220]; swprintf(text, 220, L"Ensamblado: %zu bytes, %zu etiquetas. Listo para ejecutar.", app.session->image.count, app.session->image.symbol_count);
    message(text); refresh(); return 1;
}
static int ensure_built(void) { return (app.session->loaded && !app.build_dirty) || assemble(); }
static void export_object(void) {
    if (!ensure_built()) return;
    wchar_t path[PATH_CAP] = L"mi_programa.obj";
    OPENFILENAMEW dialog = {0}; dialog.lStructSize = sizeof dialog; dialog.hwndOwner = app.window;
    dialog.lpstrFilter = L"Objeto ISA3C (*.obj)\0*.obj\0"; dialog.lpstrFile = path; dialog.nMaxFile = PATH_CAP;
    dialog.lpstrDefExt = L"obj"; dialog.lpstrInitialDir = app.project;
    dialog.Flags = OFN_OVERWRITEPROMPT | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR;
    if (!GetSaveFileNameW(&dialog)) return;
    char *utf8 = to_utf8(path); AsmError error = {0};
    int ok = utf8 && lc3_object_write(utf8, &app.session->image, &error); free(utf8);
    if (!ok) report_asm_error(&error); else message(L"Objeto exportado. Se puede abrir con esta interfaz o con simulador.exe.");
}
static const wchar_t *state_name(void) {
    if (app.build_dirty) return L"Falta ensamblar";
    switch (app.session->state) {
        case GUI_READY: return L"Listo"; case GUI_PAUSED: return L"Pausado";
        case GUI_RUNNING: return L"En ejecución"; case GUI_WAITING: return L"Espera teclado";
        case GUI_BREAKPOINT: return L"Breakpoint"; case GUI_LIMIT: return L"Límite alcanzado";
        case GUI_HALTED: return L"Finalizado · HALT"; case GUI_FAULT: return L"Excepción";
        default: return L"Sin programa";
    }
}
static int signed_word(uint16_t word) { return word & 0x8000u ? (int)word - 65536 : (int)word; }
static void selection_info(void) {
    int index = ListView_GetNextItem(app.memory, -1, LVNI_SELECTED);
    if (index < 0 || !app.session->loaded) { SetWindowTextW(app.selection, L"Memoria: doble clic para alternar un breakpoint."); return; }
    uint16_t address = (uint16_t)((unsigned)app.memory_base + 2u * (unsigned)index);
    uint16_t word = lc3_peek(&app.session->machine, address); wchar_t text[200];
    swprintf(text, 200, L"x%04X = %d  |  Q3.12 %.6f  |  Q7.8 %.6f", (unsigned)address, signed_word(word), (double)signed_word(word) / 4096.0, (double)signed_word(word) / 256.0);
    SetWindowTextW(app.selection, text);
}
static void memory_refresh(void) {
    HWND list = app.memory; Lc3 *m = &app.session->machine;
    int rows = app.session->loaded ? (int)((65536u - (unsigned)app.memory_base) / 2u) : 0;
    if (rows > 128) rows = 128;
    SendMessageW(list, WM_SETREDRAW, FALSE, 0);
    int previous = ListView_GetItemCount(list);
    while (previous > rows) ListView_DeleteItem(list, --previous);
    for (int i = 0; i < rows; ++i) {
        uint16_t address = (uint16_t)((unsigned)app.memory_base + 2u * (unsigned)i);
        uint16_t word = lc3_peek(m, address);
        wchar_t cell[260]; char instruction[100];
        if (i >= previous) { LVITEMW item = {0}; item.mask = LVIF_TEXT; item.iItem = i; item.pszText = L""; ListView_InsertItem(list, &item); }
        ListView_SetItemText(list, i, 0, app.session->breakpoints[address] ? L"●" : L"");
        swprintf(cell, 260, L"x%04X", (unsigned)address); ListView_SetItemText(list, i, 1, cell);
        swprintf(cell, 260, L"x%04X", (unsigned)word); ListView_SetItemText(list, i, 2, cell);
        swprintf(cell, 260, L"%d", signed_word(word)); ListView_SetItemText(list, i, 3, cell);
        lc3_disassemble(address, word, instruction, sizeof instruction);
        wchar_t *wide = to_wide(instruction); ListView_SetItemText(list, i, 4, wide ? wide : L""); free(wide);
        cell[0] = 0;
        for (size_t j = 0; j < app.session->image.symbol_count; ++j) {
            if (app.session->image.symbols[j].address == address) {
                wide = to_wide(app.session->image.symbols[j].name);
                if (wide) { wcsncpy(cell, wide, 259u); cell[259] = 0; free(wide); } break;
            }
        }
        ListView_SetItemText(list, i, 5, cell);
    }
    SendMessageW(list, WM_SETREDRAW, TRUE, 0); InvalidateRect(list, NULL, FALSE); selection_info();
}
static void refresh(void) {
    GuiSession *s = app.session; Lc3 *m = &s->machine; wchar_t text[500];
    for (unsigned i = 0; i < 8; ++i) {
        swprintf(text, 500, L"R%u    x%04X\n%d", i, (unsigned)m->r[i], signed_word(m->r[i]));
        SetWindowTextW(app.registers[i], text); InvalidateRect(app.registers[i], NULL, FALSE);
    }
    wchar_t cc = m->psr & 4u ? L'N' : m->psr & 2u ? L'Z' : L'P';
    swprintf(text, 500, L"PC x%04X    IR x%04X    CC %lc\r\nPSR x%04X · %ls", (unsigned)m->pc, (unsigned)m->ir, cc, (unsigned)m->psr, m->psr & 0x8000u ? L"Usuario" : L"Supervisor");
    SetWindowTextW(app.cpu_meta, s->loaded ? text : L"PC —    IR —    CC —\r\nEnsamblá o abrí un objeto para comenzar.");
    int include = SendMessageW(app.include_system, BM_GETCHECK, 0, 0) == BST_CHECKED;
    uint64_t selected = include ? m->instructions : s->program_instructions;
    swprintf(text, 500, L"%llu instrucciones %ls", (unsigned long long)selected, include ? L"en total" : L"del programa"); SetWindowTextW(app.counter, text);
    swprintf(text, 500, L"Programa: %llu   Sistema: %llu   Total: %llu", (unsigned long long)s->program_instructions, (unsigned long long)s->system_instructions, (unsigned long long)m->instructions);
    SetWindowTextW(app.breakdown, text);
    swprintf(text, 500, L"PROCESADOR  ·  %ls", state_name()); SetWindowTextW(app.cpu_title, text);
    if (app.shown_output != s->output_length) {
        wchar_t *output = to_wide(s->output);
        if (output) {
            size_t n = wcslen(output); wchar_t *crlf = malloc((n * 2u + 1u) * sizeof *crlf);
            if (crlf) {
                size_t dst = 0;
                for (size_t i = 0; i < n; ++i) { if (output[i] == L'\n' && (!i || output[i - 1u] != L'\r')) crlf[dst++] = L'\r'; crlf[dst++] = output[i]; }
                crlf[dst] = 0; SetWindowTextW(app.console, crlf);
                int end = GetWindowTextLengthW(app.console);
                SendMessageW(app.console, EM_SETSEL, (WPARAM)end, (LPARAM)end); SendMessageW(app.console, EM_SCROLLCARET, 0, 0); free(crlf);
            }
            free(output);
        }
        app.shown_output = s->output_length;
    }
    int running = active();
    EnableWindow(app.buttons[0], !running); EnableWindow(app.buttons[1], !running);
    EnableWindow(app.buttons[3], !running && !app.object_mode);
    EnableWindow(app.buttons[4], !running); EnableWindow(app.buttons[5], running);
    EnableWindow(app.buttons[6], !running); EnableWindow(app.buttons[7], s->loaded);
    EnableWindow(app.send, s->loaded); EnableWindow(app.raw, s->loaded); EnableWindow(app.input, s->loaded);
    SendMessageW(app.code, EM_SETREADONLY, (WPARAM)(running || app.object_mode), 0);
    memory_refresh();
}
static void go_address(int to_pc) {
    uint16_t address; wchar_t *text = control_text(app.address); char *utf8 = text ? to_utf8(text) : NULL; free(text);
    int ok = to_pc && app.session->loaded ? (address = app.session->machine.pc, 1) : utf8 && gui_session_address(app.session, utf8, &address);
    free(utf8);
    if (!ok) { show_error(L"Escribí una dirección como x3000 o una etiqueta visible, por ejemplo RESULTADO."); return; }
    if (address & 1u) { --address; message(L"La vista muestra palabras: se alineó la dirección al byte par anterior."); }
    app.memory_base = address; wchar_t value[20]; swprintf(value, 20, L"x%04X", (unsigned)address); SetWindowTextW(app.address, value);
    ListView_DeleteAllItems(app.memory); memory_refresh(); ListView_SetItemState(app.memory, 0, LVIS_SELECTED | LVIS_FOCUSED, LVIS_SELECTED | LVIS_FOCUSED); selection_info();
}
static void toggle_breakpoint(void) {
    int selected = ListView_GetNextItem(app.memory, -1, LVNI_SELECTED);
    if (selected < 0) { show_error(L"Seleccioná una fila de memoria. Después pulsá BP o F9; también sirve hacer doble clic en la fila."); return; }
    uint16_t address = (uint16_t)((unsigned)app.memory_base + 2u * (unsigned)selected);
    if (gui_session_breakpoint(app.session, address)) {
        wchar_t text[150]; swprintf(text, 150, L"Breakpoint %ls en x%04X.", app.session->breakpoints[address] ? L"activado" : L"quitado", (unsigned)address); message(text); memory_refresh();
    }
}
static void send_input(int newline) {
    wchar_t *text = control_text(app.input); if (!text) return;
    size_t n = wcslen(text);
    if (!n && !newline) { free(text); SetFocus(app.console); message(L"Consola enfocada: cada tecla se envía directamente a la ISA."); return; }
    unsigned char bytes[LC3_INPUT_SIZE]; size_t count = 0;
    for (size_t i = 0; i < n; ++i) {
        if (text[i] > 127 || count >= sizeof bytes) { free(text); show_error(L"Enviá hasta 255 caracteres ASCII por vez. Para el programa, Enter se representa con LF."); return; }
        bytes[count++] = (unsigned char)text[i];
    }
    free(text);
    if (newline) { if (count >= sizeof bytes) { show_error(L"La línea es demasiado larga."); return; } bytes[count++] = '\n'; }
    if (!gui_session_input(app.session, bytes, count)) { show_error(L"La cola de teclado está llena o falta ensamblar. Ejecutá el programa para consumir la entrada."); return; }
    SetWindowTextW(app.input, L""); message(L"Entrada enviada. Si el programa estaba esperando, continuará automáticamente.");
    if (!active()) refresh();
}
static void start_run(void) {
    if (active() || !ensure_built()) return;
    if (!(app.session->machine.mcr & 0x8000u)) {
        AsmError error = {0}; if (!gui_session_reset(app.session, &error)) { report_asm_error(&error); return; }
        app.shown_output = (size_t)-1;
    }
    wchar_t value[80], *end; GetWindowTextW(app.limit, value, 80); errno = 0;
    unsigned long long limit = wcstoull(value, &end, 10);
    if (errno || *end || !limit || value[0] == L'-') { show_error(L"El límite total debe ser un entero positivo, por ejemplo 1000000. Siempre incluye las instrucciones del sistema."); return; }
    if (!gui_session_run(app.session, (uint64_t)limit)) return;
    SetTimer(app.window, 1, 16, NULL); app.timer_active = 1;
    message(L"Ejecutando. F6 pausa; podés escribir directamente en la consola."); SetFocus(app.console); refresh();
}
static void execution_tick(void) {
    if (!active()) return;
    GuiState before = app.session->state;
    if (!gui_session_tick(app.session, 12000u)) return;
    if (!active()) {
        KillTimer(app.window, 1); app.timer_active = 0;
        switch (app.session->state) {
            case GUI_HALTED: message(L"HALT: ejecución finalizada. Los resultados siguen en registros y memoria."); break;
            case GUI_FAULT: { wchar_t text[180]; swprintf(text, 180, L"Ejecución detenida por excepción x%03X. Revisá dirección, permisos y pila.", app.session->machine.last_exception); message(text); break; }
            case GUI_LIMIT: message(L"Se alcanzó el límite total. F5 continúa; Reiniciar vuelve al principio."); break;
            case GUI_BREAKPOINT: message(L"Breakpoint: detenido antes de ejecutar la instrucción. F5 continúa o F10 da un paso."); break;
            default: break;
        }
    } else if (app.session->state == GUI_WAITING) message(L"Esperando teclado. Hacé clic en la consola y pulsá una tecla, o enviá una línea desde abajo.");
    ULONGLONG now = GetTickCount64();
    if (!active() || before == GUI_WAITING || before != app.session->state || now - app.last_refresh >= 100u) { refresh(); app.last_refresh = now; }
}
static LRESULT CALLBACK input_proc(HWND window, UINT msg, WPARAM wp, LPARAM lp, UINT_PTR subclass, DWORD_PTR data) {
    (void)subclass; (void)data;
    if (msg == WM_GETDLGCODE && lp && ((MSG *)lp)->wParam == VK_RETURN) return DLGC_WANTMESSAGE;
    if (msg == WM_KEYDOWN && wp == VK_RETURN) { send_input(1); return 0; }
    if (msg == WM_CHAR && wp == VK_RETURN) return 0;
    return DefSubclassProc(window, msg, wp, lp);
}
static LRESULT CALLBACK address_proc(HWND window, UINT msg, WPARAM wp, LPARAM lp, UINT_PTR subclass, DWORD_PTR data) {
    (void)subclass; (void)data;
    if (msg == WM_GETDLGCODE && lp && ((MSG *)lp)->wParam == VK_RETURN) return DLGC_WANTMESSAGE;
    if (msg == WM_KEYDOWN && wp == VK_RETURN) { go_address(0); return 0; }
    if (msg == WM_CHAR && wp == VK_RETURN) return 0;
    return DefSubclassProc(window, msg, wp, lp);
}
static LRESULT CALLBACK console_proc(HWND window, UINT msg, WPARAM wp, LPARAM lp, UINT_PTR subclass, DWORD_PTR data) {
    (void)subclass; (void)data;
    if (msg == WM_CHAR && !(GetKeyState(VK_CONTROL) & 0x8000) && app.session->loaded) {
        if (wp < 128u && wp != 27u) {
            unsigned char byte = (unsigned char)(wp == '\r' ? '\n' : wp);
            if (!gui_session_input(app.session, &byte, 1)) message(L"La cola del teclado está llena.");
            return 0;
        }
    }
    return DefSubclassProc(window, msg, wp, lp);
}
static LRESULT CALLBACK checkbox_proc(HWND window, UINT msg, WPARAM wp, LPARAM lp, UINT_PTR subclass, DWORD_PTR data) {
    (void)subclass; (void)data;
    if (msg == WM_ERASEBKGND) return 1;
    if (msg == WM_PAINT) {
        PAINTSTRUCT paint; HDC dc = BeginPaint(window, &paint); RECT rect; GetClientRect(window, &rect);
        FillRect(dc, &rect, app.white); SetBkMode(dc, TRANSPARENT); SetTextColor(dc, INK); SelectObject(dc, app.ui_font);
        int checked = SendMessageW(window, BM_GETCHECK, 0, 0) == BST_CHECKED;
        RECT box = {px(1), (rect.bottom - px(18)) / 2, px(19), (rect.bottom + px(18)) / 2};
        rounded(dc, box, checked ? palette.primary : palette.surface, checked ? palette.primary : MUTED);
        if (checked) {
            HPEN pen = CreatePen(PS_SOLID, px(2), RGB(255,255,255)); HGDIOBJ old = SelectObject(dc, pen);
            MoveToEx(dc, box.left + px(4), box.top + px(9), NULL); LineTo(dc, box.left + px(8), box.top + px(13)); LineTo(dc, box.left + px(14), box.top + px(5));
            SelectObject(dc, old); DeleteObject(pen);
        }
        rect.left = px(27); wchar_t text[150]; GetWindowTextW(window, text, 150); DrawTextW(dc, text, -1, &rect, DT_SINGLELINE | DT_VCENTER | DT_LEFT);
        if (GetFocus() == window) { InflateRect(&rect, -px(2), -px(2)); DrawFocusRect(dc, &rect); }
        EndPaint(window, &paint); return 0;
    }
    LRESULT result = DefSubclassProc(window, msg, wp, lp);
    if (msg == BM_SETCHECK || msg == WM_LBUTTONUP || msg == WM_KEYUP || msg == WM_SETFOCUS || msg == WM_KILLFOCUS) InvalidateRect(window, NULL, FALSE);
    return result;
}
static LRESULT CALLBACK header_proc(HWND window, UINT msg, WPARAM wp, LPARAM lp, UINT_PTR subclass, DWORD_PTR data) {
    (void)subclass; (void)data;
    if (msg == WM_ERASEBKGND) return 1;
    if (msg == WM_PAINT) {
        PAINTSTRUCT paint; HDC dc = BeginPaint(window, &paint); RECT rect; GetClientRect(window, &rect);
        HBRUSH brush = CreateSolidBrush(palette.registers); FillRect(dc, &rect, brush); DeleteObject(brush);
        SelectObject(dc, app.small_font); SetBkMode(dc, TRANSPARENT); SetTextColor(dc, INK);
        int count = Header_GetItemCount(window);
        for (int i = 0; i < count; ++i) {
            RECT item; Header_GetItemRect(window, i, &item); wchar_t text[100]; HDITEMW header = {0};
            header.mask = HDI_TEXT; header.pszText = text; header.cchTextMax = 100; Header_GetItem(window, i, &header);
            item.left += px(5); DrawTextW(dc, text, -1, &item, DT_SINGLELINE | DT_VCENTER | DT_LEFT | DT_END_ELLIPSIS);
        }
        EndPaint(window, &paint); return 0;
    }
    return DefSubclassProc(window, msg, wp, lp);
}
static HWND child(const wchar_t *kind, const wchar_t *text, DWORD style, int id, HFONT font) {
    HWND window = CreateWindowExW(0, kind, text, WS_CHILD | WS_VISIBLE | style, 0, 0, 0, 0, app.window, (HMENU)(INT_PTR)id, app.instance, NULL);
    SendMessageW(window, WM_SETFONT, (WPARAM)font, FALSE); return window;
}
static HWND label(const wchar_t *text, HFONT font) { return child(L"STATIC", text, SS_LEFT | SS_NOPREFIX, 0, font); }
static HWND button(const wchar_t *text, int id) { return child(L"BUTTON", text, BS_OWNERDRAW | WS_TABSTOP, id, app.ui_font); }
static void place(HWND control, int x, int y, int w, int h) { MoveWindow(control, px(x), px(y), px(w), px(h), TRUE); }
static void create_controls(void) {
    app.title = label(L"ISA Grupo 6", app.heading_font);
    app.subtitle = label(L"Programá, ejecutá y mirá qué hace tu procesador.", app.ui_font);
    app.theme = button(L"Modo oscuro", ID_THEME);
    const wchar_t *names[] = {L"Nuevo", L"Abrir", L"Guardar", L"Ensamblar F7", L"Ejecutar F5", L"Pausar F6", L"Paso F10", L"Reiniciar F2"};
    for (int i = 0; i < 8; ++i) app.buttons[i] = button(names[i], ID_NEW + i);
    app.limit_title = label(L"Límite total por ejecución", app.small_font);
    app.limit = child(L"EDIT", L"1000000", WS_BORDER | WS_TABSTOP | ES_NUMBER | ES_RIGHT | ES_AUTOHSCROLL, ID_LIMIT, app.ui_font);
    app.file_title = label(L"CÓDIGO ASSEMBLY", app.ui_font);
    app.file_path = child(L"STATIC", L"", SS_LEFT | SS_PATHELLIPSIS | SS_NOPREFIX, 0, app.small_font);
    app.gutter = child(L"STATIC", L"", SS_OWNERDRAW, ID_GUTTER, app.mono_font);
    app.code = child(L"EDIT", L"", WS_BORDER | WS_TABSTOP | WS_VSCROLL | WS_HSCROLL | ES_MULTILINE | ES_AUTOVSCROLL | ES_AUTOHSCROLL | ES_WANTRETURN, ID_CODE, app.mono_font);
    SendMessageW(app.code, EM_SETLIMITTEXT, LC3_MAX_SOURCE, 0);
    SendMessageW(app.code, EM_SETMARGINS, EC_LEFTMARGIN | EC_RIGHTMARGIN, MAKELPARAM(px(10), px(10)));
    gui_editor_attach(app.code);
    app.cpu_title = label(L"PROCESADOR", app.ui_font);
    for (int i = 0; i < 8; ++i) app.registers[i] = child(L"STATIC", L"", SS_OWNERDRAW, ID_REG0 + i, app.register_font);
    app.cpu_meta = label(L"", app.small_font);
    app.counter = label(L"0 instrucciones en total", app.count_font);
    app.breakdown = label(L"", app.small_font);
    app.include_system = child(L"BUTTON", L"Incluir instrucciones del sistema", BS_AUTOCHECKBOX | WS_TABSTOP, ID_INCLUDE_SYSTEM, app.ui_font);
    SendMessageW(app.include_system, BM_SETCHECK, BST_CHECKED, 0);
    SetWindowSubclass(app.include_system, checkbox_proc, 1, 0);
    app.memory_title = label(L"MEMORIA Y BREAKPOINTS", app.ui_font);
    app.address = child(L"EDIT", L"x3000", WS_BORDER | WS_TABSTOP | ES_AUTOHSCROLL, ID_ADDRESS, app.mono_font);
    app.go = button(L"Ir", ID_GO); app.pc = button(L"PC", ID_PC); app.bp = button(L"BP · F9", ID_BP);
    app.memory = child(WC_LISTVIEWW, L"", WS_BORDER | WS_TABSTOP | LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS, ID_MEMORY, app.small_font);
    ListView_SetExtendedListViewStyle(app.memory, LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_GRIDLINES | LVS_EX_LABELTIP);
    const wchar_t *columns[] = {L"BP", L"Dirección", L"Hex", L"Decimal", L"Instrucción", L"Etiqueta"};
    for (int i = 0; i < 6; ++i) { LVCOLUMNW col = {0}; col.mask = LVCF_TEXT | LVCF_WIDTH; col.pszText = (LPWSTR)columns[i]; col.cx = px(70); ListView_InsertColumn(app.memory, i, &col); }
    SetWindowSubclass(ListView_GetHeader(app.memory), header_proc, 1, 0);
    app.memory_hint = label(L"Doble clic: breakpoint. Los datos también se desensamblan.", app.small_font);
    app.console_title = label(L"CONSOLA DEL PROGRAMA", app.ui_font);
    app.console = child(L"EDIT", L"", WS_BORDER | WS_TABSTOP | WS_VSCROLL | ES_MULTILINE | ES_AUTOVSCROLL | ES_READONLY | ES_WANTRETURN, ID_CONSOLE, app.mono_font);
    SendMessageW(app.console, EM_SETLIMITTEXT, GUI_OUTPUT_CAPACITY * 2u, 0);
    app.input = child(L"EDIT", L"", WS_BORDER | WS_TABSTOP | ES_AUTOHSCROLL, ID_INPUT, app.ui_font);
    SendMessageW(app.input, EM_SETCUEBANNER, TRUE, (LPARAM)L"Texto para el programa · Enter envía la línea");
    SendMessageW(app.input, EM_SETLIMITTEXT, 255, 0);
    app.send = button(L"Enviar línea", ID_SEND); app.raw = button(L"Solo texto", ID_SEND_RAW);
    app.input_hint = label(L"Para una tecla: clic en la consola y escribí. La consola conserva la salida.", app.small_font);
    app.status = label(L"Listo", app.small_font); app.selection = label(L"", app.small_font);
    SetWindowSubclass(app.input, input_proc, 1, 0); SetWindowSubclass(app.console, console_proc, 1, 0); SetWindowSubclass(app.address, address_proc, 1, 0);
}
static void layout(void) {
    RECT client; GetClientRect(app.window, &client);
    int w = MulDiv(client.right, 96, app.dpi), h = MulDiv(client.bottom, 96, app.dpi);
    int left = (w - 48) * 55 / 100, right_x = left + 32, right = w - right_x - 16;
    if (right < 490) { right = 490; left = w - right - 48; right_x = left + 32; }
    place(app.title, 20, 10, 230, 39); place(app.subtitle, 266, 24, w - 460, 27); place(app.theme, w - 170, 15, 150, 36);
    const int widths[] = {76, 80, 94, 116, 114, 86, 100, 110}; int x = 16;
    for (int i = 0; i < 8; ++i) { place(app.buttons[i], x, 78, widths[i], 42); x += widths[i] + 8; }
    place(app.limit_title, w - 220, 75, 204, 19); place(app.limit, w - 220, 95, 204, 28);
    app.left_card = (RECT){px(16), px(136), px(16 + left), px(h - 42)};
    app.right_card = (RECT){px(right_x), px(136), px(w - 16), px(h - 42)};
    int lx = 28, lw = left - 24, rx = right_x + 12, rw = right - 24;
    place(app.file_title, lx, 148, lw, 24); place(app.file_path, lx, 176, lw, 20);
    int editor_y = 204, editor_h = (h - 42 - editor_y) * 52 / 100;
    if (editor_h < 155) editor_h = 155;
    place(app.gutter, lx, editor_y, 40, editor_h); place(app.code, lx + 42, editor_y, lw - 42, editor_h);
    int console_y = editor_y + editor_h + 40, input_y = h - 105;
    place(app.console_title, lx, console_y - 29, lw, 23);
    place(app.console, lx, console_y, lw, input_y - console_y - 10);
    place(app.input, lx, input_y, lw - 238, 34); place(app.send, lx + lw - 228, input_y, 112, 34); place(app.raw, lx + lw - 108, input_y, 108, 34);
    place(app.input_hint, lx, input_y + 39, lw, 22);
    place(app.cpu_title, rx, 148, rw, 24);
    int cell = (rw - 18) / 4;
    for (int i = 0; i < 8; ++i) place(app.registers[i], rx + (i % 4) * (cell + 6), 177 + (i / 4) * 48, cell, 43);
    place(app.cpu_meta, rx, 278, rw, 38); place(app.counter, rx, 324, rw, 30);
    place(app.breakdown, rx, 355, rw, 21); place(app.include_system, rx, 380, rw, 28);
    place(app.memory_title, rx, 420, rw, 24);
    place(app.address, rx, 450, rw - 212, 32); place(app.go, rx + rw - 202, 450, 52, 32);
    place(app.pc, rx + rw - 142, 450, 52, 32); place(app.bp, rx + rw - 82, 450, 82, 32);
    place(app.memory, rx, 490, rw, h - 568); place(app.memory_hint, rx, h - 70, rw, 20);
    int fixed = 27 + 70 + 63 + 65 + 170;
    const int cols[] = {27, 70, 63, 65, 170};
    for (int i = 0; i < 5; ++i) ListView_SetColumnWidth(app.memory, i, px(cols[i]));
    ListView_SetColumnWidth(app.memory, 5, px(rw - fixed > 125 ? rw - fixed : 125));
    place(app.status, 20, h - 28, w / 2 - 28, 22); place(app.selection, w / 2, h - 28, w / 2 - 16, 22);
    InvalidateRect(app.window, NULL, TRUE);
}
static void rounded(HDC dc, RECT rect, COLORREF fill, COLORREF border) {
    HBRUSH brush = CreateSolidBrush(fill); HPEN pen = CreatePen(PS_SOLID, 1, border);
    HGDIOBJ old_b = SelectObject(dc, brush), old_p = SelectObject(dc, pen);
    RoundRect(dc, rect.left, rect.top, rect.right, rect.bottom, px(10), px(10));
    SelectObject(dc, old_b); SelectObject(dc, old_p); DeleteObject(brush); DeleteObject(pen);
}
static void draw_control(const DRAWITEMSTRUCT *draw) {
    HDC dc = draw->hDC; RECT rect = draw->rcItem; unsigned id = draw->CtlID;
    FillRect(dc, &rect, id >= ID_NEW && id <= ID_RESET ? app.background : app.white);
    SetBkMode(dc, TRANSPARENT);
    if (id == ID_GUTTER) {
        FillRect(dc, &rect, app.white); SelectObject(dc, app.mono_font); SetTextColor(dc, MUTED);
        TEXTMETRICW tm; GetTextMetricsW(dc, &tm); int step = tm.tmHeight + tm.tmExternalLeading;
        int first = (int)SendMessageW(app.code, EM_GETFIRSTVISIBLELINE, 0, 0), count = (int)SendMessageW(app.code, EM_GETLINECOUNT, 0, 0);
        for (int line = first, y = 2; y < rect.bottom && line < count; ++line, y += step) {
            wchar_t number[24]; swprintf(number, 24, L"%d", line + 1); RECT row = {0, y, rect.right - px(6), y + step}; DrawTextW(dc, number, -1, &row, DT_RIGHT | DT_SINGLELINE);
        }
        return;
    }
    if (id >= ID_REG0 && id < ID_REG0 + 8u) {
        unsigned index = id - ID_REG0; wchar_t text[80];
        rounded(dc, rect, palette.registers, LINE); SelectObject(dc, app.register_font); SetTextColor(dc, INK);
        swprintf(text, 80, L"R%u  x%04X", index, (unsigned)app.session->machine.r[index]);
        RECT row = {rect.left + px(7), rect.top + px(3), rect.right, rect.top + px(23)}; DrawTextW(dc, text, -1, &row, DT_LEFT | DT_SINGLELINE);
        SelectObject(dc, app.small_font); SetTextColor(dc, MUTED); swprintf(text, 80, L"%d", signed_word(app.session->machine.r[index]));
        row.top = rect.top + px(23); row.bottom = rect.bottom; DrawTextW(dc, text, -1, &row, DT_LEFT | DT_SINGLELINE); return;
    }
    COLORREF fill = palette.button, color = INK, border = LINE;
    if (id == ID_RUN) { fill = GREEN; color = RGB(255,255,255); border = GREEN; }
    if (id == ID_BUILD) { fill = palette.primary; color = RGB(255,255,255); border = palette.primary; }
    if (id == ID_PAUSE) { fill = palette.pause; color = palette.pause_text; border = palette.pause_border; }
    if (draw->itemState & ODS_DISABLED) { fill = palette.disabled; color = palette.disabled_text; border = LINE; }
    else if (draw->itemState & ODS_SELECTED) { fill = RGB(GetRValue(fill) * 9 / 10, GetGValue(fill) * 9 / 10, GetBValue(fill) * 9 / 10); }
    rounded(dc, rect, fill, border); wchar_t text[100]; GetWindowTextW(draw->hwndItem, text, 100);
    SelectObject(dc, app.ui_font); SetTextColor(dc, color); DrawTextW(dc, text, -1, &rect, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
    if (draw->itemState & ODS_FOCUS) { InflateRect(&rect, -px(4), -px(4)); DrawFocusRect(dc, &rect); }
}
static HMENU create_menu(void) {
    HMENU bar = CreateMenu(), file = CreatePopupMenu(), examples = CreatePopupMenu(), debug = CreatePopupMenu(), help = CreatePopupMenu();
    AppendMenuW(file, MF_STRING, ID_NEW, L"Nuevo\tCtrl+N"); AppendMenuW(file, MF_STRING, ID_OPEN, L"Abrir ASM u objeto...\tCtrl+O");
    AppendMenuW(file, MF_STRING, ID_SAVE, L"Guardar fuente\tCtrl+S"); AppendMenuW(file, MF_STRING, ID_SAVE_AS, L"Guardar fuente como...\tCtrl+Shift+S");
    AppendMenuW(file, MF_STRING, ID_EXPORT, L"Exportar objeto .obj..."); AppendMenuW(file, MF_SEPARATOR, 0, NULL); AppendMenuW(file, MF_STRING, ID_EXIT, L"Salir");
    const wchar_t *labels[] = {L"Suma 15 + 27 (resultado en memoria)", L"Mensaje 5 + 7 (salida en consola)", L"EXP optimizada: e elevado a 3", L"Operaciones nuevas de la ISA", L"Teclado: leer y mostrar una tecla", L"Calculadora del laboratorio"};
    for (int i = 0; i < 6; ++i) AppendMenuW(examples, MF_STRING, (UINT_PTR)(ID_EX_SUM + i), labels[i]);
    AppendMenuW(debug, MF_STRING, ID_LIBRARY, L"Elegir carpeta adicional de subrutinas...");
    AppendMenuW(debug, MF_STRING, ID_CLEAR, L"Limpiar la salida de consola"); AppendMenuW(debug, MF_STRING, ID_PC, L"Ver dirección del PC en memoria");
    AppendMenuW(help, MF_STRING, ID_HELP, L"Cómo usar la interfaz\tF1");
    AppendMenuW(help, MF_STRING, ID_THEME, L"Cambiar tema claro / oscuro");
    AppendMenuW(bar, MF_POPUP, (UINT_PTR)file, L"Archivo"); AppendMenuW(bar, MF_POPUP, (UINT_PTR)examples, L"Ejemplos");
    AppendMenuW(bar, MF_POPUP, (UINT_PTR)debug, L"Herramientas"); AppendMenuW(bar, MF_POPUP, (UINT_PTR)help, L"Ayuda"); return bar;
}
static void command(unsigned id) {
    switch (id) {
        case ID_NEW:
            if (may_replace()) { app.path[0] = 0; set_source(L".ORIG x3000\r\n    AND R0,R0,#0\r\n    ADD R0,R0,#5\r\n    HALT\r\n.END\r\n", 0); gui_session_dispose(app.session); memory_origin(0x3000); app.shown_output = (size_t)-1; message(L"Nuevo programa. Escribí código, ensamblá y ejecutá."); refresh(); SetFocus(app.code); } break;
        case ID_OPEN: open_dialog(); break;
        case ID_SAVE: save_source(0); break; case ID_SAVE_AS: save_source(1); break;
        case ID_BUILD: assemble(); break; case ID_RUN: start_run(); break;
        case ID_PAUSE: stop_execution(); message(L"Ejecución pausada. F5 continúa; F10 avanza una instrucción."); refresh(); break;
        case ID_STEP:
            stop_execution(); if (ensure_built()) { gui_session_step(app.session); message(L"Paso realizado. También se pueden recorrer las instrucciones del sistema con F10."); refresh(); } break;
        case ID_RESET: {
            stop_execution(); if (!ensure_built()) break; AsmError error = {0};
            if (!gui_session_reset(app.session, &error)) report_asm_error(&error);
            else { app.shown_output = (size_t)-1; message(L"Reiniciado: registros, memoria, entrada, salida y contadores. Se conservan los breakpoints."); refresh(); } break;
        }
        case ID_EXPORT: stop_execution(); export_object(); break;
        case ID_GO: go_address(0); break; case ID_PC: go_address(1); break; case ID_BP: toggle_breakpoint(); break;
        case ID_SEND: send_input(1); break; case ID_SEND_RAW: send_input(0); break;
        case ID_INCLUDE_SYSTEM: refresh(); message(L"El selector cambia el conteo visible; no omite ni altera la ejecución del sistema."); break;
        case ID_THEME: apply_theme(!app.dark_mode); message(app.dark_mode ? L"Modo oscuro activado. El programa y los contadores se conservan." : L"Modo claro activado. El programa y los contadores se conservan."); break;
        case ID_CLEAR: gui_session_clear_output(app.session); app.shown_output = (size_t)-1; refresh(); break;
        case ID_LIBRARY: {
            stop_execution(); BROWSEINFOW browse = {0}; browse.hwndOwner = app.window; browse.lpszTitle = L"Elegí la carpeta donde están las bibliotecas .asm";
            browse.ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE; PIDLIST_ABSOLUTE selected = SHBrowseForFolderW(&browse);
            if (selected) { if (SHGetPathFromIDListW(selected, app.library)) { app.build_dirty = !app.object_mode; message(L"Carpeta de subrutinas seleccionada. Volvé a ensamblar para usarla."); refresh(); } CoTaskMemFree(selected); } break;
        }
        case ID_HELP:
            MessageBoxW(app.window,
                L"1. Abrí un .asm desde Archivo o elegí un ejemplo.\n2. Ensamblá con F7 y ejecutá con F5. F6 pausa; F10 da un paso.\n3. Mirá R0..R7 y buscá RESULTADO en memoria.\n4. Doble clic en una fila coloca un breakpoint; F5 continúa.\n5. Para ingresar datos, hacé clic en la consola y escribí, o usá Enviar línea.\n\nCONTADORES\nSiempre se registran programa, sistema y total. La casilla elige si el contador grande incluye el sistema. Cambiarla conserva los resultados y no vuelve a ejecutar.\nHALT y las llamadas TRAP del fuente cuentan como programa; sus rutinas cuentan como sistema. El límite de ejecución usa siempre el total. Reiniciar pone ambos contadores en cero.\n\nSUBRUTINAS\nSe buscan junto al fuente, en benchmark/modulos y en la carpeta adicional de Herramientas. Los objetos no conservan etiquetas.\n\nATAJOS\nCtrl+O abrir · Ctrl+S guardar · F2 reiniciar · F7 ensamblar\nF5 ejecutar · F6 pausar · F9 breakpoint · F10 paso.\n\nLa interfaz ejecuta el mismo núcleo C y la misma ISA3C del proyecto.",
                L"Guía rápida · ISA3C", MB_OK | MB_ICONINFORMATION); break;
        case ID_EXIT: SendMessageW(app.window, WM_CLOSE, 0, 0); break;
        default:
            if (id >= ID_EX_SUM && id <= ID_EX_CALC && may_replace()) {
                const wchar_t *paths[] = {L"ejemplos\\suma_grafica.asm", L"ejemplos\\prueba_suma.asm", L"ejemplos\\exp_isa3c.asm", L"ejemplos\\alu_integrada.asm", L"ejemplos\\eco.asm", L"benchmark\\calculadora.asm"};
                wchar_t path[PATH_CAP]; swprintf(path, PATH_CAP, L"%ls\\%ls", app.project, paths[id - ID_EX_SUM]); load_file(path);
            } break;
    }
}
static LRESULT CALLBACK window_proc(HWND window, UINT msg, WPARAM wp, LPARAM lp) {
    switch (msg) {
        case WM_CREATE: app.window = window; create_controls(); return 0;
        case WM_SIZE: if (wp != SIZE_MINIMIZED && app.code) layout(); return 0;
        case WM_GETMINMAXINFO: { MINMAXINFO *info = (MINMAXINFO *)lp; info->ptMinTrackSize.x = px(1120); info->ptMinTrackSize.y = px(720); return 0; }
        case WM_COMMAND:
            if (LOWORD(wp) == ID_CODE && (HIWORD(wp) == EN_CHANGE || HIWORD(wp) == EN_VSCROLL || HIWORD(wp) == EN_UPDATE)) {
                InvalidateRect(app.gutter, NULL, TRUE);
                if (HIWORD(wp) == EN_CHANGE && !app.suppress_change && !app.object_mode) {
                    app.disk_dirty = 1; app.build_dirty = 1; update_title(); SetWindowTextW(app.cpu_title, L"PROCESADOR · Cambios sin ensamblar"); message(L"Código modificado. F7 ensambla; F5 ensambla y ejecuta.");
                }
            } else if (HIWORD(wp) == BN_CLICKED || HIWORD(wp) == 1u) command(LOWORD(wp));
            return 0;
        case WM_TIMER: if (wp == 1u) execution_tick(); return 0;
        case WM_NOTIFY: {
            NMHDR *notice = (NMHDR *)lp;
            if (notice->idFrom == ID_MEMORY && notice->code == NM_DBLCLK) { toggle_breakpoint(); return 0; }
            if (notice->idFrom == ID_MEMORY && notice->code == LVN_ITEMCHANGED) { selection_info(); return 0; }
            if (notice->idFrom == ID_MEMORY && notice->code == NM_CUSTOMDRAW) {
                NMLVCUSTOMDRAW *draw = (NMLVCUSTOMDRAW *)lp;
                if (draw->nmcd.dwDrawStage == CDDS_PREPAINT) return CDRF_NOTIFYITEMDRAW;
                if (draw->nmcd.dwDrawStage == CDDS_ITEMPREPAINT) {
                    uint16_t address = (uint16_t)((unsigned)app.memory_base + 2u * (unsigned)draw->nmcd.dwItemSpec);
                    draw->clrTextBk = address == app.session->machine.pc ? palette.current_pc : ((draw->nmcd.dwItemSpec & 1u) ? palette.alternate : palette.surface);
                    draw->clrText = app.session->breakpoints[address] ? palette.breakpoint : INK; return CDRF_NEWFONT;
                }
            } break;
        }
        case WM_DRAWITEM: draw_control((DRAWITEMSTRUCT *)lp); return TRUE;
        case WM_CTLCOLORSTATIC: case WM_CTLCOLOREDIT: {
            HDC dc = (HDC)wp; HWND control = (HWND)lp; SetTextColor(dc, control == app.counter ? BLUE : control == app.status || control == app.selection || control == app.file_path || control == app.breakdown || control == app.memory_hint || control == app.input_hint ? MUTED : INK);
            if (control == app.status || control == app.selection || control == app.limit_title) { SetBkColor(dc, BG); return (LRESULT)app.background; }
            SetBkColor(dc, palette.surface); return (LRESULT)app.white;
        }
        case WM_PAINT: {
            PAINTSTRUCT paint; HDC dc = BeginPaint(window, &paint); RECT client; GetClientRect(window, &client); FillRect(dc, &client, app.background);
            RECT header = {0,0,client.right,px(64)}; FillRect(dc, &header, app.white);
            rounded(dc, app.left_card, palette.surface, LINE); rounded(dc, app.right_card, palette.surface, LINE); EndPaint(window, &paint); return 0;
        }
        case WM_CLOSE: if (may_replace()) DestroyWindow(window); return 0;
        case WM_DESTROY: KillTimer(window, 1); PostQuitMessage(0); return 0;
        default: break;
    }
    return DefWindowProcW(window, msg, wp, lp);
}
int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR cmdline, int show) {
    (void)previous; (void)cmdline;
    memset(&app, 0, sizeof app); app.instance = instance; app.dpi = 96; app.shown_output = (size_t)-1; set_palette(0);
    app.session = calloc(1, sizeof *app.session); if (!app.session) return 1;
    GetModuleFileNameW(NULL, app.project, PATH_CAP);
    wchar_t *slash = wcsrchr(app.project, L'\\'); if (slash) *slash = 0;
    slash = wcsrchr(app.project, L'\\'); if (slash && !_wcsicmp(slash + 1, L"build")) *slash = 0;
    SetCurrentDirectoryW(app.project);
    HDC screen = GetDC(NULL); app.dpi = GetDeviceCaps(screen, LOGPIXELSY); ReleaseDC(NULL, screen);
    app.ui_font = CreateFontW(-px(15), 0, 0, 0, FW_MEDIUM, FALSE, FALSE, FALSE, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, L"Segoe UI");
    app.small_font = CreateFontW(-px(13), 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, L"Segoe UI");
    app.heading_font = CreateFontW(-px(30), 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, L"Segoe UI");
    app.mono_font = CreateFontW(-px(17), 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, FIXED_PITCH, L"Consolas");
    app.register_font = CreateFontW(-px(15), 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, FIXED_PITCH, L"Consolas");
    app.count_font = CreateFontW(-px(21), 0, 0, 0, FW_SEMIBOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, L"Segoe UI");
    app.background = CreateSolidBrush(BG); app.white = CreateSolidBrush(RGB(255,255,255));
    INITCOMMONCONTROLSEX common = {sizeof common, ICC_LISTVIEW_CLASSES | ICC_STANDARD_CLASSES}; InitCommonControlsEx(&common); CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
    WNDCLASSW klass = {0}; klass.style = CS_HREDRAW | CS_VREDRAW; klass.lpfnWndProc = window_proc; klass.hInstance = instance;
    klass.hIcon = LoadIconW(NULL, IDI_APPLICATION); klass.hCursor = LoadCursorW(NULL, IDC_ARROW); klass.hbrBackground = app.background; klass.lpszClassName = L"ISA3C_GraphicEditor";
    if (!RegisterClassW(&klass)) return 1;
    RECT area; SystemParametersInfoW(SPI_GETWORKAREA, 0, &area, 0);
    int width = px(1420), height = px(920);
    if (width > area.right - area.left - px(20)) width = area.right - area.left - px(20);
    if (height > area.bottom - area.top - px(16)) height = area.bottom - area.top - px(16);
    HWND window = CreateWindowExW(0, klass.lpszClassName, L"ISA Grupo 6", WS_OVERLAPPEDWINDOW | WS_CLIPCHILDREN, area.left + (area.right - area.left - width) / 2, area.top + (area.bottom - area.top - height) / 2, width, height, NULL, create_menu(), instance, NULL);
    if (!window) return 1;
    wchar_t initial_path[PATH_CAP]; swprintf(initial_path, PATH_CAP, L"%ls\\ejemplos\\suma_grafica.asm", app.project);
    if (GetFileAttributesW(initial_path) != INVALID_FILE_ATTRIBUTES) load_file(initial_path);
    else { wchar_t *wide = to_wide(initial_source); if (wide) { set_source(wide, 0); free(wide); } }
    assemble(); layout(); ShowWindow(window, show); UpdateWindow(window);
    ACCEL shortcuts[] = {
        {FVIRTKEY | FCONTROL, 'N', ID_NEW}, {FVIRTKEY | FCONTROL, 'O', ID_OPEN}, {FVIRTKEY | FCONTROL, 'S', ID_SAVE},
        {FVIRTKEY | FCONTROL | FSHIFT, 'S', ID_SAVE_AS}, {FVIRTKEY, VK_F1, ID_HELP}, {FVIRTKEY, VK_F2, ID_RESET},
        {FVIRTKEY, VK_F5, ID_RUN}, {FVIRTKEY, VK_F6, ID_PAUSE}, {FVIRTKEY, VK_F7, ID_BUILD}, {FVIRTKEY, VK_F9, ID_BP}, {FVIRTKEY, VK_F10, ID_STEP}
        , {FVIRTKEY, VK_ESCAPE, ID_PAUSE}
    };
    HACCEL accelerator = CreateAcceleratorTableW(shortcuts, (int)(sizeof shortcuts / sizeof shortcuts[0]));
    MSG event;
    while (GetMessageW(&event, NULL, 0, 0) > 0) {
        if (!TranslateAcceleratorW(window, accelerator, &event) && !IsDialogMessageW(window, &event)) { TranslateMessage(&event); DispatchMessageW(&event); }
    }
    DestroyAcceleratorTable(accelerator); gui_session_dispose(app.session); free(app.session); lc3_os_free();
    DeleteObject(app.ui_font); DeleteObject(app.small_font); DeleteObject(app.heading_font); DeleteObject(app.mono_font); DeleteObject(app.register_font); DeleteObject(app.count_font);
    DeleteObject(app.background); DeleteObject(app.white); CoUninitialize(); return 0;
}
