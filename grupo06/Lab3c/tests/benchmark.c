#include "lc3.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>

typedef struct {const char *name; unsigned slot; int a,b,want0,want1,tolerance; } Case;
static const Case cases[]={
 {"cordic_div_0.25_0.5",0,8192,16384,16384,-1,2},
 {"shift_add_2_3",1,512,768,6,0,0},
 {"pow_bin_2_3",2,2,3,8,-1,0},
 {"pow_sucesiva_2_3",3,512,3,2048,-1,0},
 {"exp_0",4,0,0,256,-1,0},
 {"exp_1",4,4096,0,696,-1,0},
 {"exp_3",4,12288,0,5142,-1,0},
 {"exp_menos8",4,-32768,0,0,-1,0},
 {"exp_saturada",4,20480,0,32767,-1,0},
 {"mcm_12_18",5,12,18,36,-1,0},
 {"mcd_48_18",6,48,18,6,-1,0},
 {"sqrt_newton_4",7,4,0,2,0,2048},
 {"division_larga_6_2",8,1536,512,768,-1,0},
 {"log_cordic_1",9,4096,0,0,-1,16},
 {"division_newton_6_2",10,1536,512,768,-1,12},
 {"ln_borchardt_1",11,128,0,0,-1,4},
 {"conversion_1.5",12,6144,0,384,-1,0},
 {"booth_2_3",13,512,768,1536,-1,0},
 {"cordic_mul_2_3",14,512,768,1536,-1,0},
 {"reduccion_1",15,4096,0,4096,-1,0},
 {"seno_tabla_0",16,0,0,0,-1,0},
 {"seno_tabla_pi2",16,6434,0,16384,-1,4},
 {"coseno_tabla_0",17,0,0,16384,-1,4},
 {"sqrt_nonrest_4",18,1024,0,1024,-1,1},
 {"seno_cheb_0",19,0,0,0,-1,0},
 {"seno_cheb_pi2",19,6434,0,16384,-1,64},
 {"cordic_div_negativa",0,-8192,16384,-16384,-1,2},
 {"sqrt_newton_2",7,2,0,1,27146,2048},
 {"log_cordic_2",9,8192,0,2839,-1,32},
 {"ln_borchardt_2",11,256,0,89,-1,4},
 {"conversion_negativa",12,-6144,0,-384,-1,0},
 {"cordic_mul_negativa",14,-512,768,-1536,-1,0},
 {"reduccion_3",15,12288,0,-579,-1,0},
 {"seno_tabla_pi4",16,3217,0,11585,-1,180},
 {"coseno_tabla_pi4",17,3217,0,11585,-1,180},
 {"seno_tabla_negativo",16,-3217,0,-11585,-1,180},
 {"coseno_tabla_negativo",17,-3217,0,11585,-1,180},
};
static void ignore(void *context,unsigned char c){(void)context;(void)c;}
int main(int argc,char **argv) {
    Lc3Image image={0};AsmError error;unsigned failures=0;
    const char *path=argc>1?argv[1]:"build/funciones.obj";
    const char *csv=argc>2?argv[2]:"build/benchmark.csv";
    Lc3 *m=malloc(sizeof *m);FILE *f=fopen(csv,"w");
    if(!m||!f||!lc3_object_read(path,&image,&error)){
        fprintf(stderr,"No se pudo abrir el objeto, CSV o memoria.\n");if(f)fclose(f);free(m);return 2;
    }
    fprintf(f,"caso,entrada_R0,entrada_R1,salida_R0,salida_R1,esperado_R0,tolerancia,instrucciones,programa_bytes,accedidos_bytes,escritos_bytes,lecturas_acumuladas_bytes,escrituras_acumuladas_bytes,resultado\n");
    for(size_t i=0;i<sizeof cases/sizeof cases[0];++i) {
        const Case *c=&cases[i];uint64_t limit=2000000;
        if(!lc3_init(m,&image,&error)){fprintf(stderr,"%s\n",error.text);return 2;}
        m->output=ignore;m->r[0]=(uint16_t)c->a;m->r[1]=(uint16_t)c->b;
        m->r[2]=0x2222;m->r[3]=0x3333;m->r[4]=0x4444;m->r[5]=0x5555;
        m->r[7]=image.origin;
        m->pc=lc3_peek(m,(uint16_t)(image.origin+2u+2u*c->slot));
        while(m->pc!=image.origin&&(m->mcr&0x8000u)&&m->instructions<limit)lc3_step(m);
        int actual=(int)(int16_t)m->r[0];
        int delta=actual-c->want0;if(delta<0)delta=-delta;
        int ok=m->pc==image.origin&&!m->last_exception&&delta<=c->tolerance;
        if(c->want1>=0) {
            /* Q15.16: comparar el par completo, no solo su entero. */
            int64_t got=(int64_t)(int16_t)m->r[0]*65536+m->r[1];
            int64_t want=(int64_t)c->want0*65536+c->want1;
            int64_t diff=got-want;if(diff<0)diff=-diff;
            ok=ok&&diff<=c->tolerance;
        }
        if(c->slot==4)ok=ok&&m->r[1]==(uint16_t)c->b&&m->r[2]==0x2222&&m->r[3]==0x3333&&m->r[4]==0x4444&&m->r[5]==0x5555&&m->r[6]==0xFE00&&m->r[7]==image.origin;
        printf("%s %-26s R0=%d R1=%u instrucciones=%" PRIu64 " pc=x%04X excepcion=%u\n",ok?"OK":"ERROR",c->name,actual,m->r[1],m->instructions,m->pc,m->last_exception);
        fprintf(f,"%s,%d,%d,%d,%u,%d,%d,%" PRIu64 ",%zu,%zu,%zu,%" PRIu64 ",%" PRIu64 ",%s\n",c->name,c->a,c->b,actual,m->r[1],c->want0,c->tolerance,m->instructions,m->program_bytes,m->accessed_bytes,m->written_bytes,m->memory_read_bytes,m->memory_write_bytes,ok?"OK":"ERROR");
        failures+=(unsigned)!ok;
    }
    fclose(f);lc3_image_free(&image);free(m);
    printf("%zu casos, %u fallos. Metricas: %s\n",sizeof cases/sizeof cases[0],failures,csv);
    return failures?1:0;
}
