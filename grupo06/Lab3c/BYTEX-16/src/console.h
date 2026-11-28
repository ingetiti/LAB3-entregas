#ifndef LC3_CONSOLE_H
#define LC3_CONSOLE_H
#include <stddef.h>
void console_init(void);
void console_shutdown(void);
int console_interactive(void);
int console_key(void); /* nonblocking, -1 when no key */
int console_line(const char *prompt, char *text, size_t capacity); /* 1 ok, 0 EOF, -1 Esc, -2 too long */
void console_pause(void);
void console_idle(void);
#endif
