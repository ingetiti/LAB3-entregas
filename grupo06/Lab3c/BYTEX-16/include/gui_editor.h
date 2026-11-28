#ifndef ISA_GUI_EDITOR_H
#define ISA_GUI_EDITOR_H
#include <windows.h>

/* Normalize LF, CRLF and CR to the line endings of a native multiline EDIT. */
wchar_t *gui_editor_crlf(const wchar_t *text);
/* One undoable replacement of the selection. Failure leaves the text intact. */
int gui_editor_insert(HWND editor, const wchar_t *text);
int gui_editor_attach(HWND editor);
#endif
