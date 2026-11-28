#include "lc3.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Contrato del main recibido: [indice, a, b, resultado0, resultado1].
 * Las entradas se fijan independientemente del ensamblador y del menu.
 * Las tolerancias se expresan en unidades del formato de salida. */
typedef struct { int a,b; int64_t want; unsigned tolerance; int double_word; } Case;
static const Case cases[]={
 {9651,0,-3217,2,0}, {600,0,3547,3,0}, {4289,0,14188,4,0},
 {4289,0,14188,64,0}, {4289,0,8193,4,0}, {1342,0,1342,0,0},
 {-1078,0,-1078,0,0}, {1115,0,1069,1,0}, {4,23395,136795,256,1},
 {4096,0,696,0,0}, {-512,5,-8192,0,0}, {-2,5,-32,0,0},
 {3540,-1853,-25624,2,0}, {3540,-1853,-6559620,0,1},
 {3540,-1853,-25624,0,0}, {1630,828,504,1,0}, {1630,828,504,12,0},
 {8192,22938,11703,2,0}, {256,0,89,4,0}, {8192,0,2839,32,0},
 {48,18,6,0,0}, {16,38,304,0,0}, {21980,0,1373,0,0}
};
static char output[60000];
static size_t used;
static void capture(void *context,unsigned char ch){
 (void)context;
 if(used+1u<sizeof output){output[used++]=(char)ch;output[used]=0;}
}
static void discard(void *context,unsigned char ch){(void)context;(void)ch;}
static void run(Lc3 *machine,const char *keys){
 used=0;output[0]=0;machine->output=capture;
 for(const char *p=keys;*p;++p)lc3_key(machine,(unsigned char)*p);
 while((machine->mcr&0x8000u)&&machine->instructions<2000000u)lc3_step(machine);
}
static int assemble(const char *path,Lc3Image *image){
 const char *includes[]={"benchmark/modulos"};AsmError error;
 if(lc3_assemble_file(path,includes,1,image,&error))return 1;
 fprintf(stderr,"%s:%u: %s\n",error.path,error.line,error.text);return 0;
}
static int automatic(const char *object_path,int original_main,int verbose){
 Lc3Image image={0},source={0};AsmError error;Lc3 *machine=malloc(sizeof *machine);
 uint16_t table=0,main_address=0;unsigned failures=0;
 const char *source_path=original_main?"benchmark/main_grupo27.asm":"benchmark/calculadora_automatica.asm";
 if(!machine||!assemble(source_path,&source)){free(machine);return 0;}
 if(original_main){
  if(!lc3_init(machine,&source,&error)){lc3_image_free(&source);free(machine);return 0;}
 }else{
  if(!lc3_object_read(object_path,&image,&error)||!lc3_init(machine,&image,&error)){
   lc3_image_free(&source);lc3_image_free(&image);free(machine);return 0;
  }
  /* El OBJ publicado debe coincidir con todos los ASM que se entregan. */
  if(image.origin!=source.origin||image.count!=source.count||memcmp(image.bytes,source.bytes,image.count)){
   fprintf(stderr,"OBJ desactualizado: %s\n",object_path);++failures;
  }
 }
 if(!lc3_symbol(&source,"programa_del_menu_completo",&table)||!lc3_symbol(&source,"main",&main_address)){
  lc3_image_free(&source);lc3_image_free(&image);free(machine);return 0;
 }
 for(unsigned i=0;i<23u;++i){
  uint16_t row=(uint16_t)(table+2u+10u*i);
  if(lc3_peek(machine,row)!=i+1u||lc3_peek(machine,(uint16_t)(row+2u))!=(uint16_t)cases[i].a||
     lc3_peek(machine,(uint16_t)(row+4u))!=(uint16_t)cases[i].b){
   fprintf(stderr,"Entrada del benchmark distinta, operacion %u\n",i+1u);++failures;
  }
 }
 lc3_poke(machine,table,(uint16_t)verbose);
 if(original_main){
  /* Seleccionar el bloque completo del main intacto sin editar el archivo:
   * R0=puntero y continuar despues de su AND inicial (modo interactivo). */
  machine->r[0]=table;machine->pc=(uint16_t)(main_address+2u);
 }
 run(machine,"");
 if((machine->mcr&0x8000u)||machine->last_exception){
  fprintf(stderr,"No finaliza: pc=x%04X, excepcion=%u\n",machine->pc,machine->last_exception);++failures;
 }
 FILE *csv=(!original_main&&verbose)?fopen("build/benchmark_grupo27.csv","w"):NULL;
 if(csv)fputs("operacion,entrada_R0,entrada_R1,salida_R0,salida_R1,esperado_crudo,tolerancia,resultado\n",csv);
 for(unsigned i=0;i<23u;++i){
  const Case *c=&cases[i];uint16_t row=(uint16_t)(table+2u+10u*i);
  uint16_t high=lc3_peek(machine,(uint16_t)(row+6u)),low=lc3_peek(machine,(uint16_t)(row+8u));
  int64_t actual=(int16_t)high;
  if(c->double_word)actual=actual*65536+low;
  int64_t delta=actual-c->want;if(delta<0)delta=-delta;
  int ok=delta<=c->tolerance&&(c->double_word||!low)&&
         lc3_peek(machine,row)==i+1u&&lc3_peek(machine,(uint16_t)(row+2u))==(uint16_t)c->a&&
         lc3_peek(machine,(uint16_t)(row+4u))==(uint16_t)c->b;
  if(!ok){fprintf(stderr,"Operacion %u: %" PRId64 ", esperado %" PRId64 " +- %u\n",i+1u,actual,c->want,c->tolerance);++failures;}
  if(csv)fprintf(csv,"%u,%d,%d,%d,%u,%" PRId64 ",%u,%s\n",i+1u,c->a,c->b,(int)(int16_t)high,low,c->want,c->tolerance,ok?"OK":"ERROR");
 }
 if(csv)fclose(csv);
 if(lc3_peek(machine,(uint16_t)(table+2u+23u*10u))!=0u)++failures;
 if(!strstr(output,"Hexadecimal: 053E")||!strstr(output,"Binario: 1111101111001010"))++failures;
 if(verbose&&(!strstr(output,"==MAXIMO COMUN DIVISOR==")||!strstr(output,"==Q3.12 -> Q7.8==")||
              !strstr(output,"(Q15.16) -100.09185791")))++failures;
 if(strstr(output,"sin subrutina")||strstr(output,"se ejecutaria"))++failures;
 printf("%s automatico G27 (%s, verboso=%d): 23 operaciones, %" PRIu64 " instrucciones, %u fallos\n",
        failures?"ERROR":"OK",original_main?"main recibido":"OBJ entregado",verbose,machine->instructions,failures);
 if(failures)puts(output);
 lc3_image_free(&source);lc3_image_free(&image);free(machine);return failures==0;
}
static int interactive(const char *path,const char *keys,const char *want){
 Lc3Image image={0};AsmError error;Lc3 *machine=malloc(sizeof *machine);
 if(!machine||!lc3_object_read(path,&image,&error)||!lc3_init(machine,&image,&error)){free(machine);return 0;}
 run(machine,keys);
 int ok=!(machine->mcr&0x8000u)&&!machine->last_exception&&strstr(output,want)!=NULL;
 printf("%s interactivo %s: %" PRIu64 " instrucciones\n",ok?"OK":"ERROR",want,machine->instructions);
 if(!ok)puts(output);
 free(machine);lc3_image_free(&image);return ok;
}
static int check_product(Lc3 *machine,const Lc3Image *image,uint16_t routine,int a,int b){
 AsmError error;if(!lc3_init(machine,image,&error))return 0;
 machine->output=discard;machine->r[0]=(uint16_t)a;machine->r[1]=(uint16_t)b;
 for(unsigned r=2;r<6u;++r)machine->r[r]=(uint16_t)(0x1111u*r);
 machine->r[7]=image->origin;machine->pc=routine;
 while(machine->pc!=image->origin&&(machine->mcr&0x8000u)&&machine->instructions<10000u)lc3_step(machine);
 int64_t actual=(int64_t)(int16_t)machine->r[0]*65536+machine->r[1];
 int ok=machine->pc==image->origin&&!machine->last_exception&&actual==(int64_t)a*b;
 for(unsigned r=2;r<6u;++r)if(machine->r[r]!=(uint16_t)(0x1111u*r))ok=0;
 if(machine->r[6]!=0xFE00u||machine->r[7]!=image->origin)ok=0;
 if(!ok)fprintf(stderr,"Shift+Add %d * %d: %" PRId64 " en vez de %" PRId64 "\n",a,b,actual,(int64_t)a*b);
 return ok;
}
static int products(void){
 Lc3Image image={0};AsmError error;Lc3 *machine=malloc(sizeof *machine);unsigned failures=0,count=0;
 static const int values[]={-32768,-32767,-1853,-512,-256,-1,0,1,255,256,512,3540,16384,32767};
 if(!machine||!assemble("benchmark/funciones.asm",&image)||!lc3_init(machine,&image,&error)){free(machine);return 0;}
 uint16_t routine=lc3_peek(machine,(uint16_t)(image.origin+4u));
 for(size_t i=0;i<sizeof values/sizeof values[0];++i)for(size_t j=0;j<sizeof values/sizeof values[0];++j){
  failures+=(unsigned)!check_product(machine,&image,routine,values[i],values[j]);++count;
 }
 uint32_t state=0x6A27u;
 for(unsigned i=0;i<4096u;++i){
  state=state*1664525u+1013904223u;int a=(int16_t)(state>>16u);
  state=state*1664525u+1013904223u;int b=(int16_t)(state>>16u);
  failures+=(unsigned)!check_product(machine,&image,routine,a,b);++count;
 }
 printf("Shift+Add: %u productos con signo y preservacion de registros, %u fallos\n",count,failures);
 lc3_image_free(&image);free(machine);return failures==0;
}
static int taylor(void){
 Lc3Image image={0};AsmError error;Lc3 *machine=malloc(sizeof *machine);unsigned failures=0;uint16_t routine=0;
 static const int angles[]={0,150,300,600,900,1800,2050,2700,3600,-1,3601};
 static const int expected[]={0,1060,2048,3547,4096,0,-1731,-4096,0,0,0};
 if(!machine||!assemble("benchmark/calculadora_automatica.asm",&image)){free(machine);return 0;}
 for(size_t i=0;i<image.symbol_count;++i){
  const char *name=image.symbols[i].name;size_t n=strlen(name),suffix=strlen("_CALCULAR_SENO");
  if(n>=suffix&&!strcmp(name+n-suffix,"_CALCULAR_SENO"))routine=image.symbols[i].address;
 }
 if(!routine){lc3_image_free(&image);free(machine);return 0;}
 for(size_t i=0;i<sizeof angles/sizeof angles[0];++i){
  if(!lc3_init(machine,&image,&error)){++failures;break;}
  machine->output=discard;machine->r[0]=(uint16_t)angles[i];
  for(unsigned r=1;r<6u;++r)machine->r[r]=(uint16_t)(0x1111u*r);
  machine->r[7]=image.origin;machine->pc=routine;
  while(machine->pc!=image.origin&&(machine->mcr&0x8000u)&&machine->instructions<2000000u)lc3_step(machine);
  int delta=(int)(int16_t)machine->r[0]-expected[i];if(delta<0)delta=-delta;
  int ok=machine->pc==image.origin&&!machine->last_exception&&delta<=3;
  for(unsigned r=1;r<6u;++r)if(machine->r[r]!=(uint16_t)(0x1111u*r))ok=0;
  if(machine->r[6]!=0xFE00u||machine->r[7]!=image.origin)ok=0;
  if(!ok){fprintf(stderr,"Taylor %d: salida %d, esperado %d; pc=x%04X\n",angles[i],(int)(int16_t)machine->r[0],expected[i],machine->pc);++failures;}
 }
 printf("Taylor: 11 entradas, 4 cuadrantes, limites y preservacion R1-R7, %u fallos\n",failures);
 lc3_image_free(&image);free(machine);return failures==0;
}
int main(int argc,char **argv){
 if(argc!=3)return 2;
 int ok=automatic(argv[1],0,1);
 ok=automatic(argv[1],0,0)&&ok;
 ok=automatic(argv[1],1,1)&&ok;
 ok=interactive(argv[2],"53\n\nd","(Q7.8) 20.0859375")&&ok;
 ok=interactive(argv[2],"10600\n\nd","(Q3.12) 0.865966796")&&ok;
 ok=interactive(argv[2],"301342\n\nd","Hexadecimal: 053E")&&ok;
 ok=interactive(argv[2],"31-1078\n\nd","Binario: 1111101111001010")&&ok;
 ok=products()&&ok;ok=taylor()&&ok;
 return !ok;
}
