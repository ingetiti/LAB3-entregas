#include "lc3.h"
#include "console.h"
#include <ctype.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define COMMAND_SIZE 8192u
typedef struct {
    char *source;
    char path[1024];
    int dirty, ready, object_mode, last_break;
    Lc3Image image;
    Lc3 machine;
    unsigned char breaks[LC3_WORDS];
} App;
static const char initial_source[] =
    "; Escribi tu programa LC-3 aqui.\n"
    ".ORIG x3000\n"
    "    LEA R0, MENSAJE\n"
    "    PUTS\n"
    "    HALT\n"
    "MENSAJE .STRINGZ \"Hola desde LC-3 en C!\\n\"\n"
    ".END\n";

static char *copy_text(const char *text) {
    size_t n = strlen(text) + 1u;
    char *copy = malloc(n);
    if (copy) memcpy(copy, text, n);
    return copy;
}
static void show_error(const AsmError *error) {
    if (error->line) printf("%s:%u: %s\n", *error->path ? error->path : "fuente", error->line, error->text);
    else printf("Error: %s\n", error->text);
}
static void output_character(void *context, unsigned char ch) {
    (void)context;
    putchar(ch);
}
static int reset_machine(App *app) {
    AsmError error;
    if (!lc3_init(&app->machine, &app->image, &error)) { show_error(&error); return 0; }
    app->machine.output = output_character;
    app->last_break = -1;
    return 1;
}
static int assemble(App *app, int verbose) {
    Lc3Image image;
    AsmError error;
    if (app->ready) return 1;
    if (!lc3_assemble_project(app->source, *app->path ? app->path : "nuevo.asm", NULL, 0, &image, &error)) { show_error(&error); return 0; }
    lc3_image_free(&app->image);
    app->image = image;
    app->object_mode = 0;
    memset(app->breaks, 0, sizeof app->breaks);
    if (!reset_machine(app)) return 0;
    app->ready = 1;
    if (verbose) printf("Ensamblado: %zu bytes desde x%04X, %zu etiquetas.\n", image.count, image.origin, image.symbol_count);
    return 1;
}
static char *read_source(const char *path) {
    FILE *file = fopen(path, "rb");
    char *source;
    long bytes;
    size_t received;
    if (!file) { printf("No se pudo abrir: %s\n", path); return NULL; }
    if (fseek(file, 0, SEEK_END) || (bytes = ftell(file)) < 0 || (unsigned long)bytes > LC3_MAX_SOURCE || fseek(file, 0, SEEK_SET)) {
        fclose(file); puts("Archivo no valido o mayor que 1 MiB."); return NULL;
    }
    source = malloc((size_t)bytes + 1u);
    if (!source) { fclose(file); puts("Sin memoria."); return NULL; }
    received = fread(source, 1, (size_t)bytes, file);
    if (received != (size_t)bytes || ferror(file) || memchr(source, 0, received)) {
        fclose(file); free(source); puts("Error de lectura o archivo con bytes NUL."); return NULL;
    }
    fclose(file);
    source[received] = 0;
    return source;
}
static int is_object(const char *path) {
    size_t n = strlen(path);
    return n >= 4 && path[n - 4] == '.' && tolower((unsigned char)path[n - 3]) == 'o' &&
        tolower((unsigned char)path[n - 2]) == 'b' && tolower((unsigned char)path[n - 1]) == 'j';
}
static int open_file(App *app, const char *path) {
    char *source;
    if (strlen(path) >= sizeof app->path) { puts("Ruta demasiado larga."); return 0; }
    if (is_object(path)) {
        Lc3Image image;
        AsmError error;
        if (!lc3_object_read(path, &image, &error)) { show_error(&error); return 0; }
        source = copy_text("");
        if (!source) { lc3_image_free(&image); return 0; }
        lc3_image_free(&app->image); app->image = image;
        free(app->source); app->source = source;
        app->path[0] = 0; app->dirty = 0; app->object_mode = 1;
        memset(app->breaks, 0, sizeof app->breaks);
        app->ready = reset_machine(app);
        return app->ready;
    }
    source = read_source(path);
    if (!source) return 0;
    free(app->source); app->source = source;
    strcpy(app->path, path);
    app->dirty = app->ready = app->object_mode = 0;
    return 1;
}
static int save_source(App *app, const char *specified_path) {
    char path[1024];
    FILE *file;
    int ok;
    if (app->object_mode) { puts("El objeto no contiene el texto fuente. Abri el editor para crear uno."); return 0; }
    if (specified_path && *specified_path) {
        if (strlen(specified_path) >= sizeof path) { puts("Ruta demasiado larga."); return 0; }
        strcpy(path, specified_path);
    } else {
        if (console_line("Guardar fuente en (Esc cancela): ", path, sizeof path) != 1 || !*path) return 0;
    }
    file = fopen(path, "wb");
    if (!file) { puts("No se pudo crear el archivo."); return 0; }
    ok = fwrite(app->source, 1, strlen(app->source), file) == strlen(app->source);
    if (fclose(file)) ok = 0;
    if (!ok) { puts("Error al guardar."); return 0; }
    strcpy(app->path, path); app->dirty = 0;
    printf("Guardado: %s\n", path);
    return 1;
}
static void registers(const App *app) {
    unsigned i;
    const Lc3 *m = &app->machine;
    puts("\n+---------------- REGISTROS ----------------+");
    for (i = 0; i < 8; ++i) {
        int decimal = m->r[i] & 0x8000u ? (int)m->r[i] - 65536 : (int)m->r[i];
        printf(" R%u: x%04X (%6d)%s", i, m->r[i], decimal, i % 2 ? "\n" : "   ");
    }
    printf(" PC: x%04X   IR: x%04X   PSR: x%04X\n", m->pc, m->ir, m->psr);
    printf(" CC: %c   Modo: %-10s   Instrucciones: %llu\n", m->psr & 4u ? 'N' : m->psr & 2u ? 'Z' : 'P',
           m->psr & 0x8000u ? "usuario" : "supervisor", (unsigned long long)m->instructions);
    printf(" Estado: %s   USP: x%04X   SSP: x%04X\n", m->mcr & 0x8000u ? "pausado" : "HALT", m->usp, m->ssp);
    printf(" Trafico: %llu bytes leidos, %llu bytes escritos\n",(unsigned long long)m->memory_read_bytes,(unsigned long long)m->memory_write_bytes);
    puts("+-------------------------------------------+");
}
static const char *label_at(const Lc3Image *image, uint16_t address) {
    size_t i;
    for (i = 0; i < image->symbol_count; ++i) if (image->symbols[i].address == address) return image->symbols[i].name;
    return "";
}
static void memory(const App *app, uint16_t start, unsigned count) {
    unsigned i;
    AsmError error;
    const Lc3Image *os = lc3_os_image(&error);
    puts("\n PC BP DIR    VALOR  INSTRUCCION                     ETIQUETA / LINEA");
    for (i = 0; i < count && (unsigned)start + 2u*i < LC3_WORDS; ++i) {
        uint16_t address = (uint16_t)(start + 2u*i), word = lc3_peek(&app->machine, address);
        const Lc3Image *image = &app->image;
        char instruction[96];
        unsigned line = 0;
        if ((size_t)address < image->origin || (size_t)address - image->origin >= image->count) image = os;
        if (image && image->lines && address >= image->origin && (size_t)address - image->origin < image->count) line = image->lines[address - image->origin];
        lc3_disassemble(address, word, instruction, sizeof instruction);
        printf(" %s %c  x%04X x%04X %-31s %s", app->machine.pc == address ? ">>" : "  ", app->breaks[address] ? '*' : ' ', address, word, instruction, image ? label_at(image, address) : "");
        if (line) printf(" / %s:%u", image == os ? "lc3os.asm" : "fuente", line);
        putchar('\n');
    }
}
/* 0 halted, 2 cycle limit, 3 user pause, 4 breakpoint. */
static int run_machine(App *app, uint64_t limit, int verbose) {
    uint64_t i;
    int skip_first = app->last_break == app->machine.pc;
    if (!assemble(app, verbose)) return 1;
    if (!(app->machine.mcr & 0x8000u)) { if (verbose) puts("El programa termino. Usa Reiniciar para ejecutarlo otra vez."); return 0; }
    if (verbose) puts("\n--- EJECUCION | Esc pausa | teclado para GETC/IN ---");
    app->last_break = -1;
    for (i = 0; i < limit; ++i) {
        int key;
        if (app->breaks[app->machine.pc] && !(i == 0 && skip_first)) {
            app->last_break = app->machine.pc;
            printf("\nPunto de interrupcion en x%04X.\n", app->machine.pc); fflush(stdout); return 4;
        }
        key = console_key();
        if (key == 27 || key == 3) { if (verbose) puts("\nEjecucion pausada con Esc."); fflush(stdout); return 3; }
        if (key >= 0 && key <= 255) {
            if (key == '\r') key = '\n';
            (void)lc3_key(&app->machine, (unsigned char)key);
        }
        (void)lc3_step(&app->machine);
        if (console_interactive() && app->machine.waiting_for_input && !app->machine.input_count && !(app->machine.kbsr & 0x8000u)) console_idle();
        if (!(app->machine.mcr & 0x8000u)) { fflush(stdout); return 0; }
        /* Flush output in programs which wait for input or run indefinitely. */
        if (!(i % 1024u)) fflush(stdout);
    }
    if (verbose) printf("\nPausa: limite de %llu instrucciones. Podes continuar.\n", (unsigned long long)limit);
    fflush(stdout);
    return 2;
}
static size_t source_lines(const char *source) {
    size_t count = 0;
    const char *p;
    for (p = source; *p; ++p) if (*p == '\n') ++count;
    if (p != source && p[-1] != '\n') ++count;
    return count;
}
static void list_source(const App *app) {
    const char *p = app->source;
    unsigned n = 1;
    while (*p) {
        const char *end = strchr(p, '\n');
        size_t length = end ? (size_t)(end - p) : strlen(p);
        printf("%4u | %.*s\n", n++, (int)length, p);
        p += length + (end ? 1u : 0u);
    }
}
/* Rebuild the source only after validating the edit, retaining it on errors. */
static int edit_line(App *app, size_t line, const char *text, int mode) {
    size_t count = source_lines(app->source), before, removed, added, total;
    const char *start = app->source, *end;
    char *next;
    size_t i;
    if (line < 1 || line > count + (mode == 1 ? 1u : 0u)) { puts("Numero de linea fuera de rango."); return 0; }
    for (i = 1; i < line && *start; ++i) {
        const char *newline = strchr(start, '\n');
        start = newline ? newline + 1 : start + strlen(start);
    }
    before = (size_t)(start - app->source);
    end = mode == 1 ? start : strchr(start, '\n');
    if (!end) end = start + strlen(start);
    else if (mode != 1) ++end;
    removed = (size_t)(end - start);
    added = mode == -1 ? 0 : strlen(text) + 1u;
    /* Inserting after a final line without a newline needs one separator. */
    i = before && app->source[before - 1u] != '\n' && added ? 1u : 0u;
    total = strlen(app->source) - removed + added + i;
    if (total > LC3_MAX_SOURCE) { puts("El editor admite hasta 1 MiB."); return 0; }
    next = malloc(total + 1u);
    if (!next) { puts("Sin memoria."); return 0; }
    memcpy(next, app->source, before);
    if (i) next[before++] = '\n';
    if (added) { memcpy(next + before, text, added - 1u); next[before + added - 1u] = '\n'; }
    strcpy(next + before + added, end);
    free(app->source); app->source = next;
    app->dirty = 1; app->ready = 0; app->object_mode = 0;
    return 1;
}
static void editor_help(void) {
    puts("\nTexto normal + Enter: agregar una linea al final.");
    puts(":list                 mostrar el programa con numeros de linea");
    puts(":set N texto          reemplazar la linea N");
    puts(":insert N texto       insertar antes de N");
    puts(":delete N             borrar la linea N");
    puts(":save [ruta]          guardar el fuente; usa la ruta actual si existe");
    puts(":assemble             ensamblar y cargar en la maquina");
    puts(":run                  ensamblar si hace falta y ejecutar");
    puts(":help                 mostrar esta ayuda");
    puts(":quit o Esc           volver al menu; el texto queda en memoria");
}
static void editor(App *app) {
    char command[COMMAND_SIZE], prompt[64];
    if (app->object_mode) {
        char *source = copy_text(initial_source);
        if (!source) return;
        free(app->source); app->source = source;
        app->dirty = 1; app->ready = app->object_mode = 0;
        puts("Se creo un fuente nuevo para editar.");
    }
    puts("\n+----------- EDITOR LC-3 | Esc: menu -----------+");
    editor_help(); list_source(app);
    for (;;) {
        char *argument, *end;
        unsigned long number;
        int result;
        snprintf(prompt, sizeof prompt, "%4zu + ", source_lines(app->source) + 1u);
        result = console_line(prompt, command, sizeof command);
        if (result == 0 || result == -1) break;
        if (result == -2) { puts("Linea demasiado larga."); continue; }
        if (command[0] != ':') { (void)edit_line(app, source_lines(app->source) + 1u, command, 1); continue; }
        argument = strchr(command, ' ');
        if (argument) { *argument++ = 0; while (*argument == ' ') ++argument; }
        if (!strcmp(command, ":quit")) break;
        if (!strcmp(command, ":help")) editor_help();
        else if (!strcmp(command, ":list")) list_source(app);
        else if (!strcmp(command, ":assemble")) (void)assemble(app, 1);
        else if (!strcmp(command, ":run")) { if (run_machine(app, 1000000u, 1) == 3) break; }
        else if (!strcmp(command, ":save")) (void)save_source(app, argument && *argument ? argument : app->path);
        else if (!strcmp(command, ":set") || !strcmp(command, ":insert") || !strcmp(command, ":delete")) {
            if (!argument || !isdigit((unsigned char)*argument)) { puts("Falta el numero de linea."); continue; }
            errno = 0; number = strtoul(argument, &end, 10);
            if (errno || !number || (*end && *end != ' ') || number > 65536u) { puts("Numero de linea no valido."); continue; }
            if (*end) ++end;
            if (!strcmp(command, ":delete") && *end) { puts(":delete solo admite el numero de linea."); continue; }
            (void)edit_line(app, (size_t)number, end, !strcmp(command, ":delete") ? -1 : !strcmp(command, ":insert") ? 1 : 0);
        } else puts("Comando desconocido. Usa :help.");
    }
    if (app->dirty) puts("Fuente conservado en memoria. Usa Guardar para conservarlo en disco.");
}
static int address_argument(const App *app, const char *text, uint16_t *address) {
    long value;
    if (lc3_number(text, &value) && value >= 0 && value <= 65535) { *address = (uint16_t)value; return 1; }
    if (lc3_symbol(&app->image, text, address)) return 1;
    puts("Usa una direccion x3000, decimal #12288 o una etiqueta del programa.");
    return 0;
}
static void debugger(App *app) {
    char command[256];
    if (!assemble(app, 1)) return;
    puts("\n+----------- DEPURADOR LC-3 | Esc: menu -----------+");
    puts("s: paso | c: continuar | r: registros | m DIR: memoria");
    puts("b DIR: activar/desactivar breakpoint | b: listar | reset: reiniciar | q: menu");
    puts("Los pasos incluyen instrucciones del sistema operativo.");
    registers(app); memory(app, app->machine.pc, 8);
    for (;;) {
        char *argument;
        uint16_t address;
        int result = console_line("debug> ", command, sizeof command);
        if (result == 0 || result == -1) break;
        if (result != 1) continue;
        argument = strchr(command, ' ');
        if (argument) { *argument++ = 0; while (*argument == ' ') ++argument; }
        if (!strcmp(command, "q")) break;
        if (!strcmp(command, "s") || !*command) {
            (void)lc3_step(&app->machine);
        if (console_interactive() && app->machine.waiting_for_input && !app->machine.input_count && !(app->machine.kbsr & 0x8000u)) console_idle();
            app->last_break = -1;
            if (app->machine.exception) printf("Excepcion x%03X: se ingreso al manejador del SO.\n", app->machine.exception);
            registers(app); memory(app, app->machine.pc, 5);
        } else if (!strcmp(command, "c")) {
            if (run_machine(app, 1000000u, 1) == 3) break;
            registers(app);
        }
        else if (!strcmp(command, "r")) registers(app);
        else if (!strcmp(command, "reset")) { (void)reset_machine(app); registers(app); }
        else if (!strcmp(command, "m")) {
            address = app->machine.pc;
            if (!argument || address_argument(app, argument, &address)) memory(app, address, 16);
        } else if (!strcmp(command, "b")) {
            if (argument && *argument) {
                if (address_argument(app, argument, &address)) {
                    app->breaks[address] ^= 1u;
                    printf("Breakpoint x%04X: %s\n", address, app->breaks[address] ? "activo" : "eliminado");
                }
            } else {
                unsigned i, count = 0;
                for (i = 0; i < LC3_WORDS; ++i) if (app->breaks[i]) { printf("  * x%04X %s\n", i, label_at(&app->image, (uint16_t)i)); ++count; }
                if (!count) puts("Sin puntos de interrupcion.");
            }
        } else puts("Comandos: s, c, r, m DIR, b DIR, b, reset, q. Esc vuelve al menu.");
    }
}
static void help(void) {
    puts("\nISA 3c | Registros 16 bits, opcodes 5 bits, memoria por bytes");
    puts("1. Editar el ejemplo o abrir ejemplos/hola.asm, suma.asm, eco.asm o subrutina.asm.");
    puts("2. Ensamblar, ejecutar o entrar al depurador. Esc vuelve o pausa.");
    puts("3. Guardar el .asm antes de cerrar. El editor conserva cambios al volver al menu.");
    puts("El editor es por lineas; :set y :insert permiten modificar texto existente.");
    puts("Numeros: #decimal, xHEX, bBIN. Etiquetas sin distinguir mayusculas.");
    puts("ALU nueva: SUB, MUL, MULU, DIVU, CLZ, MOV, SHL, SHR, SAR/ASR.");
    puts("Directivas: .ORIG, .END, .FILL, .BLKW, .STRINGZ, .BYTE, .BLKB, .ALIGN, .EXTERNAL.");
    puts("CPU basada en el codigo recibido: TRAP con pila de supervisor, retorno RTI.");
    puts("LEA conserva los flags. HALT ejecuta el SO y detiene MCR.");
    puts("Los .obj contienen dos bytes de origen y luego bytes de memoria; no guardan etiquetas.");
    puts("Enlaza .EXTERNAL archivo-simbolo. Objetos: origen de dos bytes y memoria big-endian.");
}
static int discard_check(App *app) {
    char answer[16];
    if (!app->dirty) return 1;
    puts("Hay cambios del fuente sin guardar.");
    if (console_line("g: guardar | d: descartar | Esc: cancelar > ", answer, sizeof answer) != 1) return 0;
    if (!strcmp(answer, "d")) return 1;
    if (!strcmp(answer, "g")) return save_source(app, app->path);
    return 0;
}
static void menu(App *app) {
    char choice[32], path[1024];
    for (;;) {
        int result;
        puts("\n+=============================================+");
        puts("|           ISA3C INTEGRADA / C v1.1          |");
        puts("+=============================================+");
        printf(" Archivo: %s%s\n", app->object_mode ? "objeto cargado" : *app->path ? app->path : "nuevo.asm", app->dirty ? " [sin guardar]" : "");
        printf(" Programa: %s\n", app->ready ? "cargado" : "pendiente de ensamblar");
        puts(" 1  Programar / editar fuente");
        puts(" 2  Abrir archivo .asm / .obj");
        puts(" 3  Guardar fuente .asm");
        puts(" 4  Ensamblar y cargar");
        puts(" 5  Ejecutar / continuar");
        puts(" 6  Depurador: registros, memoria y breakpoints");
        puts(" 7  Reiniciar programa");
        puts(" 8  Exportar programa .obj");
        puts(" 9  Ayuda y ejemplos");
        puts(" 0  Salir");
        result = console_line("Opcion > ", choice, sizeof choice);
        if (!result) break;
        if (result == -2) continue;
        if (result == -1 || !strcmp(choice, "0")) { if (discard_check(app)) break; continue; }
        if (!strcmp(choice, "1")) editor(app);
        else if (!strcmp(choice, "2")) {
            if (console_line("Ruta del archivo (Esc cancela): ", path, sizeof path) == 1 && *path && discard_check(app)) (void)open_file(app, path);
        } else if (!strcmp(choice, "3")) { (void)save_source(app, NULL); console_pause(); }
        else if (!strcmp(choice, "4")) { (void)assemble(app, 1); console_pause(); }
        else if (!strcmp(choice, "5")) {
            if (run_machine(app, 1000000u, 1) != 3) console_pause();
        }
        else if (!strcmp(choice, "6")) debugger(app);
        else if (!strcmp(choice, "7")) {
            if (assemble(app, 1) && reset_machine(app)) puts("Programa reiniciado desde su imagen original.");
            console_pause();
        } else if (!strcmp(choice, "8")) {
            AsmError error;
            if (assemble(app, 1) && console_line("Archivo .obj de salida (Esc cancela): ", path, sizeof path) == 1 && *path) {
                if (lc3_object_write(path, &app->image, &error)) puts("Objeto exportado."); else show_error(&error);
            }
            console_pause();
        } else if (!strcmp(choice, "9")) { help(); console_pause(); }
        else puts("Opcion no valida.");
    }
}
static void usage(void) {
    puts("Uso: lc3                                  menu de consola");
    puts("     lc3 --run archivo.asm|archivo.obj [--max-instructions N]");
    puts("     lc3 --assemble archivo.asm -o salida.obj");
    puts("     lc3 --help");
}
int main(int argc, char **argv) {
    App *app = calloc(1, sizeof *app);
    int result = 0;
    if (!app) { fputs("Sin memoria.\n", stderr); return 1; }
    app->source = copy_text(initial_source);
    if (!app->source) { free(app); return 1; }
    app->dirty = 1; app->last_break = -1;
    console_init(); atexit(console_shutdown);
    if (argc == 1) menu(app);
    else if (argc == 2 && !strcmp(argv[1], "--help")) { usage(); help(); }
    else if ((argc == 3 || argc == 5) && !strcmp(argv[1], "--run")) {
        uint64_t limit = 5000000u;
        if (argc == 5) {
            char *end;
            unsigned long long parsed;
            errno = 0; parsed = strtoull(argv[4], &end, 10);
            if ((strcmp(argv[3], "--max-cycles") && strcmp(argv[3], "--max-instructions")) || !isdigit((unsigned char)argv[4][0]) || errno || *end || !parsed) { usage(); result = 1; goto done; }
            limit = (uint64_t)parsed;
        }
        if (!open_file(app, argv[2]) || !assemble(app, 0)) { result = 1; goto done; }
        result = run_machine(app, limit, 0);
        if (result == 2) fprintf(stderr, "\nLimite de instrucciones alcanzado (%llu).\n", (unsigned long long)limit);
    } else if (argc == 5 && !strcmp(argv[1], "--assemble") && !strcmp(argv[3], "-o")) {
        AsmError error;
        if (is_object(argv[2]) || !open_file(app, argv[2]) || !assemble(app, 1)) result = 1;
        else if (!lc3_object_write(argv[4], &app->image, &error)) { show_error(&error); result = 1; }
        else printf("Objeto guardado: %s\n", argv[4]);
    } else { usage(); result = 1; }
done:
    if (argc>=3 && !strcmp(argv[1],"--run") && app->ready) {
        printf("\nMETRICAS instrucciones=%llu interrupciones=%llu programa_bytes=%zu accedidos_bytes=%zu escritos_bytes=%zu excepcion=%u\n",
            (unsigned long long)app->machine.instructions,(unsigned long long)app->machine.interrupts,
            app->machine.program_bytes,app->machine.accessed_bytes,app->machine.written_bytes,app->machine.last_exception);
        if (!result && app->machine.last_exception) result=4;
    }
    lc3_image_free(&app->image); lc3_os_free(); free(app->source); free(app);
    return result;
}
