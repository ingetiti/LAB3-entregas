#ifndef UNICODE
#define UNICODE
#endif
#include <windows.h>
#include <commctrl.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>
#include "gui_editor.h"

static unsigned checks, failures;
#define CHECK(test) do { ++checks; if (!(test)) { ++failures; fprintf(stderr, "Fallo linea %u: %s\n", (unsigned)__LINE__, #test); } } while (0)
static void text_is(HWND edit, const wchar_t *expected, unsigned lines) {
    int length = GetWindowTextLengthW(edit);
    wchar_t *actual = calloc((size_t)length + 1u, sizeof *actual);
    if (!actual) { CHECK(actual != NULL); return; }
    GetWindowTextW(edit, actual, length + 1);
    CHECK(wcscmp(actual, expected) == 0);
    CHECK(SendMessageW(edit, EM_GETLINECOUNT, 0, 0) == (LRESULT)lines);
    free(actual);
}

int main(void) {
    INITCOMMONCONTROLSEX common = {sizeof common, ICC_STANDARD_CLASSES};
    InitCommonControlsEx(&common);
    HWND parent = CreateWindowExW(0, L"STATIC", L"", WS_OVERLAPPED, 0, 0, 800, 600, NULL, NULL, GetModuleHandleW(NULL), NULL);
    HWND edit = CreateWindowExW(0, L"EDIT", L"", WS_CHILD | ES_MULTILINE | ES_AUTOHSCROLL | ES_AUTOVSCROLL,
                                 0, 0, 700, 500, parent, NULL, GetModuleHandleW(NULL), NULL);
    if (!parent || !edit) { fputs("No se pudo crear el control de prueba.\n", stderr); return 1; }
    CHECK(gui_editor_attach(edit));
    SendMessageW(edit, EM_SETLIMITTEXT, 1024u * 1024u, 0);

    const wchar_t *pasted[] = {L".ORIG x3000\nADD R0,R0,#1\nHALT\n.END\n",
        L".ORIG x3000\r\nADD R0,R0,#1\r\nHALT\r\n.END\r\n",
        L".ORIG x3000\rADD R0,R0,#1\rHALT\r.END\r"};
    for (size_t i = 0; i < sizeof pasted / sizeof pasted[0]; ++i) {
        SetWindowTextW(edit, L""); SendMessageW(edit, EM_EMPTYUNDOBUFFER, 0, 0);
        CHECK(gui_editor_insert(edit, pasted[i]));
        text_is(edit, L".ORIG x3000\r\nADD R0,R0,#1\r\nHALT\r\n.END\r\n", 5);
        CHECK(SendMessageW(edit, EM_CANUNDO, 0, 0));
        CHECK(SendMessageW(edit, EM_UNDO, 0, 0)); text_is(edit, L"", 1);
    }
    SetWindowTextW(edit, L"antes[reemplazar]despues");
    SendMessageW(edit, EM_SETSEL, 5, 17);
    SendMessageW(edit, EM_EMPTYUNDOBUFFER, 0, 0);
    CHECK(gui_editor_insert(edit, L"\t; año\n\nADD R0,R0,#1\rHALT\r\n"));
    text_is(edit, L"antes\t; año\r\n\r\nADD R0,R0,#1\r\nHALT\r\ndespues", 5);
    CHECK(SendMessageW(edit, EM_UNDO, 0, 0));
    text_is(edit, L"antes[reemplazar]despues", 1);

    SetWindowTextW(edit, L"123456"); SendMessageW(edit, EM_SETLIMITTEXT, 8, 0);
    SendMessageW(edit, EM_SETSEL, 3, 3);
    CHECK(!gui_editor_insert(edit, L"X\nY")); text_is(edit, L"123456", 1);
    DWORD start = 0, end = 0; SendMessageW(edit, EM_GETSEL, (WPARAM)&start, (LPARAM)&end);
    CHECK(start == 3 && end == 3);
    SendMessageW(edit, EM_SETSEL, 0, 6);
    CHECK(gui_editor_insert(edit, L"A\nB")); text_is(edit, L"A\r\nB", 2);
    SendMessageW(edit, EM_SETREADONLY, TRUE, 0);
    CHECK(!gui_editor_insert(edit, L"HALT")); text_is(edit, L"A\r\nB", 2);
    SendMessageW(edit, EM_SETREADONLY, FALSE, 0);
    CHECK(!gui_editor_insert(edit, NULL)); text_is(edit, L"A\r\nB", 2);

    SendMessageW(edit, EM_SETLIMITTEXT, 1024u * 1024u, 0);
    SetWindowTextW(edit, L"");
    wchar_t *large = calloc(10001u, sizeof *large);
    if (!large) { CHECK(large != NULL); }
    else {
        for (size_t i = 0; i < 10000u; i += 2u) { large[i] = L'A'; large[i + 1u] = L'\n'; }
        CHECK(gui_editor_insert(edit, large));
        CHECK(GetWindowTextLengthW(edit) == 15000);
        CHECK(SendMessageW(edit, EM_GETLINECOUNT, 0, 0) == 5001);
        free(large);
    }
    DestroyWindow(parent);
    printf("Editor Windows: %u comprobaciones, %u fallos.\n", checks, failures);
    return failures ? 1 : 0;
}
