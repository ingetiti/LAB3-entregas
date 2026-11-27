#include "lc3.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks,failures;
static Lc3 *m;
static Lc3Image image;
static char output[4096];
static size_t output_count;
#define CHECK(x) do {++checks;if(!(x)){++failures;fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);}} while(0)
static void capture(void *context,unsigned char value) {
    (void)context;
    if(output_count+1<sizeof output) {output[output_count++]=(char)value;output[output_count]=0;}
}
static int boot(const char *source) {
    AsmError e;
    lc3_image_free(&image);
    if(!lc3_assemble(source,&image,&e)||!lc3_init(m,&image,&e)) {
        fprintf(stderr,"boot: %u %s\n",e.line,e.text);CHECK(0);return 0;
    }
    output_count=0;output[0]=0;m->output=capture;return 1;
}
static uint16_t label(const char *name) {
    uint16_t a=0;CHECK(lc3_symbol(&image,name,&a));return a;
}
static void steps(unsigned n) {while(n--) CHECK(lc3_step(m));}
static void finish(void) {
    unsigned n=100000;
    while((m->mcr&0x8000u)&&n) {--n;(void)lc3_step(m);}
    CHECK(n>0);CHECK(!(m->mcr&0x8000u));
}
static void encoding(void) {
    if(!boot(".ORIG x3000\nADD R0,R1,R2\nADD R3,R4,#-16\nAND R5,R6,#15\nNOT R7,R0\nJSRR R7\nRET\n.END")) return;
    static const unsigned words[]={0x0822,0x1390,0x25CF,0x2F00,0x80E0,0x88E0};
    CHECK(image.count==12);
    for(size_t i=0;i<6;++i) CHECK(lc3_peek(m,(uint16_t)(0x3000+2*i))==words[i]);
    CHECK(sizeof m->memory==65536);CHECK(m->pc==0x3000);CHECK(m->r[6]==0xFE00);
}
static void arithmetic(void) {
    if(!boot(".ORIG x3000\nADD R0,R0,#1\nAND R1,R0,#0\nNOT R2,R1\nLEA R3,#0\nADD R4,R2,R2\n.END")) return;
    m->r[0]=0x7FFF;
    steps(1);CHECK(m->r[0]==0x8000&&(m->psr&7)==4);CHECK(m->pc==0x3002);
    steps(1);CHECK(m->r[1]==0&&(m->psr&7)==2);
    steps(1);CHECK(m->r[2]==0xFFFF&&(m->psr&7)==4);
    steps(1);CHECK(m->r[3]==0x3008&&(m->psr&7)==4);
    steps(1);CHECK(m->r[4]==0xFFFE);CHECK(m->instructions==5);
}
static void branches_calls(void) {
    if(!boot(".ORIG x3000\nBRz SKIP\nADD R0,R0,#1\nSKIP JSR SUBR\nHALT\nSUBR ADD R0,R0,#5\nRET\n.END")) return;
    steps(1);CHECK(m->pc==label("SKIP"));
    steps(1);CHECK(m->r[7]==0x3006);CHECK(m->pc==label("SUBR"));
    steps(2);CHECK(m->pc==0x3006&&m->r[0]==5);
    finish();CHECK(!m->last_exception);
    if(!boot(".ORIG x3000\nJSRR R7\nJMP R1\nRET\n.END")) return;
    m->r[7]=0x3004;steps(1);CHECK(m->pc==0x3004&&m->r[7]==0x3002);
    steps(1);CHECK(m->pc==0x3002);
    m->r[1]=0x3000;steps(1);CHECK(m->pc==0x3000);
    if(!boot(".ORIG x3000\nBRz FAR\n.BLKW #200\nFAR HALT\n.END")) return;
    CHECK((lc3_peek(m,0x3000)>>11u)==OP_BR);
    CHECK((lc3_peek(m,0x3002)>>11u)==OP_BRL);
    steps(2);CHECK(m->pc==label("FAR"));finish();
    if(!boot(".ORIG x3000\nBR FAR\n.BYTE #1\nFAR HALT\n.END")) return;
    CHECK(label("FAR")==0x3004);CHECK(lc3_peek_byte(m,0x3003)==0);
}
static void loads_stores(void) {
    if(!boot(".ORIG x3000\nLD R0,DATA\nST R0,DEST\nLEA R1,DATA\nLDR R2,R1,#0\nSTR R2,R1,#1\nLDI R3,PTR\nSTI R3,PTR2\nHALT\nDATA .FILL xBEEF\nDEST .BLKW #1\nPTR .FILL DATA\nPTR2 .FILL DEST\n.END")) return;
    steps(7);CHECK(m->r[0]==0xBEEF);CHECK(m->r[2]==0xBEEF);CHECK(m->r[3]==0xBEEF);
    CHECK(lc3_peek(m,label("DEST"))==0xBEEF);
    CHECK(lc3_peek_byte(m,label("DATA"))==0xBE);
    CHECK(lc3_peek_byte(m,(uint16_t)(label("DATA")+1))==0xEF);
    finish();
    if(!boot(".ORIG x3000\nLDR R0,R1,#-32\nSTR R0,R1,#31\n.END")) return;
    m->r[1]=0x3100;lc3_poke(m,0x30C0,0xABCD);steps(2);
    CHECK(m->r[0]==0xABCD&&lc3_peek(m,0x313E)==0xABCD);
}
static void bytes(void) {
    if(!boot(".ORIG x3000\nLDBL R0,R1,#0\nLDBH R0,R1,#1\nLDBS R2,R1,#2\nSTBL R0,R1,#3\nSTBH R0,R1,#4\nHALT\n.END")) return;
    m->r[0]=0x1234;m->r[1]=0x3100;
    lc3_poke_byte(m,0x3100,0xAB);lc3_poke_byte(m,0x3101,0xCD);lc3_poke_byte(m,0x3102,0x80);
    steps(1);CHECK(m->r[0]==0x12AB);
    steps(1);CHECK(m->r[0]==0xCDAB);
    steps(1);CHECK(m->r[2]==0xFF80&&(m->psr&7)==4);
    steps(2);CHECK(lc3_peek_byte(m,0x3103)==0xAB);CHECK(lc3_peek_byte(m,0x3104)==0xCD);
    CHECK(lc3_peek_byte(m,0x3102)==0x80);CHECK(lc3_peek_byte(m,0x3105)==0);
    CHECK(m->written_bytes==2);finish();
    if(!boot(".ORIG x3000\nLDBS R0,R1,#0\n.END")) return;
    m->r[1]=0x3101;
    for(unsigned n=0;n<256;++n) {
        m->pc=0x3000;lc3_poke_byte(m,0x3101,(uint8_t)n);steps(1);
        CHECK(m->r[0]==(uint16_t)(n<128?(int)n:(int)n-256));
    }
}
static void traps_interrupts(void) {
    if(!boot(".ORIG x3000\nLEA R0,TEXT\nPUTS\nLEA R0,PACKED\nPUTSP\nHALT\nTEXT .STRINGZ \"hola!\"\nPACKED .FILL x4241\n.FILL x0043\n.FILL #0\n.END")) return;
    m->r[7]=0xBEEF;finish();CHECK(!strcmp(output,"hola!ABC\nHALT\n"));CHECK(m->r[7]==0xBEEF);
    if(!boot(".ORIG x3000\nGETC\nOUT\nHALT\n.END")) return;
    CHECK(lc3_key(m,'Z'));finish();CHECK(!strcmp(output,"Z\nHALT\n"));
    if(!boot(".ORIG x3000\nTRAP x40\nHALT\nHAND ADD R0,R0,#1\nRTI\n.END")) return;
    lc3_poke(m,0x80,label("HAND"));steps(1);
    CHECK(m->r[6]==0x2FFC);CHECK(lc3_peek(m,0x2FFC)==0x3002);CHECK(lc3_peek(m,0x2FFE)==0x8002);
    steps(2);CHECK(m->pc==0x3002&&m->r[6]==0xFE00);CHECK(m->r[0]==1);
    if(!boot(".ORIG x3000\nBR #-1\n.END")) return;
    lc3_poke(m,LC3_KBSR,0x4000);CHECK(lc3_key(m,'K'));steps(1);
    CHECK(m->interrupts==1&&m->instructions==0);CHECK(m->pc==lc3_peek(m,0x300));
    for(unsigned i=0;i<10000&&!(m->psr&0x8000u);++i) (void)lc3_step(m);
    CHECK(m->pc==0x3000&&m->r[6]==0xFE00);CHECK(!strcmp(output,"K"));
}
static void faults(void) {
    static const char *const programs[]={
        ".ORIG x3000\nRTI\n.END",
        ".ORIG x3000\n.FILL xF818\n.END",
        ".ORIG x3000\nLDR R0,R1,#0\n.END",
        ".ORIG x3000\nJMP R1\n.END",
        ".ORIG x3000\nLDR R0,R1,#0\n.END"
    };
    static const unsigned codes[]={0x100,0x101,0x103,0x103,0x102};
    for(size_t i=0;i<5;++i) {
        if(!boot(programs[i])) continue;
        m->r[1]=i==4?0x2000:0x3101;steps(1);
        CHECK(m->exception==codes[i]);CHECK(m->last_exception==codes[i]);
        finish();CHECK(strstr(output,"exception")!=NULL);
    }
}
static void errors(void) {
    static const char *const invalid[]={
        ".ORIG x3001\nHALT\n.END",
        ".ORIG x3000\nADD R0,R0,#16\n.END",
        ".ORIG x3000\nLDR R0,R0,#32\n.END",
        ".ORIG x3000\nBRz #128\n.END",
        ".ORIG x3000\nADD R8,R0,#0\n.END",
        ".ORIG x3000\n.BYTE #256\n.END",
        ".ORIG x3000\n.BYTE #-129\n.END",
        ".ORIG x3000\n.FILL x10000\n.END",
        ".ORIG x3000\nJSR MISSING\n.END",
        ".ORIG xFFFE\n.BLKW #2\n.END",
        ".ORIG x3000\nA HALT\nA HALT\n.END",
        ".ORIG x3000\nHALT\n.END\nHALT",
        ".ORIG x3000\n.STRINGZ \"bad\\q\"\n.END",
        ".ORIG x3000\nHALT",
        "HALT\n.END"
    };
    for(size_t i=0;i<sizeof invalid/sizeof invalid[0];++i) {
        Lc3Image bad;AsmError e;
        CHECK(!lc3_assemble(invalid[i],&bad,&e));CHECK(*e.text);CHECK(!bad.bytes&&!bad.symbols);
    }
}
static void objects(void) {
    Lc3Image other;AsmError e;
    if(!boot(".ORIG x3000\nHALT\n.BYTE #1\n.END")) return;
    CHECK(lc3_object_write("test-roundtrip.tmp.obj",&image,&e));
    CHECK(lc3_object_read("test-roundtrip.tmp.obj",&other,&e));
    CHECK(other.origin==0x3000&&other.count==3);CHECK(!memcmp(other.bytes,image.bytes,3));
    lc3_image_free(&other);CHECK(remove("test-roundtrip.tmp.obj")==0);
}
static void modules(void) {
    Lc3Image linked;AsmError e;uint16_t address;
    CHECK(lc3_assemble_file("tests/modulos/main.asm",NULL,0,&linked,&e));
    if(!linked.bytes) {fprintf(stderr,"module: %s %u %s\n",e.path,e.line,e.text);return;}
    CHECK(lc3_init(m,&linked,&e));m->output=capture;finish();
    CHECK(lc3_symbol(&linked,"RESULTADO",&address));CHECK(lc3_peek(m,address)==12);
    lc3_image_free(&linked);
    CHECK(!lc3_assemble_file("tests/modulos/missing.asm",NULL,0,&linked,&e));CHECK(*e.path&&e.line);
    CHECK(!lc3_assemble_file("tests/modulos/noexport.asm",NULL,0,&linked,&e));
}
static void opcode_catalog(void) {
    const char *source=".ORIG x3000\nNOP\nADD R0,R0,R0\nADD R0,R0,#0\nAND R0,R0,R0\nAND R0,R0,#0\nNOT R0,R0\n"
        "LD R0,#0\nST R0,#0\nLDI R0,#0\nSTI R0,#0\nLEA R0,#0\nLDR R0,R0,#0\nLDR R0,R0,#-1\nSTR R0,R0,#0\nSTR R0,R0,#-1\n"
        "JSR #0\nJSRR R0\nJMP R0\nRTI\nTRAP x00\nLDBL R0,R0,#0\nLDBH R0,R0,#0\nSTBL R0,R0,#0\nSTBH R0,R0,#0\nLDBS R0,R0,#0\n"
        "LD R0,#-1\nST R0,#-1\nLDI R0,#-1\nSTI R0,#-1\nLEA R0,#-1\nBRL #0\n.END";
    /* Tabla hexadecimal independiente de los enums y del codificador. */
    static const uint16_t expected[]={0x0000,0x0800,0x1000,0x1800,0x2000,0x2800,0x3000,0x3800,0x4000,0x4800,0x5000,
        0x5800,0x601F,0x6800,0x701F,0x7800,0x8000,0x8800,0x9000,0x9800,0xA000,0xA800,0xB000,0xB800,0xC000,
        0xC8FF,0xD0FF,0xD8FF,0xE0FF,0xE8FF,0xF000};
    if(!boot(source))return;
    CHECK(image.count==sizeof expected);
    for(size_t i=0;i<sizeof expected/sizeof expected[0];++i)CHECK(lc3_peek(m,(uint16_t)(0x3000+2*i))==expected[i]);
    if(!boot(".ORIG x3000\nBR START\nDATA .FILL xBEEF\nPTR .FILL DATA\nDEST .FILL #0\nSTART LD R0,DATA\nST R0,DEST\nLDI R1,PTR\nSTI R1,PTR\nLEA R2,DATA\nHALT\n.END"))return;
    steps(6);CHECK(m->r[0]==0xBEEF&&m->r[1]==0xBEEF);CHECK(m->r[2]==label("DATA"));CHECK(lc3_peek(m,label("DEST"))==0xBEEF);
    if(!boot(".ORIG x3000\nNOP\n.END"))return;
    m->strict_access=0;m->pc=0xFFFE;m->r[0]=0x3000;
    steps(1);CHECK(m->r[7]==0&&m->pc==0x3000); /* PC+2 envuelve a cero. */
}
static void isolated_modules(void) {
    Lc3Image linked;AsmError e;uint16_t address=0;
    CHECK(lc3_assemble_file("tests/modulos/aislados.asm",NULL,0,&linked,&e));
    if(!linked.bytes){fprintf(stderr,"%s: %s\n",e.path,e.text);return;}
    CHECK(lc3_init(m,&linked,&e));m->output=capture;finish();CHECK(m->r[2]==12);
    CHECK(lc3_symbol(&linked,"TABLA",&address));
    CHECK(lc3_peek(m,address)==lc3_peek(m,(uint16_t)(address+2)));
    lc3_image_free(&linked);
}
int main(void) {
    m=calloc(1,sizeof *m);if(!m) return 1;
    encoding();arithmetic();branches_calls();loads_stores();bytes();traps_interrupts();faults();errors();objects();modules();opcode_catalog();isolated_modules();
    lc3_image_free(&image);lc3_os_free();free(m);
    printf("%u checks, %u failures\n",checks,failures);return failures?1:0;
}
