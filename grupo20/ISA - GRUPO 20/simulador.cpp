#include <array>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <string>

using namespace std;

constexpr uint32_t MEMORY_SIZE = 65536;
constexpr uint32_t MAX_INSTRUCTIONS = 10000000;

enum {
    R_R0 = 0, R_R1, R_R2, R_R3, R_R4, R_R5, R_R6, R_R7,
    R_PC, R_COND, R_COUNT
};
enum {
    FL_POS = 1 << 0,
    FL_ZRO = 1 << 1,
    FL_NEG = 1 << 2
};

enum {
    OP_BR = 0, OP_ADD = 1, OP_LD = 2, OP_ST = 3, OP_JSR = 4,
    OP_AND = 5, OP_LDR = 6, OP_STR = 7, OP_RTI = 8, OP_NOT = 9,
    OP_LDI = 10, OP_STI = 11, OP_JMP = 12, OP_SUB = 13, OP_LEA = 14,
    OP_TRAP = 15, OP_LDB = 16, OP_STB = 17, OP_LDRB = 18, OP_STRB = 19,
    OP_LDIB = 20, OP_STIB = 21, OP_SHF = 22, OP_OR = 23, OP_XOR = 24,
    OP_MUL = 25, OP_DIV = 26, OP_CMP = 27
};

array<uint8_t, MEMORY_SIZE> memory = {};
array<uint16_t, R_COUNT> reg = {};
uint32_t instructionCount = 0;
uint32_t memoryUsage = 0;

void updateFlags(uint16_t r) {
    if (reg[r] == 0) reg[R_COND] = FL_ZRO;
    else if ((reg[r] & 0x8000) != 0) reg[R_COND] = FL_NEG;
    else reg[R_COND] = FL_POS;
}

uint16_t signExtend(uint16_t value, int bitCount) {
    if (bitCount <= 0 || bitCount >= 16) return value;
    uint16_t signBit = static_cast<uint16_t>(1u << (bitCount - 1));
    if ((value & signBit) != 0)
        value = static_cast<uint16_t>(value | (0xFFFFu << bitCount));
    return value;
}

bool validByteAddress(int32_t address, const char* operation, uint16_t pc) {
    if (address < 0 || address >= static_cast<int32_t>(MEMORY_SIZE)) {
        cerr << "\n[EXCEPCION] " << operation
             << " fuera de memoria en PC: 0x" << hex << pc << dec << "\n";
        return false;
    }
    return true;
}

bool validWordAddress(int32_t address, const char* operation, uint16_t pc) {
    if (address < 0) {
        cerr << "\n[EXCEPCION] " << operation
             << " fuera de memoria en PC: 0x" << hex << pc << dec << "\n";
        return false;
    }
    if ((address & 1u) != 0) {
        cerr << "\n[EXCEPCION] " << operation
             << " usa direccion impar: 0x" << hex << address
             << " en PC: 0x" << pc << dec << "\n";
        return false;
    }
    if (address >= static_cast<int32_t>(MEMORY_SIZE - 1u)) {
        cerr << "\n[EXCEPCION] " << operation
             << " fuera de memoria en PC: 0x" << hex << pc << dec << "\n";
        return false;
    }
    return true;
}

uint16_t readWord(uint16_t address) {
    return static_cast<uint16_t>((memory[address] << 8) | memory[address + 1]);
}

void writeWord(uint16_t address, uint16_t value) {
    memory[address] = static_cast<uint8_t>((value >> 8) & 0xFF);
    memory[address + 1] = static_cast<uint8_t>(value & 0xFF);
}

void executeInstruction() {
    bool running = true;
    while (running) {
        if (instructionCount >= MAX_INSTRUCTIONS) {
            cerr << "\n[EXCEPCION] Limite de instrucciones (" << MAX_INSTRUCTIONS
                 << ") alcanzado. Posible bucle infinito.\n";
            break;
        }
        uint16_t currentPc = reg[R_PC];

        if (currentPc & 1u) {
            cerr << "\n[EXCEPCION] Salto a direccion impar en PC: 0x"
                 << hex << currentPc << dec << "\n";
            break;
        }
        if (currentPc >= MEMORY_SIZE - 1u) {
            cerr << "\n[EXCEPCION] Ejecucion fuera de memoria en PC: 0x"
                 << hex << currentPc << dec << "\n";
            break;
        }

        uint16_t instruction = readWord(currentPc);
        if (static_cast<uint32_t>(currentPc) + 2u > 65536u)
            reg[R_PC] = 0;
        else
            reg[R_PC] = static_cast<uint16_t>(currentPc + 2u);
        ++instructionCount;

        uint16_t op = instruction >> 11;
        uint16_t r0 = (instruction >> 8) & 0x7;
        uint16_t r1 = (instruction >> 5) & 0x7;
        uint16_t r2 = instruction & 0x7;
        uint16_t immFlag = (instruction >> 4) & 0x1;

        switch (op) {
            case OP_RTI:
                reg[R_PC] = reg[R_R7];
                break;
            case OP_ADD:
                reg[r0] = immFlag
                    ? static_cast<uint16_t>(reg[r1] + signExtend(instruction & 0xF, 4))
                    : static_cast<uint16_t>(reg[r1] + reg[r2]);
                updateFlags(r0);
                break;
            case OP_AND:
                reg[r0] = immFlag
                    ? static_cast<uint16_t>(reg[r1] & signExtend(instruction & 0xF, 4))
                    : static_cast<uint16_t>(reg[r1] & reg[r2]);
                updateFlags(r0);
                break;
            case OP_OR:
                reg[r0] = immFlag
                    ? static_cast<uint16_t>(reg[r1] | signExtend(instruction & 0xF, 4))
                    : static_cast<uint16_t>(reg[r1] | reg[r2]);
                updateFlags(r0);
                break;
            case OP_XOR:
                reg[r0] = immFlag
                    ? static_cast<uint16_t>(reg[r1] ^ signExtend(instruction & 0xF, 4))
                    : static_cast<uint16_t>(reg[r1] ^ reg[r2]);
                updateFlags(r0);
                break;
            case OP_NOT:
                reg[r0] = static_cast<uint16_t>(~reg[r1]);
                updateFlags(r0);
                break;
            case OP_SUB:
                reg[r0] = immFlag
                    ? static_cast<uint16_t>(reg[r1] - signExtend(instruction & 0xF, 4))
                    : static_cast<uint16_t>(reg[r1] - reg[r2]);
                updateFlags(r0);
                break;
            case OP_MUL: {
                int32_t left = static_cast<int16_t>(reg[r1]);
                int32_t right = immFlag
                    ? static_cast<int16_t>(signExtend(instruction & 0xF, 4))
                    : static_cast<int16_t>(reg[r2]);
                reg[r0] = static_cast<uint16_t>(left * right);
                updateFlags(r0);
                break;
            }
            case OP_DIV: {
                int32_t dividend = static_cast<int16_t>(reg[r1]);
                int32_t divisor = immFlag
                    ? static_cast<int16_t>(signExtend(instruction & 0xF, 4))
                    : static_cast<int16_t>(reg[r2]);
                if (divisor == 0) {
                    cerr << "\n[EXCEPCION] Division por cero en PC: 0x"
                         << hex << currentPc << dec << "\n";
                    running = false;
                    break;
                }
                int32_t quotient = dividend / divisor;
                if (quotient < -32768 || quotient > 32767) {
                    cerr << "\n[EXCEPCION] Resultado DIV fuera de rango en PC: 0x"
                         << hex << currentPc << dec << "\n";
                    running = false;
                    break;
                }
                reg[r0] = static_cast<uint16_t>(static_cast<int16_t>(quotient));
                updateFlags(r0);
                break;
            }
            case OP_BR: {
                uint16_t condition = (instruction >> 8) & 0x7;
                int32_t offset = static_cast<int16_t>(
                    signExtend(instruction & 0xFF, 8)) * 2;
                if ((condition & reg[R_COND]) != 0) {
                    int32_t next = static_cast<int32_t>(reg[R_PC]) + offset;
                    if (next < 0 || next > 65535) {
                        cerr << "\n[EXCEPCION] Salto fuera de memoria en PC: 0x"
                             << hex << currentPc << dec << "\n";
                        running = false;
                        break;
                    }
                    reg[R_PC] = static_cast<uint16_t>(next);
                }
                break;
            }
            case OP_JMP:
                reg[R_PC] = reg[r1];
                break;
            case OP_JSR:
                reg[R_R7] = reg[R_PC];
                if ((instruction & (1u << 10)) != 0) {
                    int32_t offset = static_cast<int32_t>(
                        static_cast<int16_t>(signExtend(instruction & 0x3FF, 10))) * 2;
                    int32_t next = static_cast<int32_t>(reg[R_PC]) + offset;
                    if (next < 0 || next > 65535) {
                        cerr << "\n[EXCEPCION] JSR fuera de memoria en PC: 0x"
                             << hex << currentPc << dec << "\n";
                        running = false;
                        break;
                    }
                    reg[R_PC] = static_cast<uint16_t>(next);
                } else {
                    reg[R_PC] = reg[r1];
                }
                break;
            case OP_LEA: {
                int32_t offset = static_cast<int16_t>(
                    signExtend(instruction & 0xFF, 8)) * 2;
                int32_t address = static_cast<int32_t>(reg[R_PC]) + offset;
                if (address < 0 || address > 65535) {
                    cerr << "\n[EXCEPCION] LEA fuera de memoria en PC: 0x"
                         << hex << currentPc << dec << "\n";
                    running = false;
                    break;
                }
                reg[r0] = static_cast<uint16_t>(address);
                updateFlags(r0);
                break;
            }
            case OP_LD: {
                int32_t offset = static_cast<int16_t>(
                    signExtend(instruction & 0xFF, 8)) * 2;
                int32_t address = static_cast<int32_t>(reg[R_PC]) + offset;
                if (!validWordAddress(address, "LD", currentPc)) {
                    running = false;
                    break;
                }
                reg[r0] = readWord(static_cast<uint16_t>(address));
                updateFlags(r0);
                break;
            }
            case OP_ST: {
                int32_t offset = static_cast<int16_t>(
                    signExtend(instruction & 0xFF, 8)) * 2;
                int32_t address = static_cast<int32_t>(reg[R_PC]) + offset;
                if (!validWordAddress(address, "ST", currentPc)) {
                    running = false;
                    break;
                }
                writeWord(static_cast<uint16_t>(address), reg[r0]);
                break;
            }
            case OP_LDB: {
                int32_t address = static_cast<int32_t>(reg[R_PC])
                    + static_cast<int16_t>(signExtend(instruction & 0xFF, 8));
                if (!validByteAddress(address, "LDB", currentPc)) {
                    running = false;
                    break;
                }
                reg[r0] = static_cast<uint16_t>(
                    static_cast<int8_t>(memory[static_cast<uint16_t>(address)]));
                updateFlags(r0);
                break;
            }
            case OP_STB: {
                int32_t address = static_cast<int32_t>(reg[R_PC])
                    + static_cast<int16_t>(signExtend(instruction & 0xFF, 8));
                if (!validByteAddress(address, "STB", currentPc)) {
                    running = false;
                    break;
                }
                memory[static_cast<uint16_t>(address)] = static_cast<uint8_t>(reg[r0] & 0xFF);
                break;
            }
            case OP_LDR: {
                int32_t offset = static_cast<int16_t>(
                    signExtend(instruction & 0x1F, 5)) * 2;
                int32_t address = static_cast<int32_t>(reg[r1]) + offset;
                if (!validWordAddress(address, "LDR", currentPc)) {
                    running = false;
                    break;
                }
                reg[r0] = readWord(static_cast<uint16_t>(address));
                updateFlags(r0);
                break;
            }
            case OP_STR: {
                int32_t offset = static_cast<int16_t>(
                    signExtend(instruction & 0x1F, 5)) * 2;
                int32_t address = static_cast<int32_t>(reg[r1]) + offset;
                if (!validWordAddress(address, "STR", currentPc)) {
                    running = false;
                    break;
                }
                writeWord(static_cast<uint16_t>(address), reg[r0]);
                break;
            }
            case OP_LDRB: {
                int32_t address = static_cast<int32_t>(reg[r1])
                    + static_cast<int16_t>(signExtend(instruction & 0x1F, 5));
                if (!validByteAddress(address, "LDRB", currentPc)) {
                    running = false;
                    break;
                }
                reg[r0] = static_cast<uint16_t>(
                    static_cast<int8_t>(memory[static_cast<uint16_t>(address)]));
                updateFlags(r0);
                break;
            }
            case OP_STRB: {
                int32_t address = static_cast<int32_t>(reg[r1])
                    + static_cast<int16_t>(signExtend(instruction & 0x1F, 5));
                if (!validByteAddress(address, "STRB", currentPc)) {
                    running = false;
                    break;
                }
                memory[static_cast<uint16_t>(address)] = static_cast<uint8_t>(reg[r0] & 0xFF);
                break;
            }
            case OP_LDI: {
                int32_t pointerOffset = static_cast<int16_t>(
                    signExtend(instruction & 0xFF, 8)) * 2;
                int32_t pointerAddress = static_cast<int32_t>(reg[R_PC]) + pointerOffset;
                if (!validWordAddress(pointerAddress, "LDI", currentPc)) {
                    running = false;
                    break;
                }
                uint16_t valueAddress = readWord(static_cast<uint16_t>(pointerAddress));
                if (!validWordAddress(valueAddress, "LDI destino", currentPc)) {
                    running = false;
                    break;
                }
                reg[r0] = readWord(valueAddress);
                updateFlags(r0);
                break;
            }
            case OP_STI: {
                int32_t pointerOffset = static_cast<int16_t>(
                    signExtend(instruction & 0xFF, 8)) * 2;
                int32_t pointerAddress = static_cast<int32_t>(reg[R_PC]) + pointerOffset;
                if (!validWordAddress(pointerAddress, "STI", currentPc)) {
                    running = false;
                    break;
                }
                uint16_t valueAddress = readWord(static_cast<uint16_t>(pointerAddress));
                if (!validWordAddress(valueAddress, "STI destino", currentPc)) {
                    running = false;
                    break;
                }
                writeWord(valueAddress, reg[r0]);
                break;
            }
            case OP_LDIB: {
                int32_t pointerAddress = static_cast<int32_t>(reg[R_PC])
                    + static_cast<int16_t>(signExtend(instruction & 0xFF, 8));
                if (!validWordAddress(pointerAddress, "LDIB puntero", currentPc)) {
                    running = false;
                    break;
                }
                uint16_t valueAddress = readWord(static_cast<uint16_t>(pointerAddress));
                if (!validByteAddress(valueAddress, "LDIB destino", currentPc)) {
                    running = false;
                    break;
                }
                reg[r0] = static_cast<uint16_t>(
                    static_cast<int8_t>(memory[valueAddress]));
                updateFlags(r0);
                break;
            }
            case OP_STIB: {
                int32_t pointerAddress = static_cast<int32_t>(reg[R_PC])
                    + static_cast<int16_t>(signExtend(instruction & 0xFF, 8));
                if (!validWordAddress(pointerAddress, "STIB puntero", currentPc)) {
                    running = false;
                    break;
                }
                uint16_t valueAddress = readWord(static_cast<uint16_t>(pointerAddress));
                if (!validByteAddress(valueAddress, "STIB destino", currentPc)) {
                    running = false;
                    break;
                }
                memory[valueAddress] = static_cast<uint8_t>(reg[r0] & 0xFF);
                break;
            }
            case OP_SHF: {
                uint16_t direction = (instruction >> 3) & 0x3;
                uint16_t amount = instruction & 0x7;
                if (direction == 0)
                    reg[r0] = static_cast<uint16_t>(reg[r1] << amount);
                else if (direction == 1)
                    reg[r0] = static_cast<uint16_t>(reg[r1] >> amount);
                else if (direction == 3)
                    reg[r0] = static_cast<uint16_t>(
                        static_cast<int16_t>(reg[r1]) >> amount);
                else {
                    cerr << "\n[ERROR] Direccion SHF invalida en PC: 0x"
                         << hex << currentPc << dec << "\n";
                    running = false;
                    break;
                }
                updateFlags(r0);
                break;
            }
            case OP_CMP: {
                int32_t result;
                if (immFlag)
                    result = static_cast<int16_t>(reg[r1])
                           - static_cast<int16_t>(signExtend(instruction & 0xF, 4));
                else
                    result = static_cast<int16_t>(reg[r1])
                           - static_cast<int16_t>(reg[r2]);
                if (result == 0) reg[R_COND] = FL_ZRO;
                else if (result < 0) reg[R_COND] = FL_NEG;
                else reg[R_COND] = FL_POS;
                break;
            }
            case OP_TRAP: {
                uint16_t trapVector = instruction & 0xFF;
                if (trapVector == 0x25 || trapVector == 0x00)
                    running = false;
                else if (trapVector == 0x21)
                    cout << static_cast<char>(reg[R_R0] & 0xFF);
                else if (trapVector == 0x22) {
                    uint32_t address = reg[R_R0];
                    size_t count = 0;
                    while (address < MEMORY_SIZE && count < MEMORY_SIZE) {
                        char c = static_cast<char>(memory[address]);
                        if (c == '\0') break;
                        cout << c;
                        ++address;
                        ++count;
                    }
                    if (count == MEMORY_SIZE)
                        cerr << "\n[ERROR] Cadena sin terminador para TRAP x22.\n";
                    cout << flush;
                } else {
                    cerr << "\n[ERROR] Trapvector no implementado: 0x"
                         << hex << trapVector << dec << " en PC: 0x"
                         << hex << currentPc << dec << "\n";
                    running = false;
                }
                break;
            }
            default:
                cerr << "\n[ERROR] Instruccion invalida 0x" << hex << instruction
                     << " en PC: 0x" << currentPc << dec << "\n";
                running = false;
                break;
        }
    }
}

bool parseHexWord(const string& text, uint16_t& value, bool requireFourDigits) {
    if (text.empty()) return false;
    if (requireFourDigits && text.size() != 4) return false;
    size_t consumed = 0;
    try {
        unsigned long parsed = stoul(text, &consumed, 16);
        if (consumed != text.size() || parsed > 0xFFFFu) return false;
        value = static_cast<uint16_t>(parsed);
        return true;
    } catch (...) {
        return false;
    }
}

bool loadProgram(const string& filename) {
    ifstream file(filename);
    if (!file) {
        cerr << "Error: no se pudo abrir '" << filename << "'\n";
        return false;
    }

    memory.fill(0);
    reg.fill(0);
    instructionCount = 0;
    memoryUsage = 0;

    string line;
    uint32_t address = 0;
    bool firstLine = true;
    size_t lineNumber = 0;

    while (getline(file, line)) {
        ++lineNumber;
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.empty()) continue;

        if (firstLine) {
            uint16_t start = 0;
            if (!parseHexWord(line, start, true) || (start & 1u) != 0) {
                cerr << "Error: direccion inicial invalida en linea "
                     << lineNumber << "\n";
                return false;
            }
            reg[R_PC] = start;
            address = start;
            firstLine = false;
        } else {
            uint16_t word = 0;
            if (!parseHexWord(line, word, true)) {
                cerr << "Error: palabra hexadecimal invalida en linea "
                     << lineNumber << ": '" << line << "'\n";
                return false;
            }
            if (address > MEMORY_SIZE - 2u) {
                cerr << "Error: programa excede el limite de memoria en linea "
                     << lineNumber << "\n";
                return false;
            }
            writeWord(static_cast<uint16_t>(address), word);
            address += 2;
            memoryUsage += 2;
        }
    }

    if (firstLine) {
        cerr << "Error: el archivo no contiene direccion inicial.\n";
        return false;
    }
    return true;
}

void printRegisters() {
    cout << "\n--- Estado final de los Registros ---\n";
    for (int i = 0; i < R_COUNT; ++i) {
        if (i == R_PC)
            cout << "PC   : 0x" << hex << setw(4) << setfill('0') << reg[R_PC]
                 << dec << "\n";
        else if (i == R_COND)
            cout << "COND : 0x" << hex << reg[R_COND] << dec << "\n";
        else
            cout << "R" << i << "   : 0x" << hex << setw(4) << setfill('0')
                 << reg[i] << dec << " (" << static_cast<int16_t>(reg[i]) << ")\n";
    }
}

int main(int argc, char* argv[]) {
    string filename;
    if (argc == 2)
        filename = argv[1];
    else {
        cout << "Ingrese el archivo del programa a simular (ej. salida.txt): ";
        getline(cin >> ws, filename);
    }
    if (filename.empty()) {
        cerr << "Error: no se indico un archivo de programa.\n";
        return 1;
    }
    if (!loadProgram(filename)) return 1;

    executeInstruction();
    printRegisters();
    cout << "Instrucciones ejecutadas: " << dec << instructionCount << "\n";
    cout << "Uso de memoria (Codigo + Datos): " << dec << memoryUsage << " bytes.\n";
    return 0;
}

