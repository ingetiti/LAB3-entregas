#include "lc3.h"
#include <stdio.h>
#include <string.h>

static int signed_bits(uint16_t word, unsigned bits) {
    unsigned value = word & ((1u << bits) - 1u);
    return (value & (1u << (bits - 1u))) ? (int)value - (int)(1u << bits) : (int)value;
}
static void set_cc(Lc3 *m, uint16_t value) {
    m->psr = (uint16_t)((m->psr & 0xFFF8u) | (!value ? 2u : value & 0x8000u ? 4u : 1u));
}
static void keyboard_refresh(Lc3 *m) {
    if (!(m->kbsr & 0x8000u) && m->input_count) {
        m->kbdr = m->input[m->input_start];
        m->input_start = (m->input_start + 1u) % LC3_INPUT_SIZE;
        --m->input_count;
        m->kbsr |= 0x8000u;
    }
}
int lc3_key(Lc3 *m, unsigned char ch) {
    if (m->input_count == LC3_INPUT_SIZE) return 0;
    m->input[(m->input_start + m->input_count) % LC3_INPUT_SIZE] = ch;
    ++m->input_count;
    return 1;
}
uint16_t lc3_peek(const Lc3 *m, uint16_t address) {
    if (address & 1u) return 0;
    switch (address) {
        case LC3_KBSR: return m->kbsr;
        case LC3_KBDR: return m->kbdr;
        case LC3_DSR: return 0x8000u;
        case LC3_DDR: return m->ddr;
        case LC3_PSR: return m->psr;
        case LC3_MCR: return m->mcr;
        default: return (uint16_t)((unsigned)m->memory[address] << 8u | m->memory[address + 1u]);
    }
}
void lc3_poke(Lc3 *m, uint16_t address, uint16_t value) {
    if (address & 1u) return;
    switch (address) {
        case LC3_KBSR: m->kbsr = (uint16_t)((m->kbsr & 0x8000u) | (value & 0x4000u)); break;
        case LC3_KBDR: case LC3_DSR: break;
        case LC3_DDR:
            m->ddr = (uint16_t)(value & 255u);
            if (m->output) m->output(m->output_context, (unsigned char)value);
            break;
        case LC3_PSR: m->psr = value; break;
        case LC3_MCR: m->mcr = value; break;
        default: m->memory[address] = (uint8_t)(value >> 8u); m->memory[address + 1u] = (uint8_t)value; break;
    }
}

uint8_t lc3_peek_byte(const Lc3 *m,uint16_t address) {
    uint16_t word=lc3_peek(m,(uint16_t)(address&0xFFFEu));
    return (uint8_t)(address&1u?word:word>>8u);
}
void lc3_poke_byte(Lc3 *m,uint16_t address,uint8_t value) {
    uint16_t aligned=(uint16_t)(address&0xFFFEu);
    uint16_t word=lc3_peek(m,aligned);
    word=address&1u?(uint16_t)((word&0xFF00u)|value):(uint16_t)((word&255u)|(unsigned)value<<8u);
    lc3_poke(m,aligned,word);
}
static void touch(Lc3 *m,uint16_t address,int write) {
    if(write)++m->memory_write_bytes;else ++m->memory_read_bytes;
    if(!m->accessed[address]) ++m->accessed_bytes;
    if(write && !(m->accessed[address]&2u)) ++m->written_bytes;
    m->accessed[address]|=(uint8_t)(write?3u:1u);
}
static void raw_write(Lc3 *m,uint16_t address,uint16_t value) {
    touch(m,address,1);touch(m,(uint16_t)(address+1u),1);
    lc3_poke(m,address,value);
}

static uint16_t raw_read(Lc3 *m, uint16_t address) {
    uint16_t value = lc3_peek(m, address);
    if(address==LC3_KBSR && !(value&0x8000u))m->waiting_for_input=1;
    touch(m,address,0);touch(m,(uint16_t)(address+1u),0);
    if (address == LC3_KBDR) m->kbsr &= 0x7FFFu;
    return value;
}
static void supervisor(Lc3 *m, uint16_t vector, uint16_t return_pc, int priority) {
    uint16_t old_psr = m->psr;
    if (vector >= 0x100u) m->last_exception = vector;
    if (old_psr & 0x8000u) { m->usp = m->r[6]; m->r[6] = m->ssp; }
    if ((m->r[6] & 1u) || m->r[6] < 4u) {
        m->exception=m->last_exception=0x103u; m->mcr&=0x7FFFu; return;
    }
    m->psr &= 0x7FFFu;
    if (priority >= 0) m->psr = (uint16_t)((m->psr & 0xF8FFu) | (unsigned)priority << 8u);
    m->r[6] = (uint16_t)(m->r[6] - 2u);
    raw_write(m, m->r[6], old_psr);
    m->r[6] = (uint16_t)(m->r[6] - 2u);
    raw_write(m, m->r[6], return_pc);
    m->pc = raw_read(m, (uint16_t)(vector * 2u));
}
static int permitted(Lc3 *m, uint16_t address, uint16_t instruction_pc) {
    if (address & 1u) {
        m->exception=0x103u; supervisor(m,0x103u,instruction_pc,-1); return 0;
    }
    if (m->strict_access && (m->psr & 0x8000u) && (address < 0x3000u || address >= 0xFE00u)) {
        m->exception = 0x102u;
        supervisor(m, 0x102u, instruction_pc, -1);
        return 0;
    }
    return 1;
}
int lc3_init(Lc3 *m, const Lc3Image *program, AsmError *error) {
    const Lc3Image *os = lc3_os_image(error);
    if (!os) return 0;
    if (program && (!program->bytes || !program->count || (program->origin & 1u) || (size_t)program->origin + program->count > LC3_WORDS)) {
        if (error) { error->line = 0; strcpy(error->text, "Imagen de programa no valida."); }
        return 0;
    }
    memset(m, 0, sizeof *m);
    memcpy(m->memory + os->origin, os->bytes, os->count);
    if (program) {memcpy(m->memory + program->origin, program->bytes, program->count);m->program_bytes=program->count;}
    m->pc = program ? program->origin : 0x3000u;
    m->usp = 0xFE00u; m->ssp = 0x3000u;
    m->psr = m->pc >= 0x3000u && m->pc < 0xFE00u ? 0x8002u : 2u;
    m->r[6] = m->psr & 0x8000u ? m->usp : m->ssp;
    m->mcr = 0x8000u;
    m->strict_access = 1;
    return 1;
}
int lc3_step(Lc3 *m) {
    uint16_t instruction_pc = m->pc, word, a, b, address;
    unsigned d, s, t, op, raw_op;
    int pc_offset, base_offset;
    if (!(m->mcr & 0x8000u)) return 0;
    m->exception = 0;
    m->waiting_for_input=0;
    keyboard_refresh(m);
    if ((m->kbsr & 0xC000u) == 0xC000u && ((m->psr >> 8u) & 7u) < 4u) {
        supervisor(m, 0x180u, m->pc, 4);
        ++m->interrupts; return 1;
    }
    if (!permitted(m, m->pc, instruction_pc)) goto done;
    word = raw_read(m, m->pc);
    m->ir = word;
    m->pc = (uint16_t)(m->pc + 2u);
    ++m->instructions;
    {
        static const unsigned operations[32]={0,1,1,5,5,9,2,3,10,11,14,6,6,7,7,4,4,12,8,15,20,21,22,23,24,2,3,10,11,14,30,31};
        raw_op=word>>11u;op=operations[raw_op];
        d=word>>8u&7u;s=word>>5u&7u;t=word&7u;
        pc_offset=((int)(word&255u)-(raw_op>=OP_LD_NEG&&raw_op<=OP_LEA_NEG?256:0))*2;
        base_offset=((int)(word&31u)-(raw_op==OP_LDR_NEG||raw_op==OP_STR_NEG?32:0))*2;
    }
#define READ(dst, addr) do { address = (uint16_t)(addr); if (!permitted(m, address, instruction_pc)) goto done; (dst) = raw_read(m, address); } while (0)
#define WRITE(addr, val) do { address = (uint16_t)(addr); if (!permitted(m, address, instruction_pc)) goto done; raw_write(m, address, (uint16_t)(val)); } while (0)
    switch (op) {
        case 0:
            if (d & m->psr & 7u) m->pc = (uint16_t)(m->pc + 2 * signed_bits(word, 8));
            break;
        case 1: case 5: {
            unsigned fn=(word>>3u)&3u;
            a=m->r[s];
            b = (raw_op == OP_ADDI || raw_op == OP_ANDI) ? (uint16_t)signed_bits(word, 5) : m->r[t];
            if(raw_op==OP_ADD && fn) {
                if(fn==FN_SUB)a=(uint16_t)(a-b);
                else if(fn==FN_MUL)a=(uint16_t)((int32_t)signed_bits(a,16)*(int32_t)signed_bits(b,16));
                else a=(uint16_t)(((uint32_t)a*(uint32_t)b)>>16u);
            } else if(raw_op==OP_AND && fn) {
                if(fn==FN_DIVU)a=b?(uint16_t)(a/b):0;
                else {
                    if(t){m->exception=0x101u;supervisor(m,0x101u,instruction_pc,-1);break;}
                    if(fn==FN_CLZ) {
                        uint16_t scan=a;a=0;
                        while(a<16u && !(scan&0x8000u)){++a;scan=(uint16_t)(scan<<1u);}
                    } /* FN_MOV conserva el valor de a. */
                }
            } else a=op==1?(uint16_t)(a+b):(uint16_t)(a&b);
            m->r[d]=a;set_cc(m,a);break;
        }
        case 2:
            READ(a, m->pc + pc_offset); m->r[d] = a; set_cc(m, a); break;
        case 3:
            WRITE(m->pc + pc_offset, m->r[d]); break;
        case 4:
            a = raw_op == OP_JSR ? (uint16_t)(m->pc + 2 * signed_bits(word, 11)) : m->r[s];
            if (!permitted(m,a,instruction_pc)) break;
            m->r[7] = m->pc; m->pc = a; break;
        case 6:
            READ(a, m->r[s] + base_offset); m->r[d] = a; set_cc(m, a); break;
        case 7:
            WRITE(m->r[s] + base_offset, m->r[d]); break;
        case 8:
            if (m->psr & 0x8000u) {
                m->exception = 0x100u; supervisor(m, 0x100u, instruction_pc, -1); break;
            }
            if (m->r[6]&1u) {m->exception=0x103u;supervisor(m,0x103u,instruction_pc,-1);break;}
            a = raw_read(m, m->r[6]); m->r[6] = (uint16_t)(m->r[6] + 2u);
            b = raw_read(m, m->r[6]); m->r[6] = (uint16_t)(m->r[6] + 2u);
            if(a&1u) {m->exception=0x103u;supervisor(m,0x103u,instruction_pc,-1);break;}
            m->pc = a; m->psr = b;
            if (b & 0x8000u) { m->ssp = m->r[6]; m->r[6] = m->usp; }
            break;
        case 9:
            m->r[d] = (uint16_t)~m->r[s]; set_cc(m, m->r[d]); break;
        case 10:
            READ(a, m->pc + pc_offset); READ(b, a); m->r[d] = b; set_cc(m, b); break;
        case 11:
            READ(a, m->pc + pc_offset); WRITE(a, m->r[d]); break;
        case 12:
            if(permitted(m,m->r[s],instruction_pc)) m->pc = m->r[s];
            break;
        case 13:
            m->exception = 0x101u; supervisor(m, 0x101u, instruction_pc, -1); break;
        case 14:
            /* The supplied third-edition implementation leaves CC unchanged for LEA. */
            m->r[d] = (uint16_t)(m->pc + pc_offset); break;
        case 20: case 21: case 22: case 23: case 24:
            address=(uint16_t)(m->r[s]+signed_bits(word,5));
            if(m->strict_access&&(m->psr&0x8000u)&&(address<0x3000u||address>=0xFE00u)) {
                m->exception=0x102u;supervisor(m,0x102u,instruction_pc,-1);break;
            }
            if(op==22||op==23) {
                touch(m,address,1);lc3_poke_byte(m,address,(uint8_t)(op==22?m->r[d]:m->r[d]>>8u));
            } else {
                touch(m,address,0);a=lc3_peek_byte(m,address);
                if((address&0xFFFEu)==LC3_KBDR) m->kbsr&=0x7FFFu;
                if(op==24) m->r[d]=(uint16_t)signed_bits(a,8);
                else if(op==20) m->r[d]=(uint16_t)((m->r[d]&0xFF00u)|a);
                else m->r[d]=(uint16_t)((m->r[d]&255u)|(unsigned)a<<8u);
                set_cc(m,m->r[d]);
            }
            break;
        case 31: {
            unsigned mode=(word>>3u)&3u, count=m->r[t]&15u;
            uint16_t source=m->r[s];unsigned value;
            if(mode==3u){m->exception=0x101u;supervisor(m,0x101u,instruction_pc,-1);break;}
            if(mode==0u)value=(unsigned)source<<count;
            else {
                value=(unsigned)source>>count;
                if(mode==2u&&count&&(source&0x8000u))value|=0xFFFFu<<(16u-count);
            }
            m->r[d]=(uint16_t)value;set_cc(m,m->r[d]);break;
        }
        case 30:m->pc=(uint16_t)(m->pc+2*signed_bits(word,11));break;
        case 15:
            /* Match the supplied simulator: PC/PSR on supervisor stack, return via RTI. */
            supervisor(m, word & 255u, m->pc, -1); break;
    }
#undef READ
#undef WRITE
done:
    return 1;
}

void lc3_disassemble(uint16_t address,uint16_t word,char *out,size_t size) {
    unsigned op=word>>11u,d=word>>8u&7u,s=word>>5u&7u;
    unsigned base=op>=OP_LD_NEG&&op<=OP_LEA_NEG?OP_LD+(op-OP_LD_NEG):op;
    static const char *const traps[]={"GETC","OUT","PUTS","IN","PUTSP","HALT"};
    if(op==OP_BR) {
        unsigned cc=word>>8u&7u;
        if(!cc) snprintf(out,size,"NOP");
        else snprintf(out,size,"BR%s%s%s x%04X",cc&4u?"n":"",cc&2u?"z":"",cc&1u?"p":"",(uint16_t)(address+2+2*signed_bits(word,8)));
    } else if(op==OP_BRL||op==OP_JSR) snprintf(out,size,"%s x%04X",op==OP_JSR?"JSR":"BRL",(uint16_t)(address+2+2*signed_bits(word,11)));
    else if((op==OP_ADD||op==OP_AND)&&((word>>3u)&3u)) {
        unsigned fn=(word>>3u)&3u;
        static const char *const add_names[]={"ADD","SUB","MUL","MULU"};
        static const char *const and_names[]={"AND","DIVU","CLZ","MOV"};
        const char *name=op==OP_ADD?add_names[fn]:and_names[fn];
        if(op==OP_AND&&fn>=FN_CLZ) {
            if(word&7u)snprintf(out,size,".FILL x%04X",word);
            else snprintf(out,size,"%s R%u,R%u",name,d,s);
        } else snprintf(out,size,"%s R%u,R%u,R%u",name,d,s,word&7u);
    }
    else if(op>=OP_ADD&&op<=OP_ANDI) {
        const char *name=op==OP_ADD||op==OP_ADDI?"ADD":"AND";
        if(op==OP_ADDI||op==OP_ANDI) snprintf(out,size,"%s R%u,R%u,#%d",name,d,s,signed_bits(word,5));
        else snprintf(out,size,"%s R%u,R%u,R%u",name,d,s,word&7u);
    }    else if(op==OP_SHIFT) {
        const char *names[]={"SHL","SHR","SAR","RESERVADO"};
        snprintf(out,size,"%s R%u,R%u,R%u",names[(word>>3u)&3u],d,s,word&7u);
    }
    else if(op==OP_NOT) snprintf(out,size,"NOT R%u,R%u",d,s);
    else if(base>=OP_LD&&base<=OP_LEA) {
        const char *name=base==OP_LD?"LD":base==OP_ST?"ST":base==OP_LDI?"LDI":base==OP_STI?"STI":"LEA";
        int off=(int)(word&255u)-(op>=OP_LD_NEG?256:0);
        snprintf(out,size,"%s R%u,x%04X",name,d,(uint16_t)(address+2+2*off));
    } else if(op>=OP_LDR&&op<=OP_STR_NEG) {
        int off=(int)(word&31u)-((op==OP_LDR_NEG||op==OP_STR_NEG)?32:0);
        snprintf(out,size,"%s R%u,R%u,#%d",op<=OP_LDR_NEG?"LDR":"STR",d,s,off);
    } else if(op>=OP_LDBL&&op<=OP_LDBS) {
        const char *name=op==OP_LDBL?"LDBL":op==OP_LDBH?"LDBH":op==OP_STBL?"STBL":op==OP_STBH?"STBH":"LDBS";
        snprintf(out,size,"%s R%u,R%u,#%d",name,d,s,signed_bits(word,5));
    } else if(op==OP_JMP&&s==7) snprintf(out,size,"RET");
    else if(op==OP_JMP||op==OP_JSRR) snprintf(out,size,"%s R%u",op==OP_JMP?"JMP":"JSRR",s);
    else if(op==OP_RTI) snprintf(out,size,"RTI");
    else if(op==OP_TRAP) {
        unsigned vector=word&255u;
        if(vector>=0x20u&&vector<=0x25u) snprintf(out,size,"%s",traps[vector-0x20u]);
        else snprintf(out,size,"TRAP x%02X",vector);
    } else snprintf(out,size,".FILL x%04X",word);
}
