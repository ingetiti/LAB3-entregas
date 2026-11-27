#ifndef LC3_ISA_H
#define LC3_ISA_H

/* Todos los opcodes ocupan los bits 15..11. El 31 contiene SHL/SHR/SAR; submodo 11 reservado. */
enum {
    OP_BR, OP_ADD, OP_ADDI, OP_AND, OP_ANDI, OP_NOT,
    OP_LD, OP_ST, OP_LDI, OP_STI, OP_LEA,
    OP_LDR, OP_LDR_NEG, OP_STR, OP_STR_NEG,
    OP_JSR, OP_JSRR, OP_JMP, OP_RTI, OP_TRAP,
    OP_LDBL, OP_LDBH, OP_STBL, OP_STBH, OP_LDBS,
    OP_LD_NEG, OP_ST_NEG, OP_LDI_NEG, OP_STI_NEG, OP_LEA_NEG,
    OP_BRL, OP_SHIFT
};
/* Suboperaciones de los campos [4:3], antes sin uso en ADD/AND registro.
 * Los opcodes, inmediatos y desplazamientos existentes no cambian. */
enum { FN_ADD=0, FN_SUB=1, FN_MUL=2, FN_MULU=3 };
enum { FN_AND=0, FN_DIVU=1, FN_CLZ=2, FN_MOV=3 };
#define ISA_MEMORY_BYTES 65536u
#define ISA_REGISTER_COUNT 8u

#endif
