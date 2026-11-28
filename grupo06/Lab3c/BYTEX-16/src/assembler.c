#include "assembler.h"
#include "isa.h"
#include <ctype.h>
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define LINE_SIZE 8192u
#define HASH_SIZE 8192u
typedef enum { WORD, STRING, COMMA, COLON } TokenKind;
typedef struct { char *text; size_t length; TokenKind kind; } Token;
typedef struct {
    char buffer[LINE_SIZE];
    Token tokens[12];
    unsigned count, line;
    char *label, *op;
    Token args[8];
    unsigned argc;
} Row;
typedef struct {
    Lc3Image image;
    int hash[HASH_SIZE];
    AsmError *error;
} Assembly;

static int fail(AsmError *error, unsigned line, const char *format, ...) {
    if (error) {
        va_list args;
        error->line = line;
        va_start(args, format);
        vsnprintf(error->text, sizeof error->text, format, args);
        va_end(args);
    }
    return 0;
}
static int same(const char *a, const char *b) {
    while (*a && *b) {
        if (toupper((unsigned char)*a++) != toupper((unsigned char)*b++)) return 0;
    }
    return *a == *b;
}
int lc3_number(const char *text, long *value) {
    const char *p = text;
    char *end;
    int base = 10, sign = 1;
    long result;
    if (*p == '#') ++p;
    if (*p == '-') { sign = -1; ++p; }
    else if (*p == '+') ++p;
    if (*p == 'x' || *p == 'X') { base = 16; ++p; }
    else if (p[0] == '0' && (p[1] == 'x' || p[1] == 'X')) { base = 16; p += 2; }
    else if (*p == 'b' || *p == 'B') { base = 2; ++p; }
    if (!*p || !isxdigit((unsigned char)*p)) return 0;
    errno = 0;
    result = strtol(p, &end, base);
    if (errno || *end || result < 0) return 0;
    *value = result * sign;
    return 1;
}
static int branch(const char *op) {
    unsigned mask = 0;
    const char *p;
    if (toupper((unsigned char)op[0]) != 'B' || toupper((unsigned char)op[1]) != 'R') return -1;
    if (!op[2]) return 7;
    for (p = op + 2; *p; ++p) {
        unsigned bit;
        switch (toupper((unsigned char)*p)) {
            case 'N': bit = 4; break;
            case 'Z': bit = 2; break;
            case 'P': bit = 1; break;
            default: return -1;
        }
        if (mask & bit) return -1;
        mask |= bit;
    }
    return (int)mask;
}
static int operation(const char *op) {
    static const char *const ops[] = {
        "ADD", "AND", "NOT", "LD", "LDI", "LDR", "LEA", "ST", "STI", "STR",
        "JMP", "JSR", "JSRR", "RET", "RTI", "TRAP", "GETC", "OUT", "PUTS", "IN",
        "PUTSP", "HALT", "NOP", "BRL", "SHL", "SHR", "SAR", "ASR", "SUB", "MUL", "MULU", "DIVU", "CLZ", "MOV", "LDBL", "LDBH", "STBL", "STBH", "LDBS",
        ".ORIG", ".END", ".FILL", ".BLKW", ".STRINGZ", ".BYTE", ".BLKB", ".ALIGN", ".EXTERNAL"
    };
    size_t i;
    if (branch(op) >= 0) return 1;
    for (i = 0; i < sizeof ops / sizeof ops[0]; ++i) if (same(op, ops[i])) return 1;
    return 0;
}
static int label_valid(const char *name) {
    const char *p = name;
    long n;
    if (!isalpha((unsigned char)*p) && *p != '_') return 0;
    for (++p; *p; ++p) if (!isalnum((unsigned char)*p) && *p != '_') return 0;
    if (strlen(name) >= LC3_LABEL_SIZE || operation(name) || lc3_number(name, &n)) return 0;
    return !(toupper((unsigned char)name[0]) == 'R' && name[1] >= '0' && name[1] <= '7' && !name[2]);
}
static int scan(Row *row, const char *start, size_t length, AsmError *error) {
    char *p;
    unsigned i = 0;
    row->count = row->argc = 0;
    row->op = row->label = NULL;
    if (length >= LINE_SIZE) return fail(error, row->line, "Linea demasiado larga (maximo %u bytes).", LINE_SIZE - 1);
    memcpy(row->buffer, start, length);
    row->buffer[length] = 0;
    p = row->buffer;
    while (*p && *p != ';') {
        Token *token;
        char delimiter;
        if (isspace((unsigned char)*p)) { ++p; continue; }
        if (row->count == 12) return fail(error, row->line, "Demasiados tokens en la linea.");
        token = &row->tokens[row->count++];
        token->text = p;
        token->length = 1;
        if (*p == ',' || *p == ':') { token->kind = *p++ == ',' ? COMMA : COLON; continue; }
        if (*p == '"') {
            char *destination;
            token->kind = STRING;
            token->text = destination = ++p;
            while (*p && *p != '"') {
                unsigned char ch = (unsigned char)*p++;
                if (ch == '\\') {
                    switch (*p++) {
                        case 'n': ch = '\n'; break;
                        case 'r': ch = '\r'; break;
                        case 't': ch = '\t'; break;
                        case '0': ch = 0; break;
                        case '\\': ch = '\\'; break;
                        case '"': ch = '"'; break;
                        default: return fail(error, row->line, "Escape de cadena no valido.");
                    }
                }
                *destination++ = (char)ch;
            }
            if (*p != '"') return fail(error, row->line, "Cadena sin comillas de cierre.");
            ++p;
            if (*p && !isspace((unsigned char)*p) && *p != ';' && *p != ',')
                return fail(error, row->line, "Falta separador despues de la cadena.");
            token->length = (size_t)(destination - token->text);
            *destination = 0;
            continue;
        }
        token->kind = WORD;
        while (*p && !isspace((unsigned char)*p) && *p != ',' && *p != ':' && *p != ';') ++p;
        token->length = (size_t)(p - token->text);
        delimiter = *p;
        if (*p) *p++ = 0;
        if (delimiter == ';') break;
        if (delimiter == ',' || delimiter == ':') {
            if (row->count == 12) return fail(error, row->line, "Demasiados tokens.");
            row->tokens[row->count++] = (Token){NULL, 1, delimiter == ',' ? COMMA : COLON};
        }
    }
    if (!row->count) return 1;
    if (row->tokens[0].kind != WORD) return fail(error, row->line, "Se esperaba etiqueta o instruccion.");
    if (!operation(row->tokens[0].text)) {
        row->label = row->tokens[0].text;
        if (!label_valid(row->label)) return fail(error, row->line, "Etiqueta o instruccion no valida: %s", row->label);
        i = 1;
        if (i < row->count && row->tokens[i].kind == COLON) ++i;
    }
    if (i == row->count) return 1;
    if (row->tokens[i].kind != WORD || !operation(row->tokens[i].text))
        return fail(error, row->line, "Instruccion o directiva desconocida.");
    row->op = row->tokens[i++].text;
    for (; i < row->count; ++i) {
        if (row->tokens[i].kind == COMMA) {
            if (!row->argc || i + 1 == row->count || row->tokens[i - 1].kind == COMMA)
                return fail(error, row->line, "Coma sin operando.");
            continue;
        }
        if (row->tokens[i].kind == COLON || row->argc == 8) return fail(error, row->line, "Operandos no validos.");
        row->args[row->argc++] = row->tokens[i];
    }
    return 1;
}
static unsigned hash_name(const char *name) {
    unsigned h = 2166136261u;
    while (*name) h = (h ^ (unsigned)toupper((unsigned char)*name++)) * 16777619u;
    return h & (HASH_SIZE - 1u);
}
static int find_symbol(Assembly *assembly, const char *name) {
    unsigned h = hash_name(name);
    while (assembly->hash[h]) {
        int index = assembly->hash[h] - 1;
        if (same(assembly->image.symbols[index].name, name)) return index;
        h = (h + 1u) & (HASH_SIZE - 1u);
    }
    return -1;
}
static int add_symbol(Assembly *assembly, Row *row, size_t address) {
    unsigned h;
    Lc3Symbol *symbol;
    if (address > 65535u) return fail(assembly->error, row->line, "Etiqueta fuera de memoria.");
    if (find_symbol(assembly, row->label) >= 0) return fail(assembly->error, row->line, "Etiqueta duplicada: %s", row->label);
    if (assembly->image.symbol_count == LC3_MAX_SYMBOLS) return fail(assembly->error, row->line, "Demasiadas etiquetas.");
    h = hash_name(row->label);
    while (assembly->hash[h]) h = (h + 1u) & (HASH_SIZE - 1u);
    assembly->hash[h] = (int)assembly->image.symbol_count + 1;
    symbol = &assembly->image.symbols[assembly->image.symbol_count++];
    strcpy(symbol->name, row->label);
    symbol->address = (uint16_t)address;
    return 1;
}
static int arity(Assembly *assembly, Row *row, unsigned n) {
    if (row->argc != n) return fail(assembly->error, row->line, "%s requiere %u operando(s); se recibieron %u.", row->op, n, row->argc);
    return 1;
}
static int value(Assembly *assembly, Row *row, unsigned i, long *n, int labels) {
    int index;
    if (row->args[i].kind != WORD) return fail(assembly->error, row->line, "Se esperaba un numero o etiqueta.");
    if (lc3_number(row->args[i].text, n)) return 1;
    index = labels ? find_symbol(assembly, row->args[i].text) : -1;
    if (index >= 0) { *n = assembly->image.symbols[index].address; return 1; }
    return fail(assembly->error, row->line, "Numero no valido o etiqueta no definida: %s", row->args[i].text);
}
static int reg(Assembly *assembly, Row *row, unsigned i, unsigned *n) {
    const char *p = row->args[i].text;
    if (row->args[i].kind != WORD || toupper((unsigned char)p[0]) != 'R' || p[1] < '0' || p[1] > '7' || p[2])
        return fail(assembly->error, row->line, "Se esperaba un registro R0..R7.");
    *n = (unsigned)(p[1] - '0');
    return 1;
}
static int offset(Assembly *assembly, Row *row, unsigned i, unsigned bits, uint16_t pc, int labels, unsigned *out) {
    long n;
    long half = 1L << (bits - 1u);
    if (!value(assembly, row, i, &n, labels)) return 0;
    if (labels && !lc3_number(row->args[i].text, &n)) {
        int symbol = find_symbol(assembly, row->args[i].text);
        unsigned difference = (unsigned)(uint16_t)(assembly->image.symbols[symbol].address - (uint16_t)(pc + 2u));
        n = difference >= 32768u ? (long)difference - 65536L : (long)difference;
        if (n % 2) return fail(assembly->error, row->line, "Destino de palabra no alineado.");
        n /= 2;
    }
    if (n < -half || n >= half) return fail(assembly->error, row->line, "Operando fuera de rango de %u bits (%ld..%ld).", bits, -half, half - 1);
    *out = (unsigned)n & ((1u << bits) - 1u);
    return 1;
}

static int encode(Assembly *a, Row *row, uint16_t pc, uint16_t *word) {
    static const char *const traps[] = {"GETC","OUT","PUTS","IN","PUTSP","HALT"};
    unsigned d=0,s=0,t=0,imm=0,op;
    long n;
    int br=branch(row->op);
    for (unsigned i=0;i<6;++i) if(same(row->op,traps[i])) {
        if(!arity(a,row,0)) return 0;
        *word=(uint16_t)(OP_TRAP<<11u | (0x20u+i)); return 1;
    }
    if(same(row->op,".FILL")) {
        if(!arity(a,row,1)||!value(a,row,0,&n,1)) return 0;
        if(n < -32768 || n > 65535) return fail(a->error,row->line,".FILL fuera de 16 bits.");
        *word=(uint16_t)n; return 1;
    }
    if(same(row->op,"NOP")) {
        if(!arity(a,row,0)) return 0;
        *word=0; return 1;
    }
    if(same(row->op,"RET")||same(row->op,"RTI")) {
        if(!arity(a,row,0)) return 0;
        *word=(uint16_t)(same(row->op,"RET") ? (OP_JMP<<11u | 7u<<5u) : OP_RTI<<11u); return 1;
    }
    if(same(row->op,"TRAP")) {
        if(!arity(a,row,1)||!value(a,row,0,&n,0)) return 0;
        if(n<0||n>255) return fail(a->error,row->line,"Vector TRAP fuera de 0..255.");
        *word=(uint16_t)(OP_TRAP<<11u | (unsigned)n); return 1;
    }
    if(br>=0||same(row->op,"BRL")||same(row->op,"JSR")) {
        unsigned bits=(br>=0 && br!=7)?8u:11u;
        if(!arity(a,row,1)||!offset(a,row,0,bits,pc,1,&imm)) return 0;
        op=same(row->op,"JSR")?OP_JSR:OP_BRL;
        *word=br>=0 && br!=7 ? (uint16_t)((unsigned)br<<8u|imm) : (uint16_t)(op<<11u|imm);
        return 1;
    }
    if(same(row->op,"JMP")||same(row->op,"JSRR")) {
        if(!arity(a,row,1)||!reg(a,row,0,&s)) return 0;
        *word=(uint16_t)((unsigned)(same(row->op,"JMP")?OP_JMP:OP_JSRR)<<11u|s<<5u); return 1;
    }
    if(same(row->op,"ADD")||same(row->op,"AND")) {
        if(!arity(a,row,3)||!reg(a,row,0,&d)||!reg(a,row,1,&s)) return 0;
        op=same(row->op,"ADD")?OP_ADD:OP_AND;
        if(row->args[2].kind==WORD && toupper((unsigned char)row->args[2].text[0])=='R') {
            if(!reg(a,row,2,&t)) return 0;
        } else {
            if(!offset(a,row,2,5,pc,0,&t)) return 0;
            ++op;
        }
        *word=(uint16_t)(op<<11u|d<<8u|s<<5u|t); return 1;
    }
    if(same(row->op,"SUB")||same(row->op,"MUL")||same(row->op,"MULU")||
       same(row->op,"DIVU")||same(row->op,"CLZ")||same(row->op,"MOV")) {
        int unary=same(row->op,"CLZ")||same(row->op,"MOV");
        unsigned fn;
        if(!arity(a,row,unary?2u:3u)||!reg(a,row,0,&d)||!reg(a,row,1,&s))return 0;
        if(!unary&&!reg(a,row,2,&t))return 0;
        if(same(row->op,"SUB")||same(row->op,"MUL")||same(row->op,"MULU")) {
            op=OP_ADD;fn=same(row->op,"SUB")?FN_SUB:same(row->op,"MUL")?FN_MUL:FN_MULU;
        } else {
            op=OP_AND;fn=same(row->op,"DIVU")?FN_DIVU:same(row->op,"CLZ")?FN_CLZ:FN_MOV;
        }
        *word=(uint16_t)(op<<11u|d<<8u|s<<5u|fn<<3u|t);return 1;
    }
    if(same(row->op,"SHL")||same(row->op,"SHR")||same(row->op,"SAR")||same(row->op,"ASR")) {
        if(!arity(a,row,3)||!reg(a,row,0,&d)||!reg(a,row,1,&s)||!reg(a,row,2,&t))return 0;
        unsigned mode=same(row->op,"SHL")?0u:same(row->op,"SHR")?1u:2u;
        *word=(uint16_t)(31u<<11u|d<<8u|s<<5u|mode<<3u|t);return 1;
    }
    if(same(row->op,"NOT")) {
        if(!arity(a,row,2)||!reg(a,row,0,&d)||!reg(a,row,1,&s)) return 0;
        *word=(uint16_t)(OP_NOT<<11u|d<<8u|s<<5u); return 1;
    }
    if(same(row->op,"LDR")||same(row->op,"STR")) {
        if(!arity(a,row,3)||!reg(a,row,0,&d)||!reg(a,row,1,&s)||!offset(a,row,2,6,pc,0,&imm)) return 0;
        op=same(row->op,"LDR")?OP_LDR:OP_STR;
        if(imm&32u) ++op;
        *word=(uint16_t)(op<<11u|d<<8u|s<<5u|(imm&31u)); return 1;
    }
    if(same(row->op,"LDBL")||same(row->op,"LDBH")||same(row->op,"STBL")||same(row->op,"STBH")||same(row->op,"LDBS")) {
        if(!arity(a,row,3)||!reg(a,row,0,&d)||!reg(a,row,1,&s)||!offset(a,row,2,5,pc,0,&imm)) return 0;
        op=same(row->op,"LDBL")?OP_LDBL:same(row->op,"LDBH")?OP_LDBH:same(row->op,"STBL")?OP_STBL:same(row->op,"STBH")?OP_STBH:OP_LDBS;
        *word=(uint16_t)(op<<11u|d<<8u|s<<5u|imm); return 1;
    }
    op=same(row->op,"LD")?OP_LD:same(row->op,"ST")?OP_ST:same(row->op,"LDI")?OP_LDI:same(row->op,"STI")?OP_STI:OP_LEA;
    if(!arity(a,row,2)||!reg(a,row,0,&d)||!offset(a,row,1,9,pc,1,&imm)) return 0;
    if(imm&256u) op=OP_LD_NEG+(op-OP_LD);
    *word=(uint16_t)(op<<11u|d<<8u|(imm&255u)); return 1;
}

static void put_word(Lc3Image *image,size_t index,uint16_t word) {
    image->bytes[index]=(uint8_t)(word>>8u);
    image->bytes[index+1u]=(uint8_t)word;
}

static int layout(Assembly *a,const char *source,unsigned char *far,int emit,int detect,int *changed) {
    Row row;
    const char *p=source;
    size_t pc=0,used=0;
    int origin_seen=0,end_seen=0;
    char pending[LC3_MAX_SYMBOLS][LC3_LABEL_SIZE];
    unsigned pending_count=0;
    row.line=0;
    if(strlen(p)>=3 && (unsigned char)p[0]==0xEF && (unsigned char)p[1]==0xBB && (unsigned char)p[2]==0xBF) p+=3;
    while(*p) {
        const char *end=strchr(p,'\n');
        size_t length=end?(size_t)(end-p):strlen(p),size=0,pad=0;
        long n=0;
        int data_byte=0,br;
        ++row.line;
        if(!scan(&row,p,length,a->error)) return 0;
        p+=length+(end?1u:0u);
        if(!row.op&&!row.label) continue;
        if(end_seen) return fail(a->error,row.line,"Hay codigo despues de .END.");
        if(row.op&&same(row.op,".ORIG")) {
            if(origin_seen||row.label||!arity(a,&row,1)||!value(a,&row,0,&n,0)) return fail(a->error,row.line,".ORIG debe aparecer una vez y sin etiqueta.");
            if(n<0||n>65535||(n&1)) return fail(a->error,row.line,"El origen debe ser par y estar dentro de memoria.");
            a->image.origin=(uint16_t)n; pc=(size_t)n; origin_seen=1; continue;
        }
        if(!origin_seen) return fail(a->error,row.line,"El primer enunciado debe ser .ORIG.");
        if(!row.op) {
            if(pending_count==LC3_MAX_SYMBOLS) return fail(a->error,row.line,"Demasiadas etiquetas pendientes.");
            strcpy(pending[pending_count++],row.label); continue;
        }
        if(same(row.op,".EXTERNAL")) return fail(a->error,row.line,"Use lc3_assemble_file o el ensamblador de archivos para .EXTERNAL.");
        if(same(row.op,".END")) {
            if(row.label||!arity(a,&row,0)) return fail(a->error,row.line,".END no admite operandos ni etiqueta.");
            end_seen=1;
        } else if(same(row.op,".ALIGN")) {
            if(!arity(a,&row,1)||!value(a,&row,0,&n,0)) return 0;
            if(n!=2) return fail(a->error,row.line,".ALIGN admite #2.");
            pad=pc&1u;
        } else if(same(row.op,".BYTE")||same(row.op,".BLKB")) {
            if(!arity(a,&row,1)||!value(a,&row,0,&n,same(row.op,".BYTE"))) return 0;
            data_byte=1;
            if(same(row.op,".BYTE")) {
                if(n < -128||n>255) return fail(a->error,row.line,".BYTE fuera de 8 bits.");
                size=1;
            } else {
                if(n<0||n>65536) return fail(a->error,row.line,".BLKB fuera de memoria.");
                size=(size_t)n;
            }
        } else {
            pad=pc&1u;
            if(same(row.op,".BLKW")) {
                if(!arity(a,&row,1)||!value(a,&row,0,&n,0)) return 0;
                if(n<0||n>32768) return fail(a->error,row.line,".BLKW requiere 0..32768 palabras.");
                size=(size_t)n*2u;
            } else if(same(row.op,".STRINGZ")) {
                if(!arity(a,&row,1)||row.args[0].kind!=STRING) return fail(a->error,row.line,".STRINGZ requiere una cadena.");
                size=(row.args[0].length+1u)*2u;
            } else size=far[row.line]?4u:2u;
        }
        if(pc+pad+size>65536u) return fail(a->error,row.line,"Programa fuera de la memoria de 65536 bytes.");
        pc+=pad; used+=pad;
        if(!emit&&!detect) {
            for(unsigned i=0;i<pending_count;++i) {
                char *saved=row.label; row.label=pending[i];
                if(!add_symbol(a,&row,pc)) return 0;
                row.label=saved;
            }
            if(row.label&&!add_symbol(a,&row,pc)) return 0;
        }
        pending_count=0;
        br=branch(row.op);
        if(detect && br>0 && br!=7 && !far[row.line] && row.argc==1 && !lc3_number(row.args[0].text,&n)) {
            int symbol=find_symbol(a,row.args[0].text);
            if(symbol>=0) {
                int displacement=(int)a->image.symbols[symbol].address-(int)pc-2;
                if(displacement%2) return fail(a->error,row.line,"Salto a direccion impar.");
                if(displacement/2 < -128 || displacement/2 > 127) { far[row.line]=1; *changed=1; }
            }
        }
        if(emit) {
            for(size_t j=0;j<size;++j) a->image.lines[used+j]=row.line;
            if(data_byte && same(row.op,".BYTE")) a->image.bytes[used]=(uint8_t)n;
            else if(same(row.op,".STRINGZ")) {
                for(size_t j=0;j<row.args[0].length;++j) put_word(&a->image,used+j*2u,(unsigned char)row.args[0].text[j]);
            } else if(size && !same(row.op,".BLKW")&&!same(row.op,".BLKB")) {
                uint16_t word;
                if(far[row.line]) {
                    unsigned imm;
                    put_word(&a->image,used,(uint16_t)((unsigned)(br^7)<<8u|1u));
                    if(!offset(a,&row,0,11,(uint16_t)(pc+2u),1,&imm)) return 0;
                    put_word(&a->image,used+2u,(uint16_t)(OP_BRL<<11u|imm));
                } else {
                    if(!encode(a,&row,(uint16_t)pc,&word)) return 0;
                    put_word(&a->image,used,word);
                }
            }
        }
        pc+=size; used+=size;
    }
    if(!origin_seen||!end_seen||!used) return fail(a->error,row.line,"Se requieren .ORIG, .END y datos o instrucciones.");
    if(pending_count) return fail(a->error,row.line,"Etiqueta sin dato ni instruccion al final.");
    if(!emit&&!detect) a->image.count=used;
    return 1;
}

int lc3_assemble(const char *source,Lc3Image *out,AsmError *error) {
    Assembly *a;
    unsigned char *far;
    size_t lines=2;
    int success=0,changed;
    memset(out,0,sizeof *out);
    if(error) memset(error,0,sizeof *error);
    if(!source||strlen(source)>LC3_MAX_SOURCE) return fail(error,0,"Fuente vacia o mayor que 1 MiB.");
    for(const char *p=source;*p;++p) if(*p=='\n') ++lines;
    a=calloc(1,sizeof *a); far=calloc(lines,1);
    if(!a||!far) {free(a);free(far);return fail(error,0,"Sin memoria.");}
    a->error=error; a->image.symbols=calloc(LC3_MAX_SYMBOLS,sizeof(Lc3Symbol));
    if(!a->image.symbols) goto done;
    do {
        changed=0;
        memset(a->hash,0,sizeof a->hash); a->image.symbol_count=0;
        if(!layout(a,source,far,0,0,&changed)||!layout(a,source,far,0,1,&changed)) goto done;
    } while(changed);
    a->image.bytes=calloc(a->image.count,1);
    a->image.lines=calloc(a->image.count,sizeof(unsigned));
    if(!a->image.bytes||!a->image.lines) {fail(error,0,"Sin memoria para imagen.");goto done;}
    if(!layout(a,source,far,1,0,&changed)) goto done;
    *out=a->image; memset(&a->image,0,sizeof a->image); success=1;
done:
    lc3_image_free(&a->image); free(a); free(far); return success;
}

int lc3_is_operation(const char *text) { return operation(text); }
