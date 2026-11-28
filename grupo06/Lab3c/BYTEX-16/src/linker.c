#include "assembler.h"
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_MODULES 128u
#define MAX_IMPORTS 128u
#define PATH_SIZE 1024u
int lc3_is_operation(const char *text);

typedef struct {
    char token[LC3_LABEL_SIZE];
    char symbol[LC3_LABEL_SIZE];
    size_t module;
    unsigned line;
} Import;
typedef struct {
    char path[PATH_SIZE];
    char *source;
    Import imports[MAX_IMPORTS];
    size_t import_count;
} Module;
typedef struct {
    Module modules[MAX_MODULES];
    size_t count;
    const char *const *directories;
    size_t directory_count;
    char *combined;
    size_t used;
    unsigned *source_lines;
    size_t *source_modules;
    size_t line_count;
    AsmError *error;
    const char *main_source;
} Linker;

static int same(const char *a,const char *b) {
    while(*a&&*b) if(toupper((unsigned char)*a++)!=toupper((unsigned char)*b++)) return 0;
    return *a==*b;
}
static int link_error(Linker *l,const char *path,unsigned line,const char *text) {
    if(l->error) {
        l->error->line=line;
        snprintf(l->error->path,sizeof l->error->path,"%s",path);
        snprintf(l->error->text,sizeof l->error->text,"%s",text);
    }
    return 0;
}
static int exists(const char *path) {
    FILE *f=fopen(path,"rb");
    if(!f) return 0;
    fclose(f);return 1;
}
static char *read_file(Linker *l,const char *path) {
    FILE *f=fopen(path,"rb");
    long length;
    char *text;
    if(!f) {link_error(l,path,0,"No se pudo abrir modulo.");return NULL;}
    if(fseek(f,0,SEEK_END)||(length=ftell(f))<0||(unsigned long)length>LC3_MAX_SOURCE||fseek(f,0,SEEK_SET)) {
        fclose(f);link_error(l,path,0,"Modulo vacio o mayor que 1 MiB.");return NULL;
    }
    text=malloc((size_t)length+1u);
    if(!text) {fclose(f);link_error(l,path,0,"Sin memoria.");return NULL;}
    if(fread(text,1,(size_t)length,f)!=(size_t)length||ferror(f)||memchr(text,0,(size_t)length)) {
        fclose(f);free(text);link_error(l,path,0,"Error de lectura o bytes NUL en modulo.");return NULL;
    }
    fclose(f);text[length]=0;return text;
}
static int find_module(Linker *l,const char *parent,const char *name,char *path) {
    char directory[PATH_SIZE];
    const char *last=NULL;
    for(const char *p=parent;*p;++p) if(*p=='/'||*p=='\\') last=p;
    if(last) {
        size_t n=(size_t)(last-parent);
        if(n>=sizeof directory) return 0;
        memcpy(directory,parent,n);directory[n]=0;
    } else strcpy(directory,".");
    for(size_t i=0;i<=l->directory_count;++i) {
        const char *base=i?l->directories[i-1u]:directory;
        int n=snprintf(path,PATH_SIZE,"%s/%s%s",base,name,strchr(name,'.')?"":".asm");
        if(n>0 && n<(int)PATH_SIZE && exists(path)) return 1;
    }
    return 0;
}
static int token_word(const char **cursor,const char *end,char *out,size_t capacity) {
    const char *p=*cursor;
    size_t n=0;
    while(p<end&&isspace((unsigned char)*p)) ++p;
    while(p<end&&!isspace((unsigned char)*p)&&*p!=';') {
        if(n+1u>=capacity) return 0;
        out[n++]=*p++;
    }
    out[n]=0;*cursor=p;return 1;
}
static int load_module(Linker *l,const char *path,size_t *index) {
    Module *m;
    const char *p;
    unsigned line=0;
    int ended=0;
    for(size_t i=0;i<l->count;++i) if(same(path,l->modules[i].path)) {*index=i;return 1;}
    if(l->count==MAX_MODULES) return link_error(l,path,0,"Demasiados modulos.");
    *index=l->count++;m=&l->modules[*index];
    if(strlen(path)>=sizeof m->path) return link_error(l,path,0,"Ruta demasiado larga.");
    strcpy(m->path,path);
    if(*index==0 && l->main_source) {
        size_t length=strlen(l->main_source);
        if(length>LC3_MAX_SOURCE) return link_error(l,path,0,"Fuente mayor que 1 MiB.");
        m->source=malloc(length+1u);
        if(m->source) memcpy(m->source,l->main_source,length+1u);
    } else m->source=read_file(l,path);
    if(!m->source) return 0;
    p=m->source;
    if(strlen(p)>=3&&(unsigned char)p[0]==0xEF&&(unsigned char)p[1]==0xBB&&(unsigned char)p[2]==0xBF) p+=3;
    while(*p) {
        const char *end=strchr(p,'\n'),*cursor=p;
        char op[LC3_LABEL_SIZE];
        ++line;if(!end) end=p+strlen(p);
        if(!token_word(&cursor,end,op,sizeof op)) return link_error(l,path,line,"Token demasiado largo.");
        if(*op) {
            if(ended) return link_error(l,path,line,"Hay codigo despues de .END.");
            if(same(op,".END")) {
                char extra[LC3_LABEL_SIZE];
                if(!token_word(&cursor,end,extra,sizeof extra)||*extra) return link_error(l,path,line,".END no admite operandos.");
                ended=1;
            } else if(same(op,".ORIG")&&*index!=0) return link_error(l,path,line,"El modulo importado debe omitir .ORIG.");
            else if(same(op,".EXTERNAL")) {
                char reference[LC3_LABEL_SIZE],extra[LC3_LABEL_SIZE],filename[LC3_LABEL_SIZE],resolved[PATH_SIZE];
                char *separator;
                Import *import;
                size_t child;
                if(!token_word(&cursor,end,reference,sizeof reference)||!token_word(&cursor,end,extra,sizeof extra)||*extra) return link_error(l,path,line,".EXTERNAL requiere archivo-simbolo.");
                separator=strrchr(reference,'-');
                if(!separator||separator==reference||!separator[1]) return link_error(l,path,line,"Importacion invalida. Use archivo-simbolo.");
                if(m->import_count==MAX_IMPORTS) return link_error(l,path,line,"Demasiadas importaciones.");
                strcpy(filename,reference);filename[separator-reference]=0;
                for(const char *c=filename;*c;++c) if(!isalnum((unsigned char)*c)&&*c!='_'&&*c!='.') return link_error(l,path,line,"Nombre de modulo invalido.");
                if(!find_module(l,path,filename,resolved)) {
                    char message[240];snprintf(message,sizeof message,"Modulo no encontrado: %.120s",filename);
                    return link_error(l,path,line,message);
                }
                if(!load_module(l,resolved,&child)) return 0;
                import=&m->imports[m->import_count++];
                strcpy(import->token,reference);strcpy(import->symbol,separator+1);
                import->module=child;import->line=line;
            }
        }
        p=*end?end+1:end;
    }
    if(!ended) return link_error(l,path,line,"Falta .END en modulo.");
    return 1;
}
static int append(Linker *l,const char *text,size_t length,size_t module,unsigned line) {
    if(l->used+length>LC3_MAX_SOURCE) return link_error(l,l->modules[module].path,line,"Programa enlazado mayor que 1 MiB.");
    memcpy(l->combined+l->used,text,length);l->used+=length;
    for(size_t i=0;i<length;++i) if(text[i]=='\n') {
        l->source_lines[l->line_count]=line;
        l->source_modules[l->line_count++]=module;
    }
    l->combined[l->used]=0;return 1;
}
static int symbol_name(char *out,size_t capacity,size_t module,const char *name) {
    int n=module?snprintf(out,capacity,"M%zu_%s",module,name):snprintf(out,capacity,"%s",name);
    return n>=0&&(size_t)n<capacity;
}
static int emit_module(Linker *l,size_t index) {
    Module *m=&l->modules[index];
    const char *p=m->source;
    unsigned line=0;
    if(index&&!append(l,".ALIGN #2\n",10,index,1)) return 0;
    if(strlen(p)>=3&&(unsigned char)p[0]==0xEF&&(unsigned char)p[1]==0xBB&&(unsigned char)p[2]==0xBF) p+=3;
    while(*p) {
        const char *end=strchr(p,'\n'),*cursor=p;
        char first[LC3_LABEL_SIZE];
        int quote=0,escape=0;
        ++line;if(!end) end=p+strlen(p);
        if(!token_word(&cursor,end,first,sizeof first)) return link_error(l,m->path,line,"Token demasiado largo.");
        if(same(first,".EXTERNAL")||same(first,".END")) {p=*end?end+1:end;continue;}
        cursor=p;
        while(cursor<end) {
            char ch=*cursor;
            if(quote) {
                if(!append(l,cursor,1,index,line)) return 0;
                if(escape) escape=0;
                else if(ch=='\\') escape=1;
                else if(ch=='"') quote=0;
                ++cursor;
            } else if(ch=='"') {
                quote=1;if(!append(l,cursor++,1,index,line)) return 0;
            } else if(ch==';') {
                if(!append(l,cursor,(size_t)(end-cursor),index,line)) return 0;
                cursor=end;
            } else if(isalpha((unsigned char)ch)||ch=='_'||ch=='.'||ch=='#'||isdigit((unsigned char)ch)||ch=='-'||ch=='+') {
                const char *start=cursor;
                char word[LC3_LABEL_SIZE],converted[LC3_LABEL_SIZE];
                long number;
                size_t n;
                while(cursor<end&&!isspace((unsigned char)*cursor)&&*cursor!=','&&*cursor!=':'&&*cursor!=';') ++cursor;
                n=(size_t)(cursor-start);
                if(n>=sizeof word) return link_error(l,m->path,line,"Simbolo demasiado largo.");
                memcpy(word,start,n);word[n]=0;
                if(lc3_is_operation(word)||lc3_number(word,&number)||(toupper((unsigned char)word[0])=='R'&&word[1]>='0'&&word[1]<='7'&&!word[2])) {
                    if(!append(l,word,n,index,line)) return 0;
                } else {
                    Import *import=NULL;
                    for(size_t i=0;i<m->import_count;++i) if(same(word,m->imports[i].token)) {import=&m->imports[i];break;}
                    if(strchr(word,'-')&&!import) return link_error(l,m->path,line,"Simbolo externo usado sin .EXTERNAL.");
                    if(!symbol_name(converted,sizeof converted,import?import->module:index,import?import->symbol:word)) return link_error(l,m->path,line,"Nombre enlazado demasiado largo.");
                    if(!append(l,converted,strlen(converted),index,line)) return 0;
                }
            } else if(!append(l,cursor++,1,index,line)) return 0;
        }
        if(!append(l,"\n",1,index,line)) return 0;
        p=*end?end+1:end;
    }
    return 1;
}
int lc3_assemble_project(const char *source,const char *path,const char *const *directories,size_t count,Lc3Image *out,AsmError *error) {
    Linker *l=calloc(1,sizeof *l);
    size_t main_index=0;
    int ok=0;
    memset(out,0,sizeof *out);if(error) memset(error,0,sizeof *error);
    if(!l) return 0;
    l->directories=directories;l->directory_count=count;l->error=error;l->main_source=source;
    if(!load_module(l,path,&main_index)) goto done;
    l->combined=calloc(LC3_MAX_SOURCE+1u,1);
    l->source_lines=calloc(LC3_MAX_SOURCE+1u,sizeof(unsigned));
    l->source_modules=calloc(LC3_MAX_SOURCE+1u,sizeof(size_t));
    if(!l->combined||!l->source_lines||!l->source_modules) {link_error(l,path,0,"Sin memoria para enlazar.");goto done;}
    for(size_t i=0;i<l->count;++i) if(!emit_module(l,i)) goto done;
    if(!append(l,".END\n",5,0,1)) goto done;
    if(!lc3_assemble(l->combined,out,error)) {
        if(error&&error->line&&error->line<=l->line_count) {
            size_t at=error->line-1u;Module *m=&l->modules[l->source_modules[at]];
            error->line=l->source_lines[at];snprintf(error->path,sizeof error->path,"%s",m->path);
        }
        goto done;
    }
    for(size_t i=0;i<l->count;++i) for(size_t j=0;j<l->modules[i].import_count;++j) {
        Import *import=&l->modules[i].imports[j];char name[LC3_LABEL_SIZE];uint16_t address;
        if(!symbol_name(name,sizeof name,import->module,import->symbol)||!lc3_symbol(out,name,&address)) {
            lc3_image_free(out);link_error(l,l->modules[i].path,import->line,"El modulo no exporta el simbolo solicitado.");goto done;
        }
    }
    ok=1;
done:
    for(size_t i=0;i<l->count;++i) free(l->modules[i].source);
    free(l->combined);free(l->source_lines);free(l->source_modules);free(l);return ok;
}
int lc3_assemble_file(const char *path,const char *const *directories,size_t count,Lc3Image *out,AsmError *error) {
    return lc3_assemble_project(NULL,path,directories,count,out,error);
}
