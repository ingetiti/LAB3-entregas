#include "assembler.h"
#include <stdio.h>
#include <string.h>

int main(int argc,char **argv) {
    const char *input=NULL,*output=NULL,*header=NULL,*includes[64];
    size_t include_count=0;
    Lc3Image image;
    AsmError error;
    int ok=0;
    for(int i=1;i<argc;++i) {
        if(!strcmp(argv[i],"-o")&&i+1<argc) output=argv[++i];
        else if(!strcmp(argv[i],"--emit-c")&&i+1<argc) header=argv[++i];
        else if(!strcmp(argv[i],"-I")&&i+1<argc&&include_count<64) includes[include_count++]=argv[++i];
        else if(!input&&argv[i][0]!='-') input=argv[i];
        else goto usage;
    }
    if(!input||!output) goto usage;
    if(!lc3_assemble_file(input,includes,include_count,&image,&error)) {
        fprintf(stderr,"%s:%u: %s\n",*error.path?error.path:input,error.line,error.text);return 1;
    }
    if(!lc3_object_write(output,&image,&error)) {fprintf(stderr,"%s\n",error.text);goto done;}
    if(header) {
        FILE *f=fopen(header,"wb");
        if(!f) {fprintf(stderr,"No se pudo crear cabecera.\n");goto done;}
        fprintf(f,"/* Generado desde %s. */\nstatic const unsigned short lc3_os_origin=0x%04X;\nstatic const unsigned char lc3_os_bytes[]={\n",input,image.origin);
        for(size_t i=0;i<image.count;++i) fprintf(f,"0x%02X,%s",image.bytes[i],i%16==15?"\n":"");
        fprintf(f,"\n};\n");
        int write_error=ferror(f);
        if(fclose(f)!=0)write_error=1;
        if(write_error) {fprintf(stderr,"Error al guardar cabecera.\n");goto done;}
    }
    printf("%s: %zu bytes desde x%04X, %zu simbolos.\n",output,image.count,image.origin,image.symbol_count);ok=1;
done:
    lc3_image_free(&image);return ok?0:1;
usage:
    fprintf(stderr,"Uso: ensamblador programa.asm -o programa.obj [-I directorio] [--emit-c cabecera.h]\n");return 1;
}
