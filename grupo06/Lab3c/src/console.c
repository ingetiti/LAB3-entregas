#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L
#endif
#include "console.h"
#include <stdio.h>
#include <string.h>
#ifdef _WIN32
#include <conio.h>
#include <io.h>
#include <windows.h>
static UINT previous_output_cp;
#else
#include <sys/select.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>
static struct termios previous_terminal;
static int terminal_changed;
#endif
static int interactive;
void console_init(void) {
    setvbuf(stdin, NULL, _IONBF, 0);
#ifdef _WIN32
    interactive = _isatty(_fileno(stdin)) && _isatty(_fileno(stdout));
    previous_output_cp = GetConsoleOutputCP();
    if (interactive) SetConsoleOutputCP(CP_UTF8);
#else
    interactive = isatty(STDIN_FILENO) && isatty(STDOUT_FILENO);
    if (interactive && tcgetattr(STDIN_FILENO, &previous_terminal) == 0) {
        struct termios raw = previous_terminal;
        raw.c_lflag &= (tcflag_t)~(ICANON | ECHO | ISIG);
        raw.c_iflag &= (tcflag_t)~(IXON | ICRNL);
        raw.c_cc[VMIN] = 1; raw.c_cc[VTIME] = 0;
        terminal_changed = tcsetattr(STDIN_FILENO, TCSANOW, &raw) == 0;
    }
#endif
}
void console_shutdown(void) {
#ifdef _WIN32
    if (interactive && previous_output_cp) SetConsoleOutputCP(previous_output_cp);
#else
    if (terminal_changed) tcsetattr(STDIN_FILENO, TCSANOW, &previous_terminal);
#endif
}
int console_interactive(void) { return interactive; }
static int blocking_key(void) {
#ifdef _WIN32
    if (_isatty(_fileno(stdin))) {
        int key = _getch();
        if (key == 0 || key == 224) { (void)_getch(); return -2; }
        return key;
    }
#endif
    return getchar();
}
int console_key(void) {
#ifdef _WIN32
    if (_isatty(_fileno(stdin))) return _kbhit() ? blocking_key() : -1;
    {
        HANDLE input = GetStdHandle(STD_INPUT_HANDLE);
        if (GetFileType(input) == FILE_TYPE_PIPE) {
            DWORD available = 0;
            if (!PeekNamedPipe(input, NULL, 0, NULL, &available, NULL) || !available) return -1;
        }
        return getchar();
    }
#else
    fd_set read_set;
    struct timeval timeout = {0, 0};
    FD_ZERO(&read_set); FD_SET(STDIN_FILENO, &read_set);
    return select(STDIN_FILENO + 1, &read_set, NULL, NULL, &timeout) > 0 ? getchar() : -1;
#endif
}
int console_line(const char *prompt, char *text, size_t capacity) {
    size_t length = 0;
    if (capacity < 2) return -2;
    fputs(prompt, stdout); fflush(stdout);
    text[0] = 0;
    if (!interactive) {
        char *newline;
        if (!fgets(text, (int)capacity, stdin)) return 0;
        newline = strchr(text, '\n');
        if (!newline && !feof(stdin)) {
            int key;
            while ((key = getchar()) != '\n' && key != EOF) { }
            text[0] = 0; return -2;
        }
        text[strcspn(text, "\r\n")] = 0;
        return strchr(text, 27) ? -1 : 1;
    }
    for (;;) {
        int key = blocking_key();
        if (key == EOF || key == 4 || key == 26) { putchar('\n'); return 0; }
        if (key == 27 || key == 3) { text[0] = 0; putchar('\n'); return -1; }
        if (key == '\r' || key == '\n') { text[length] = 0; putchar('\n'); return 1; }
        if (key == 8 || key == 127) {
            if (length) { --length; fputs("\b \b", stdout); fflush(stdout); }
        } else if (key == '\t' || (key >= 32 && key <= 255)) {
            if (length + 1 < capacity) {
                text[length++] = key == '\t' ? ' ' : (char)key;
                putchar((unsigned char)text[length - 1u]); fflush(stdout);
            } else { putchar('\a'); fflush(stdout); }
        }
    }
}
void console_pause(void) {
    char line[8];
    if (interactive) (void)console_line("Enter para continuar (Esc para volver)... ", line, sizeof line);
}

void console_idle(void) {
#ifdef _WIN32
    Sleep(1);
#else
    struct timespec delay={0,1000000};
    nanosleep(&delay,NULL);
#endif
}
