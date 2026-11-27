#ifndef LC3_MACHINE_H
#define LC3_MACHINE_H
#include "assembler.h"
#include "isa.h"
#include <stddef.h>
#include <stdint.h>

#define LC3_WORDS 65536u
#define LC3_INPUT_SIZE 256u
#define LC3_KBSR 0xFE00u
#define LC3_KBDR 0xFE02u
#define LC3_DSR  0xFE04u
#define LC3_DDR  0xFE06u
#define LC3_PSR  0xFFFCu
#define LC3_MCR  0xFFFEu
typedef void (*Lc3Output)(void *context, unsigned char ch);
typedef struct {
    uint8_t memory[ISA_MEMORY_BYTES];
    uint8_t accessed[ISA_MEMORY_BYTES];
    uint16_t r[8], pc, ir, psr, mcr, usp, ssp;
    uint16_t kbsr, kbdr, ddr;
    unsigned char input[LC3_INPUT_SIZE];
    size_t input_start, input_count;
    uint64_t instructions, interrupts;
    uint64_t memory_read_bytes, memory_write_bytes; /* trafico acumulado, no ocupacion */
    size_t program_bytes, accessed_bytes, written_bytes;
    int strict_access;
    int waiting_for_input; /* ultimo paso consulto KBSR sin dato */
    unsigned exception, last_exception; /* 0 = none; 0x100 privilege, 0x101 opcode, 0x102 access */
    Lc3Output output;
    void *output_context;
} Lc3;

int lc3_init(Lc3 *machine, const Lc3Image *program, AsmError *error);
int lc3_step(Lc3 *machine); /* 1 executed (including exception/interrupt); 0 halted */
int lc3_key(Lc3 *machine, unsigned char ch);
uint16_t lc3_peek(const Lc3 *machine, uint16_t address);
uint8_t lc3_peek_byte(const Lc3 *machine, uint16_t address);
void lc3_poke_byte(Lc3 *machine, uint16_t address, uint8_t value);
void lc3_poke(Lc3 *machine, uint16_t address, uint16_t value);
void lc3_disassemble(uint16_t address, uint16_t word, char *out, size_t size);
const Lc3Image *lc3_os_image(AsmError *error);
void lc3_os_free(void);
#endif
