#include "lc3.h"
#include <stdio.h>
#include <stdlib.h>
#define main exp_reference_cli
#include "../benchmark/originales/exp_referencia.c"
#undef main

int main(int argc,char **argv) {
    Lc3Image image={0};AsmError error;Lc3 *m=malloc(sizeof *m);
    unsigned failures=0;uint64_t instructions=0;
    if(argc!=2||!m||!lc3_object_read(argv[1],&image,&error)) {free(m);return 2;}
    for(unsigned value=0;value<65536;++value) {
        if(!lc3_init(m,&image,&error)){free(m);lc3_image_free(&image);return 2;}
        int16_t x=(int16_t)value;Resultado expected=exp_q3_12(x,NULL);
        m->r[0]=(uint16_t)x;
        for(unsigned i=1;i<6;++i)m->r[i]=(uint16_t)(0x1111u*i);
        m->r[7]=image.origin;
        m->pc=lc3_peek(m,(uint16_t)(image.origin+10u)); /* casilla EXP, indice 4 */
        while(m->pc!=image.origin&&(m->mcr&0x8000u)&&m->instructions<20000)lc3_step(m);
        int ok=m->pc==image.origin&&!m->last_exception&&(int16_t)m->r[0]==expected.valor&&m->r[6]==0xFE00&&m->r[7]==image.origin;
        for(unsigned i=1;i<6;++i)ok=ok&&m->r[i]==(uint16_t)(0x1111u*i);
        if(!ok&&failures++<10)fprintf(stderr,"EXP(%d) esperado %d, obtenido %d\n",x,expected.valor,(int16_t)m->r[0]);
        instructions+=m->instructions;
    }
    printf("EXP: 65536 entradas, %u fallos; %llu instrucciones simuladas. R1-R7 preservados.\n",failures,(unsigned long long)instructions);
    lc3_image_free(&image);free(m);return failures?1:0;
}
