#include "lc3.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static Lc3 *m;
static unsigned long long checks,failures;
#define CHECK(x) do{++checks;if(!(x)){if(failures++<8)fprintf(stderr,"linea %d: %s\n",__LINE__,#x);}}while(0)
static void encoding(void) {
    const char *source=".ORIG x3000\nSUB R0,R1,R2\nMUL R0,R1,R2\nMULU R0,R1,R2\nDIVU R0,R1,R2\nCLZ R0,R1\nMOV R0,R1\nSHL R0,R1,R2\nSHR R0,R1,R2\nSAR R0,R1,R2\nASR R0,R1,R2\n.END";
    static const uint16_t words[]={0x082A,0x0832,0x083A,0x182A,0x1830,0x1838,0xF822,0xF82A,0xF832,0xF832};
    static const char *const names[]={"SUB R0,R1,R2","MUL R0,R1,R2","MULU R0,R1,R2","DIVU R0,R1,R2","CLZ R0,R1","MOV R0,R1","SHL R0,R1,R2","SHR R0,R1,R2","SAR R0,R1,R2","SAR R0,R1,R2"};
    Lc3Image image={0};AsmError e;CHECK(lc3_assemble(source,&image,&e));
    if(!image.bytes)return;
    CHECK(lc3_init(m,&image,&e));CHECK(image.count==20);
    for(unsigned i=0;i<10;++i){
        char line[80];CHECK(lc3_peek(m,(uint16_t)(0x3000+2*i))==words[i]);
        lc3_disassemble((uint16_t)(0x3000+2*i),words[i],line,sizeof line);CHECK(!strcmp(line,names[i]));
    }
    lc3_image_free(&image);
}
static uint16_t expected(unsigned op,uint16_t a,uint16_t b) {
    if(op==0)return (uint16_t)((uint32_t)a+65536u-b);
    if(op==1)return (uint16_t)(((uint64_t)a*b)%65536u);
    if(op==2)return (uint16_t)(((uint64_t)a*b)/65536u);
    if(op==3)return b?(uint16_t)(a/b):0;
    if(op==4){unsigned bits=0;for(unsigned v=a;v;v/=2u)++bits;return (uint16_t)(16u-bits);}
    return a;
}
static void one(unsigned op,uint16_t a,uint16_t b,unsigned destination) {
    static const uint16_t codes[]={0x082A,0x0832,0x083A,0x182A,0x1830,0x1838};
    uint16_t word=(uint16_t)(codes[op]|destination<<8u),want=expected(op,a,b);
    m->pc=0x3000;m->r[0]=0xBABE;m->r[1]=a;m->r[2]=b;m->r[7]=0xBEEF;
    uint64_t count=m->instructions,reads=m->memory_read_bytes,writes=m->memory_write_bytes;lc3_poke(m,0x3000,word);CHECK(lc3_step(m));
    CHECK(m->r[destination]==want);CHECK(m->instructions==count+1);CHECK(m->memory_read_bytes==reads+2&&m->memory_write_bytes==writes);CHECK(!m->last_exception);
    if(destination!=1)CHECK(m->r[1]==a);
    if(destination!=2)CHECK(m->r[2]==b);
    CHECK(m->r[7]==0xBEEF&&m->r[6]==0xFE00);
    CHECK((m->psr&7u)==(!want?2u:want>=32768?4u:1u));
}
static void arithmetic(void) {
    uint8_t bytes[2]={0,0};Lc3Image image={0};AsmError e;
    image.origin=0x3000;image.count=2;image.bytes=bytes;CHECK(lc3_init(m,&image,&e));
    for(unsigned a=0;a<65536;++a){one(4,(uint16_t)a,0,0);one(5,(uint16_t)a,0,0);}
    static const uint16_t edge[]={0,1,2,7,15,127,128,255,256,32767,32768,32769,65534,65535};
    for(unsigned op=0;op<6;++op)for(unsigned i=0;i<14;++i)for(unsigned j=0;j<14;++j)for(unsigned d=0;d<3;++d)one(op,edge[i],edge[j],d);
    uint32_t state=20261125u;
    for(unsigned i=0;i<100000;++i){
        state=state*1664525u+1013904223u;uint16_t a=(uint16_t)(state>>7u);
        state=state*1664525u+1013904223u;uint16_t b=(uint16_t)(state>>7u);
        for(unsigned op=0;op<4;++op)one(op,a,b,i%3);
    }
}
static void invalid(void) {
    const char *bad[]={"MUL R0,R1,#2","MOV R0,#15","CLZ R0,R1,R2","SUB R8,R0,R0","DIVU R0,R1"};
    for(unsigned i=0;i<5;++i){char source[160];Lc3Image image={0};AsmError e;
        snprintf(source,sizeof source,".ORIG x3000\n%s\n.END",bad[i]);CHECK(!lc3_assemble(source,&image,&e));}
    uint8_t bytes[2]={0x18,0x11};Lc3Image image={0};AsmError e;
    image.origin=0x3000;image.count=2;image.bytes=bytes;CHECK(lc3_init(m,&image,&e));
    lc3_step(m);CHECK(m->last_exception==0x101); /* CLZ con campo reservado no cero. */
}
int main(void){
    m=malloc(sizeof *m);if(!m)return 2;
    encoding();arithmetic();invalid();free(m);
    printf("ALU integrada: %llu comprobaciones, %llu fallos.\n",checks,failures);return failures?1:0;
}
