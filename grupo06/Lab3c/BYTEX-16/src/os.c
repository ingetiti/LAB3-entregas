#include "lc3.h"
#include <os_image.h>

const Lc3Image *lc3_os_image(AsmError *error) {
    static Lc3Image image;
    (void)error;
    image.origin=lc3_os_origin;
    image.count=sizeof lc3_os_bytes;
    image.bytes=(uint8_t *)(const void *)lc3_os_bytes;
    return &image;
}
void lc3_os_free(void) { }
