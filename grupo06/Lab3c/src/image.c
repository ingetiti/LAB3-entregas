#include "assembler.h"
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int error_text(AsmError *error,const char *text) {
    if(error) { memset(error,0,sizeof *error); snprintf(error->text,sizeof error->text,"%s",text); }
    return 0;
}
static int equal(const char *a,const char *b) {
    while(*a&&*b) if(toupper((unsigned char)*a++)!=toupper((unsigned char)*b++)) return 0;
    return *a==*b;
}
void lc3_image_free(Lc3Image *image) {
    free(image->bytes);free(image->lines);free(image->symbols);memset(image,0,sizeof *image);
}
int lc3_symbol(const Lc3Image *image,const char *name,uint16_t *address) {
    for(size_t i=0;i<image->symbol_count;++i) if(equal(name,image->symbols[i].name)) {
        *address=image->symbols[i].address;return 1;
    }
    return 0;
}
int lc3_object_write(const char *path,const Lc3Image *image,AsmError *error) {
    FILE *f;
    int ok;
    if(!image->bytes||!image->count||(size_t)image->origin+image->count>65536u) return error_text(error,"Imagen no valida.");
    f=fopen(path,"wb");if(!f) return error_text(error,"No se pudo crear objeto.");
    ok=fputc(image->origin>>8u,f)!=EOF&&fputc(image->origin&255u,f)!=EOF;
    if(ok) ok=fwrite(image->bytes,1,image->count,f)==image->count;
    if(fclose(f)) ok=0;
    return ok?1:error_text(error,"Error al escribir objeto.");
}
int lc3_object_read(const char *path,Lc3Image *image,AsmError *error) {
    FILE *f;
    long length;
    int hi,lo,ok;
    memset(image,0,sizeof *image);
    f=fopen(path,"rb");if(!f) return error_text(error,"No se pudo abrir objeto.");
    if(fseek(f,0,SEEK_END)||(length=ftell(f))<3||length>65538||fseek(f,0,SEEK_SET)) {
        fclose(f);return error_text(error,"Objeto invalido: origen big-endian de dos bytes seguido de memoria.");
    }
    hi=fgetc(f);lo=fgetc(f);image->origin=(uint16_t)((unsigned)hi<<8u|(unsigned)lo);
    image->count=(size_t)length-2u;
    if((size_t)image->origin+image->count>65536u) {fclose(f);memset(image,0,sizeof *image);return error_text(error,"Objeto fuera de memoria.");}
    image->bytes=malloc(image->count);
    if(!image->bytes) {fclose(f);memset(image,0,sizeof *image);return error_text(error,"Sin memoria.");}
    ok=fread(image->bytes,1,image->count,f)==image->count&&!ferror(f);
    if(fclose(f)) ok=0;
    if(!ok) {lc3_image_free(image);return error_text(error,"Objeto truncado.");}
    return 1;
}
