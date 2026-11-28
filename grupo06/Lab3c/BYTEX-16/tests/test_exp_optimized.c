#include "lc3.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define main exp_reference_cli
#include "../benchmark/originales/exp_referencia.c"
#undef main

typedef struct {Lc3Image image;uint16_t entry,work,round,product,product_end,status,iterations;} Program;
static uint16_t suffix(const Lc3Image *im,const char *end) {
    size_t n=strlen(end);
    for(size_t i=0;i<im->symbol_count;++i){const char *s=im->symbols[i].name;size_t len=strlen(s);
        if(len>=n&&!strcmp(s+len-n,end))return im->symbols[i].address;}
    return 0;
}
static int prepare(const char *path,Program *p) {
    AsmError e;const char *dirs[]={"benchmark/modulos"};
    if(!lc3_assemble_file(path,dirs,1,&p->image,&e)){fprintf(stderr,"%s:%u: %s\n",path,e.line,e.text);return 0;}
    p->entry=suffix(&p->image,"_EXP_Q3_12");p->work=suffix(&p->image,"_TRABAJO");
    p->round=suffix(&p->image,"_REDONDEA");p->product=suffix(&p->image,"_EXP_PRODUCTO");
    p->product_end=suffix(&p->image,"_EXP_MULT_FIN");p->status=suffix(&p->image,"_EST_EXP");
    p->iterations=suffix(&p->image,"_NUM_ITER");
    return p->entry&&p->work&&p->round&&p->status&&p->iterations;
}
static int init(Lc3 *m,const Program *p) {AsmError e;return lc3_init(m,&p->image,&e);}
static int run_to(Lc3 *m,uint16_t stop,uint64_t limit) {
    while(m->pc!=stop&&(m->mcr&0x8000u)&&m->instructions<limit)lc3_step(m);
    return m->pc==stop&&!m->last_exception;
}
static int invoke(Lc3 *m,const Program *p,int16_t input) {
    if(!init(m,p))return 0;
    m->r[0]=(uint16_t)input;
    for(unsigned i=1;i<6;++i)m->r[i]=(uint16_t)((0x1111u*i)^(uint16_t)input);
    m->r[6]=0xFCEE;m->r[7]=p->image.origin;m->pc=p->entry;
    if(!run_to(m,p->image.origin,20000))return 0;
    for(unsigned i=1;i<6;++i)if(m->r[i]!=(uint16_t)((0x1111u*i)^(uint16_t)input))return 0;
    uint16_t cc=m->r[0]?((m->r[0]&0x8000u)?4u:1u):2u;
    return m->r[6]==0xFCEE&&m->r[7]==p->image.origin&&(m->psr&7u)==cc;
}
static int helper_round(Lc3 *m,const Program *p,unsigned n,uint64_t value) {
    if(!init(m,p))return 0;
    m->r[0]=(uint16_t)n;m->r[5]=p->work;m->r[6]=0xFCEE;m->r[7]=p->image.origin;m->pc=p->round;
    for(unsigned i=0;i<3;++i)lc3_poke(m,(uint16_t)(p->work+26u+2u*i),(uint16_t)((value>>(15u*i))&32767u));
    if(!run_to(m,p->image.origin,2000))return 0;
    uint64_t got=(uint64_t)m->r[0]|(uint64_t)m->r[1]<<15u|(uint64_t)m->r[2]<<30u;
    uint64_t want=(value+(UINT64_C(1)<<(n-1u)))>>n;
    return got==want&&m->r[0]<=32767u&&m->r[1]<=32767u&&m->r[2]<=32767u&&m->r[5]==p->work&&m->r[6]==0xFCEE;
}
static int helper_product(Lc3 *m,const Program *p,unsigned digit,uint32_t value) {
    if(!p->product||!p->product_end||!init(m,p))return 0;
    m->r[0]=0xAAAA;m->r[1]=0xBBBB;m->r[2]=0xCCCC;m->r[3]=(uint16_t)digit;
    m->r[5]=p->work;m->r[6]=0xFCEE;m->r[7]=32767;m->pc=p->product;
    for(unsigned i=0;i<3;++i)lc3_poke(m,(uint16_t)(p->work+12u+2u*i),(uint16_t)(((uint64_t)value>>(15u*i))&32767u));
    if(!run_to(m,p->product_end,2000))return 0;
    uint64_t got=(uint64_t)m->r[0]|(uint64_t)m->r[1]<<15u|(uint64_t)m->r[2]<<30u;
    return got==(uint64_t)value*digit&&m->r[0]<=32767u&&m->r[1]<=32767u&&m->r[2]<=32767u&&m->r[5]==p->work&&m->r[6]==0xFCEE;
}
int main(int argc,char **argv) {
    if(argc!=5){fprintf(stderr,"Uso: test_exp_optimized anterior.asm nueva.asm salida.csv resumen.json\n");return 2;}
    Program old={0},now={0};Lc3 *a=malloc(sizeof *a),*b=malloc(sizeof *b);
    FILE *csv=NULL,*json=NULL;unsigned failures=0,improved=0,equal=0,worse=0,round_cases=0,product_cases=0;
    uint64_t total_old=0,total_new=0,max_old=0,max_new=0;
    int status=2;
    if(!a||!b||!prepare(argv[1],&old)||!prepare(argv[2],&now))goto done;
    csv=fopen(argv[3],"w");json=fopen(argv[4],"w");if(!csv||!json)goto done;
    fprintf(csv,"entrada_cruda,x,salida_cruda,estado,iteraciones,antes,despues,ahorro\n");
    for(int32_t x=-32768;x<=32767;++x){
        int ok_old=invoke(a,&old,(int16_t)x),ok_new=invoke(b,&now,(int16_t)x);
        Resultado reference=exp_q3_12((int16_t)x,NULL);
        uint16_t state=lc3_peek(b,now.status),steps=lc3_peek(b,now.iterations);
        uint16_t want_steps=(x==0||x<=-25553||x>19873)?0u:6u;
        int ok=ok_old&&ok_new&&a->r[0]==b->r[0]&&(int16_t)b->r[0]==reference.valor&&
               state==(uint16_t)reference.estado&&steps==want_steps&&
               state==lc3_peek(a,old.status)&&steps==lc3_peek(a,old.iterations);
        if(!ok&&failures++<10)fprintf(stderr,"Fallo EXP raw=%ld: antes=%d despues=%d C=%d estado=%u pasos=%u\n",(long)x,(int16_t)a->r[0],(int16_t)b->r[0],reference.valor,state,steps);
        uint64_t prev=a->instructions,next=b->instructions;total_old+=prev;total_new+=next;
        if(prev>max_old)max_old=prev;
        if(next>max_new)max_new=next;
        if(next<prev)++improved;else if(next==prev)++equal;else ++worse;
        fprintf(csv,"%ld,%.12f,%u,%u,%u,%" PRIu64 ",%" PRIu64 ",%" PRId64 "\n",(long)x,(double)x/4096.0,b->r[0],state,steps,prev,next,(int64_t)prev-(int64_t)next);
    }
    const uint64_t edges[]={0,1,2,3,32766,32767,32768,65535,UINT64_C(1)<<29u,(UINT64_C(1)<<30u)-1u,UINT64_C(1)<<30u,(UINT64_C(1)<<44u)-1u,UINT64_C(1)<<44u,(UINT64_C(1)<<45u)-1u};
    uint64_t random=314159265;
    for(unsigned n=1;n<45;++n){
        for(size_t j=0;j<sizeof edges/sizeof edges[0];++j){++round_cases;if(!helper_round(b,&now,n,edges[j])){if(failures++<10)fprintf(stderr,"Fallo REDONDEA n=%u value=%" PRIu64 "\n",n,edges[j]);}}
        for(unsigned j=0;j<512;++j){random=random*UINT64_C(6364136223846793005)+1u;uint64_t value=random&((UINT64_C(1)<<45u)-1u);++round_cases;
            if(!helper_round(b,&now,n,value)){if(failures++<10)fprintf(stderr,"Fallo REDONDEA aleatorio n=%u\n",n);}}
    }
    const uint32_t products[]={0,1,32767,32768,65535,65536,1073741824,2147483647};
    for(unsigned digit=0;digit<=16;++digit){
        for(size_t j=0;j<sizeof products/sizeof products[0];++j){++product_cases;if(!helper_product(b,&now,digit,products[j])){if(failures++<10)fprintf(stderr,"Fallo producto d=%u value=%u\n",digit,products[j]);}}
        for(unsigned j=0;j<1024;++j){random=random*UINT64_C(6364136223846793005)+1u;++product_cases;
            if(!helper_product(b,&now,digit,(uint32_t)(random&2147483647u))){if(failures++<10)fprintf(stderr,"Fallo producto aleatorio d=%u\n",digit);}}
    }
    if(worse){fprintf(stderr,"%u entradas ejecutan mas instrucciones.\n",worse);++failures;}
    fprintf(json,"{\n  \"entradas_exp\": 65536,\n  \"fallos\": %u,\n  \"registros_R1_R7_preservados\": %s,\n  \"casos_redondeo\": %u,\n  \"casos_producto\": %u,\n  \"instrucciones_antes\": %" PRIu64 ",\n  \"instrucciones_despues\": %" PRIu64 ",\n  \"maximo_antes\": %" PRIu64 ",\n  \"maximo_despues\": %" PRIu64 ",\n  \"entradas_mas_rapidas\": %u,\n  \"entradas_iguales\": %u,\n  \"entradas_mas_lentas\": %u,\n  \"bytes_antes\": %zu,\n  \"bytes_despues\": %zu\n}\n",failures,failures?"false":"true",round_cases,product_cases,total_old,total_new,max_old,max_new,improved,equal,worse,old.image.count,now.image.count);
    printf("EXP: 65536 entradas, REDONDEA: %u casos, producto: %u casos, fallos: %u.\n",round_cases,product_cases,failures);
    printf("Instrucciones: %" PRIu64 " -> %" PRIu64 "; reduccion %.2f%%. Mas lentas: %u.\n",total_old,total_new,100.0*(1.0-(double)total_new/(double)total_old),worse);
    status=failures?1:0;
done:
    if(csv)fclose(csv);
    if(json)fclose(json);
    lc3_image_free(&old.image);lc3_image_free(&now.image);free(a);free(b);
    return status;
}
