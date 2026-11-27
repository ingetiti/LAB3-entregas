#include "lc3.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Exportar un vector para comparar binariamente el nucleo Q7.8 y su envoltorio.
 * Cada caso guarda R0 y R1: resultado completo del formato de salida. */
static int call(Lc3 *m,const Lc3Image *im,uint16_t entry,uint16_t a,uint16_t b,FILE *out) {
    AsmError e;if(!lc3_init(m,im,&e))return 0;
    m->pc=entry;m->r[0]=a;m->r[1]=b;m->r[2]=0x2222;m->r[3]=0x3333;m->r[4]=0x4444;m->r[5]=0x5555;m->r[7]=im->origin;
    while(m->pc!=im->origin&&(m->mcr&0x8000u)&&m->instructions<100000)lc3_step(m);
    if(m->pc!=im->origin||m->last_exception||m->r[2]!=0x2222||m->r[3]!=0x3333||m->r[4]!=0x4444||m->r[5]!=0x5555||m->r[6]!=0xFE00||m->r[7]!=im->origin)return 0;
    for(unsigned i=0;i<2;++i){if(fputc(m->r[i]&255u,out)==EOF||fputc(m->r[i]>>8u,out)==EOF)return 0;}
    return 1;
}
int main(int argc,char **argv) {
    if(argc!=4&&argc!=5)return 2;
    Lc3Image im={0};AsmError e;const char *dirs[]={argv[2]};uint16_t kernel=0,wrapper=0;
    Lc3 *m=malloc(sizeof *m);FILE *f=fopen(argv[3],"wb");
    if(!m||!f||!lc3_assemble_file(argv[1],dirs,1,&im,&e)) {fprintf(stderr,"No se pudo preparar la prueba.\n");if(f)fclose(f);free(m);return 2;}
    for(size_t i=0;i<im.symbol_count;++i){
        const char *n=im.symbols[i].name;size_t len=strlen(n);
        if(len>=11&&!strcmp(n+len-11,"_SQRT_NR_Q8"))kernel=im.symbols[i].address;
        if(len>=13&&!strcmp(n+len-13,"_SQRT_NR_DQ16"))wrapper=im.symbols[i].address;
    }
    if(!kernel||!wrapper){fprintf(stderr,"No se encontraron los simbolos SQRT.\n");fclose(f);free(m);lc3_image_free(&im);return 2;}
    unsigned cases=0;
    for(unsigned a=1024;a<=4096;++a){if(!call(m,&im,kernel,(uint16_t)a,0,f))return 1;++cases;}
    const uint16_t integer[]={0,1,2,3,4,15,16,17,127,256,4096,32767};
    const uint16_t fraction[]={0,1,32767,32768,65535};
    for(unsigned i=0;i<12;++i)for(unsigned j=0;j<5;++j){if(!call(m,&im,wrapper,integer[i],fraction[j],f))return 1;++cases;}
    uint32_t state=314159u;
    for(unsigned i=0;i<2048;++i){state=state*1664525u+1013904223u;uint16_t a=(uint16_t)((state>>16u)&32767u);state=state*1664525u+1013904223u;uint16_t b=(uint16_t)state;
        if(!call(m,&im,wrapper,a,b,f))return 1;
        ++cases;}
    fclose(f);lc3_image_free(&im);free(m);
    if(argc==5){
        FILE *actual=fopen(argv[3],"rb"),*reference=fopen(argv[4],"rb");int equal=1;
        if(!actual||!reference){if(actual)fclose(actual);if(reference)fclose(reference);return 2;}
        for(;;){int a=fgetc(actual),b=fgetc(reference);if(a!=b){equal=0;break;}if(a==EOF)break;}
        if(ferror(actual)||ferror(reference))equal=0;
        fclose(actual);fclose(reference);if(!equal){fprintf(stderr,"El resultado SQRT difiere de la referencia anterior.\n");return 1;}
    }
    printf("SQRT: %u llamadas con preservacion de registros.\n",cases);return 0;
}
