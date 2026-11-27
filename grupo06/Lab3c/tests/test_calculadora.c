#include "lc3.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static char out[30000];static size_t used;
static void capture(void *context,unsigned char c) {
    (void)context;if(used+1<sizeof out){out[used++]=(char)c;out[used]=0;}
}
static int run(const char *path,const char *keys,const char *want) {
    Lc3Image image={0};AsmError error;Lc3 *m=malloc(sizeof *m);
    if(!m||!lc3_object_read(path,&image,&error)||!lc3_init(m,&image,&error)) {
        fprintf(stderr,"No se pudo iniciar %s\n",path);free(m);return 0;
    }
    used=0;out[0]=0;m->output=capture;
    for(const char *k=keys;*k;++k)lc3_key(m,(unsigned char)*k);
    while((m->mcr&0x8000u)&&m->instructions<2000000)lc3_step(m);
    int ok=!(m->mcr&0x8000u)&&!m->last_exception&&strstr(out,want)!=NULL;
    printf("%s %s: %llu instrucciones\n",ok?"OK":"ERROR",path,(unsigned long long)m->instructions);
    if(!*keys)ok=ok&&strstr(out,"(Q15.16) 1.421875")&&strstr(out,"(Q1.14) 0");
    if(!ok)puts(out);
    free(m);lc3_image_free(&image);return ok;
}
int main(int argc,char **argv) {
    if(argc!=3)return 2;
    return !(run(argv[1],"","(Q7.8) -60")&&
             run(argv[2],"53\n\nd","(Q7.8) 20.0859375"));
}
