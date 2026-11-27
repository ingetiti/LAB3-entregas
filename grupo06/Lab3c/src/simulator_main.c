#include "lc3.h"
#include "console.h"
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void output(void *context,unsigned char c) {
    (void)context;putchar(c);fflush(stdout);
}
int main(int argc,char **argv) {
    uint64_t limit=10000000;const char *input_path=NULL;FILE *input=NULL;
    Lc3Image image={0};AsmError error;Lc3 *m;int status=0;
    if(argc<2||!strcmp(argv[1],"--help")) {
        puts("Uso: simulador programa.obj [--max-instructions N] [--input teclado.txt]\n"
             "Entrada: objeto binario ISA3C, con origen big-endian de dos bytes.\n"
             "Esc interrumpe la ejecucion interactiva. No ensambla archivos ASM.");
        return argc<2?1:0;
    }
    for(int i=2;i<argc;++i) {
        if(!strcmp(argv[i],"--input")&&i+1<argc)input_path=argv[++i];
        else if(!strcmp(argv[i],"--max-instructions")&&i+1<argc) {
            char *end;errno=0;const char *arg=argv[++i];
            unsigned long long n=strtoull(arg,&end,10);
            if(errno||*end||!n||*arg=='-'){fprintf(stderr,"Limite invalido.\n");return 1;}
            limit=(uint64_t)n;
        } else {fprintf(stderr,"Opcion desconocida: %s\n",argv[i]);return 1;}
    }
    size_t len=strlen(argv[1]);
    if(len>=4&&!strcmp(argv[1]+len-4,".asm")) {
        fprintf(stderr,"Ensamble primero: ensamblador archivo.asm -o programa.obj\n");return 1;
    }
    if(!lc3_object_read(argv[1],&image,&error)) {fprintf(stderr,"%s\n",error.text);return 1;}
    m=malloc(sizeof *m);
    if(!m||!lc3_init(m,&image,&error)) {
        fprintf(stderr,"%s\n",m?error.text:"Sin memoria.");lc3_image_free(&image);free(m);return 1;
    }
    if(input_path) {
        input=fopen(input_path,"rb");
        if(!input){fprintf(stderr,"No se pudo abrir %s\n",input_path);lc3_image_free(&image);free(m);return 1;}
    }
    console_init();m->output=output;
    while((m->mcr&0x8000u)&&m->instructions<limit) {
        if(m->input_count<LC3_INPUT_SIZE) {
            int key=input?fgetc(input):console_key();
            if(key>=0) {
                if(!input&&console_interactive()&&key==27){status=3;break;}
                /* GETLINE de la catedra espera LF, tambien en Windows. */
                if(key!='\r'||!input)lc3_key(m,(unsigned char)(key=='\r'?'\n':key));
            }
        }
        lc3_step(m);
        if(m->waiting_for_input&&!m->input_count&&!(m->kbsr&0x8000u)&&console_interactive())console_idle();
    }
    if(m->last_exception)status=4;
    else if(!status&&(m->mcr&0x8000u))status=2;
    console_shutdown();if(input)fclose(input);
    printf("\nMETRICAS instrucciones=%" PRIu64 " interrupciones=%" PRIu64
           " programa_bytes=%zu accedidos_bytes=%zu escritos_bytes=%zu excepcion=%u\n",
           m->instructions,m->interrupts,m->program_bytes,m->accessed_bytes,m->written_bytes,m->last_exception);
    if(status==2)fprintf(stderr,"Se alcanzo el limite de instrucciones.\n");
    if(status==3)fprintf(stderr,"Ejecucion interrumpida.\n");
    printf("TRAFICO lecturas_bytes=%" PRIu64 " escrituras_bytes=%" PRIu64 "\n",m->memory_read_bytes,m->memory_write_bytes);
    lc3_image_free(&image);free(m);return status;
}
