#include "lc3.h"
#include <stdio.h>
#include <stdlib.h>
int main(int argc,char **argv) {
    if(argc!=3)return 2;
    Lc3Image im={0};AsmError e;Lc3 *m=malloc(sizeof *m);FILE *f=fopen(argv[2],"wb");
    if(!m||!f||!lc3_object_read(argv[1],&im,&e)){if(f)fclose(f);free(m);return 2;}
    unsigned slots[]={9,12,13,14};uint32_t seed=123456u;unsigned cases=0;
    for(unsigned k=0;k<4;++k)for(unsigned i=0;i<1024;++i) {
        if(!lc3_init(m,&im,&e))return 2;
        seed=seed*1664525u+1013904223u;uint16_t a=(uint16_t)(seed>>8u);
        seed=seed*1664525u+1013904223u;uint16_t b=(uint16_t)(seed>>8u);
        if(k==0)a=(uint16_t)(1u+a%32767u);
        m->r[0]=a;m->r[1]=b;m->r[2]=0x2222;m->r[3]=0x3333;m->r[4]=0x4444;m->r[5]=0x5555;
        m->r[7]=im.origin;m->pc=lc3_peek(m,(uint16_t)(im.origin+2+2*slots[k]));
        while(m->pc!=im.origin&&(m->mcr&0x8000u)&&m->instructions<50000)lc3_step(m);
        if(m->pc!=im.origin||m->last_exception){fprintf(stderr,"fallo slot=%u\n",slots[k]);return 1;}
        if(fwrite(m->r,sizeof m->r,1,f)!=1)return 2;
        uint16_t cc=m->psr&7u;if(fwrite(&cc,sizeof cc,1,f)!=1)return 2;
        ++cases;
    }
    fclose(f);free(m);lc3_image_free(&im);printf("%u casos diferenciales.\n",cases);return 0;
}
