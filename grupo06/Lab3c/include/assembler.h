#ifndef LC3_ASSEMBLER_H
#define LC3_ASSEMBLER_H
#include <stddef.h>
#include <stdint.h>

#define LC3_MAX_SOURCE (1024u * 1024u)
#define LC3_MAX_SYMBOLS 4096u
#define LC3_LABEL_SIZE 128u
typedef struct { char name[LC3_LABEL_SIZE]; uint16_t address; } Lc3Symbol;
typedef struct {
    uint16_t origin;
    size_t count;
    uint8_t *bytes;
    unsigned *lines;
    Lc3Symbol *symbols;
    size_t symbol_count;
} Lc3Image;
typedef struct { unsigned line; char text[240]; char path[1024]; } AsmError;

/* On failure the output image is empty; dispose images before reusing them. */
int lc3_assemble(const char *source, Lc3Image *out, AsmError *error);
int lc3_assemble_file(const char *path, const char *const *include_dirs,
                      size_t include_count, Lc3Image *out, AsmError *error);
int lc3_assemble_project(const char *source, const char *path,
                         const char *const *include_dirs, size_t include_count,
                         Lc3Image *out, AsmError *error);
void lc3_image_free(Lc3Image *image);
int lc3_symbol(const Lc3Image *image, const char *name, uint16_t *address);
int lc3_number(const char *text, long *value);
int lc3_object_write(const char *path, const Lc3Image *image, AsmError *error);
int lc3_object_read(const char *path, Lc3Image *image, AsmError *error);
#endif
