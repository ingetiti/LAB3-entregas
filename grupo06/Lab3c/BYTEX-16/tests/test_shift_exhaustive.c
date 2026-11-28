#include "lc3.h"
#include <stdio.h>
#include <stdlib.h>
int main(void) {
    Lc3 *m=malloc(sizeof *m);AsmError e;unsigned failures=0;
    uint8_t bytes[2]={0xF8,0x22};Lc3Image image={0};image.origin=0x3000;image.count=2;image.bytes=bytes;
    if(!m||!lc3_init(m,&image,&e)){free(m);return 2;}
    for(unsigned mode=0;mode<3;++mode){
        lc3_poke(m,0x3000,(uint16_t)(0xF822u|mode<<3u));
        for(unsigned n=0;n<16;++n)for(unsigned x=0;x<65536;++x){
            m->pc=0x3000;m->r[1]=(uint16_t)x;m->r[2]=(uint16_t)n;
            uint16_t want;
            if(mode==0)want=(uint16_t)(x*(1u<<n));
            else if(mode==1)want=(uint16_t)(x/(1u<<n));
            else {int value=x<32768?(int)x:(int)x-65536,divisor=1<<n;
                want=(uint16_t)(value>=0?value/divisor:(value-divisor+1)/divisor);}
            lc3_step(m);
            int value=(int)(int16_t)want;unsigned cc=value<0?4u:value==0?2u:1u;
            if(m->r[0]!=want||(m->psr&7u)!=cc||m->last_exception||m->r[1]!=x||m->r[2]!=n){
                if(failures++<5)fprintf(stderr,"mode=%u n=%u x=%u\n",mode,n,x);
            }
        }
    }
    printf("SHL/SHR/SAR: 3145728 combinaciones, %u fallos.\n",failures);free(m);return failures?1:0;
}
