#ifndef UNICODE
#define UNICODE
#endif
#include <windows.h>
#include <commctrl.h>
#include <stdint.h>
#include <stdlib.h>
#include <wchar.h>
#include "gui_editor.h"

wchar_t *gui_editor_crlf(const wchar_t *text) {
    if (!text) return NULL;
    size_t length = wcslen(text), dst = 0;
    if (length > (SIZE_MAX / sizeof(wchar_t) - 1u) / 2u) return NULL;
    wchar_t *out = malloc((length * 2u + 1u) * sizeof *out);
    if (!out) return NULL;
    for (size_t i = 0; i < length; ++i) {
        if (text[i] == L'\r' || text[i] == L'\n') {
            if (text[i] == L'\r' && text[i + 1u] == L'\n') ++i;
            out[dst++] = L'\r'; out[dst++] = L'\n';
        } else out[dst++] = text[i];
    }
    out[dst] = 0;
    return out;
}

int gui_editor_insert(HWND editor, const wchar_t *text) {
    if (!editor || (GetWindowLongPtrW(editor, GWL_STYLE) & ES_READONLY)) return 0;
    wchar_t *normalized = gui_editor_crlf(text);
    if (!normalized) return 0;
    DWORD start = 0, end = 0;
    SendMessageW(editor, EM_GETSEL, (WPARAM)&start, (LPARAM)&end);
    size_t length = (size_t)GetWindowTextLengthW(editor);
    size_t limit = (size_t)SendMessageW(editor, EM_GETLIMITTEXT, 0, 0);
    size_t added = wcslen(normalized);
    size_t retained = length - (size_t)(end - start);
    if (retained > limit || added > limit - retained) { free(normalized); return 0; }
    /* The native control keeps selection, caret, EN_CHANGE and undo semantics. */
    SendMessageW(editor, EM_REPLACESEL, TRUE, (LPARAM)normalized);
    free(normalized);
    SendMessageW(editor, EM_SCROLLCARET, 0, 0);
    return 1;
}

static int paste_text(HWND editor) {
    if (GetWindowLongPtrW(editor, GWL_STYLE) & ES_READONLY) return 1;
    if (!OpenClipboard(editor)) return 0;
    HANDLE data = GetClipboardData(CF_UNICODETEXT);
    int ok = 0;
    if (data) {
        SIZE_T capacity = GlobalSize(data) / sizeof(wchar_t);
        const wchar_t *text = GlobalLock(data);
        if (text) {
            /* Clipboard contents are external data: require a bounded terminator. */
            size_t n = 0;
            while (n < capacity && text[n]) ++n;
            if (n < capacity) ok = gui_editor_insert(editor, text);
            GlobalUnlock(data);
        }
    }
    CloseClipboard();
    return ok;
}

static LRESULT CALLBACK editor_proc(HWND editor, UINT msg, WPARAM wp, LPARAM lp,
                                    UINT_PTR subclass, DWORD_PTR data) {
    (void)data;
    if (msg == WM_PASTE) {
        if (!paste_text(editor)) MessageBeep(MB_ICONWARNING);
        return 0;
    }
    if (msg == WM_NCDESTROY) RemoveWindowSubclass(editor, editor_proc, subclass);
    return DefSubclassProc(editor, msg, wp, lp);
}

int gui_editor_attach(HWND editor) {
    return SetWindowSubclass(editor, editor_proc, 1, 0) != FALSE;
}
