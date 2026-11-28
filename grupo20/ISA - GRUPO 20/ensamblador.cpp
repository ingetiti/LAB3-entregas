#include <array>
#include <algorithm>
#include <cctype>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

using namespace std;

const unordered_map<string, uint16_t> OPCODES = {
    {"BR", 0}, {"ADD", 1}, {"LD", 2}, {"ST", 3}, {"JSR", 4},
    {"AND", 5}, {"LDR", 6}, {"STR", 7}, {"RTI", 8}, {"NOT", 9},
    {"LDI", 10}, {"STI", 11}, {"JMP", 12}, {"SUB", 13}, {"LEA", 14},
    {"TRAP", 15}, {"LDB", 16}, {"STB", 17}, {"LDRB", 18}, {"STRB", 19},
    {"LDIB", 20}, {"STIB", 21}, {"SHF", 22}, {"OR", 23}, {"XOR", 24},
    {"MUL", 25}, {"DIV", 26}, {"CMP", 27}, {"LDW", 2}, {"STW", 3},
    {"JSRR", 4}, {"LDRW", 6}, {"STRW", 7}, {"LDIW", 10}, {"STIW", 11},
    {"RET", 12}
};

struct Line {
    uint16_t address;
    vector<string> tokens;
};

string upper(string value) {
    for (char& c : value)
        c = static_cast<char>(toupper(static_cast<unsigned char>(c)));
    return value;
}

vector<string> tokenize(const string& source) {
    vector<string> result;
    istringstream input(source);
    string token;
    while (input >> token)
        result.push_back(upper(token));
    return result;
}

bool parseUnsigned(const string& text, int& out) {
    string value = text;
    if (value.empty()) return false;

    if (value.front() == '#') value.erase(value.begin());

    size_t pos = 0;
    try {
        unsigned long base = 10;
        if (!value.empty() && (value.front() == 'X')) {
            value.erase(value.begin());
            base = 16;
        }
        long number = stoll(value, &pos, static_cast<int>(base));
        if (pos != value.size()) return false;
        out = static_cast<int>(number);
        return true;
    } catch (...) {
        return false;
    }
}

bool parseSigned(const string& text, int& out) {
    string value = text;
    if (!value.empty() && value.front() == '#') value.erase(value.begin());

    int sign = 1;
    if (!value.empty() && (value.front() == '+' || value.front() == '-')) {
        if (value.front() == '-') sign = -1;
        value.erase(value.begin());
    }
    if (!value.empty() && (value.front() == 'X')) {
        value.erase(value.begin());
        size_t pos = 0;
        try {
            unsigned long number = stoul(value, &pos, 16);
            if (pos != value.size()) return false;
            out = sign * static_cast<int>(number);
            return true;
        } catch (...) {
            return false;
    }
    }

    size_t pos = 0;
    try {
        long number = stol(value, &pos, 10);
        if (pos != value.size()) return false;
        out = sign * static_cast<int>(number);
        return true;
    } catch (...) {
        return false;
    }
}

bool parseRegister(const string& text, uint16_t& out) {
    if (text.size() < 2 || upper(text).front() != 'R') return false;
    int value = 0;
    if (!parseUnsigned(text.substr(1), value)) return false;
    if (value < 0 || value > 7) return false;
    out = static_cast<uint16_t>(value);
    return true;
}

bool rangeSigned(int value, int bits, bool allowImmediateLabel = false) {
    if (allowImmediateLabel) return true;
    int limit = 1 << (bits - 1);
    return value >= -limit && value < limit;
}

bool rangeImmediate4(int value) {
    return value >= -8 && value <= 15;
}

bool addWord(array<uint8_t, 65536>& memory, uint16_t address,
             uint16_t word, const string& line) {
    if (static_cast<uint32_t>(address) + 1 >= 65536) {
        cerr << "Error: desborda memoria al ensamblar '" << line << "' en 0x"
             << hex << uppercase << address << dec << "\n";
        return false;
    }
    memory[address] = static_cast<uint8_t>((word >> 8) & 0xFF);
    memory[address + 1] = static_cast<uint8_t>(word & 0xFF);
    return true;
}

int main(int argc, char* argv[]) {
    string inputName;
    string outputName;

    if (argc == 3) {
        inputName = argv[1];
        outputName = argv[2];
    } else {
        cout << "Ingrese el archivo ASM de entrada (ej. prog.asm): ";
        getline(cin >> ws, inputName);
        cout << "Ingrese el nombre del archivo de salida (ej. salida.txt): ";
        getline(cin >> ws, outputName);
    }

    if (inputName.empty() || outputName.empty()) {
        cerr << "Error: debe indicar archivos de entrada y salida.\n";
        return 1;
    }
    if (inputName == outputName) {
        cerr << "Error: los archivos de entrada y salida deben ser distintos.\n";
        return 1;
    }

    ifstream input(inputName);
    if (!input) {
        cerr << "Error: no se pudo abrir el archivo de entrada '" << inputName << "'\n";
        return 1;
    }

    uint32_t address = 0;
    uint32_t startAddress = 0;
    bool hasOrig = false;
    unordered_map<string, uint16_t> labels;
    unordered_set<string> externalSymbols;
    vector<Line> lines;
    vector<string> pendingLabels;
    size_t sourceNumber = 0;
    auto bindLabel = [&](const string& name, uint16_t labelAddress) -> bool {
        if (labels.count(name) != 0) {
            cerr << "Error: etiqueta duplicada '" << name
                 << "' en linea " << sourceNumber << "\n";
            return false;
        }
        labels[name] = labelAddress;
        return true;
    };
    string sourceLine;

    while (getline(input, sourceLine)) {
        ++sourceNumber;
        string line = sourceLine.substr(0, sourceLine.find(';'));

        size_t quote = line.find('"');
        if (quote != string::npos) {
            size_t close = line.rfind('"');
            if (close == quote) {
                cerr << "Error: comilla sin cerrar en linea " << sourceNumber << "\n";
                return 1;
            }
            string before = line.substr(0, quote);
            string content = line.substr(quote + 1, close - quote - 1);
            replace(before.begin(), before.end(), ',', ' ');
            vector<string> prefix = tokenize(before);

            if (!prefix.empty() && upper(prefix[0]) == ".STRINGZ") prefix.clear();
            if (!prefix.empty()) {
                string label = upper(prefix.front());
                if (!prefix.empty() && prefix[0].find('.') != 0) {
                    if (address % 2 != 0) {
                        lines.push_back({static_cast<uint16_t>(address), {".NOP_PADDING"}});
                        ++address;
                    }
                    if (address + content.size() + 1 > 65536) {
                        cerr << "Error: .STRINGZ excede memoria en linea " << sourceNumber << "\n";
                        return 1;
                    }
                    if (!bindLabel(label, static_cast<uint16_t>(address))) return 1;
                    pendingLabels.clear();
                }
            }

            if (address % 2 != 0) {
                lines.push_back({static_cast<uint16_t>(address), {".NOP_PADDING"}});
                ++address;
            }
            if (address + content.size() + 1 > 65536) {
                cerr << "Error: .STRINGZ excede memoria en linea " << sourceNumber << "\n";
                return 1;
            }
            for (const string& pending : pendingLabels)
                if (!bindLabel(pending, static_cast<uint16_t>(address))) return 1;
            pendingLabels.clear();
            lines.push_back({static_cast<uint16_t>(address), {".STRINGZ", content}});
            address += content.size() + 1;
            continue;
        }

        replace(line.begin(), line.end(), ',', ' ');
        vector<string> tokens = tokenize(line);
        if (tokens.empty()) continue;

        if (tokens[0] == ".ORIG") {
            if (tokens.size() != 2) {
                cerr << "Error: .ORIG requiere una direccion en linea " << sourceNumber << "\n";
                return 1;
            }
            int origin = 0;
            if (!parseSigned(tokens[1], origin) || origin < 0 || origin > 65534) {
                cerr << "Error: direccion .ORIG invalida en linea " << sourceNumber << "\n";
                return 1;
            }
            if (origin % 2 != 0) {
                cerr << "Error: .ORIG debe ser una direccion par en linea " << sourceNumber << "\n";
                return 1;
            }
            address = static_cast<uint32_t>(origin);
            startAddress = address;
            hasOrig = true;
            continue;
        }
        if (tokens[0] == ".END") break;
        if (tokens[0] == ".EXTERNAL") {
            if (tokens.size() < 2) {
                cerr << "Error: .EXTERNAL requiere al menos un simbolo en linea "
                     << sourceNumber << "\n";
                return 1;
            }
            for (size_t i = 1; i < tokens.size(); ++i)
                externalSymbols.insert(tokens[i]);
            continue;
        }
        if (tokens[0].front() == '.' &&
            tokens[0] != ".BYTE" && tokens[0] != ".FILL" &&
            tokens[0] != ".STRINGZ") {
            cerr << "Error: directiva desconocida '" << tokens[0]
                 << "' en linea " << sourceNumber << "\n";
            return 1;
        }

        bool isDirective = tokens[0] == ".BYTE" || tokens[0] == ".FILL" ||
                           tokens[0] == ".STRINGZ";
        bool isOpcode = OPCODES.count(tokens[0]) != 0 ||
                        tokens[0].rfind("BR", 0) == 0;
        string labelName;
        if (!isOpcode && !isDirective) {
            labelName = tokens[0];
            tokens.erase(tokens.begin());
        }

        if (tokens.empty()) {
            if (!labelName.empty()) {
                if (labels.count(labelName) != 0) {
                    cerr << "Error: etiqueta duplicada '" << labelName
                         << "' en linea " << sourceNumber << "\n";
                    return 1;
                }
                pendingLabels.push_back(labelName);
            }
            continue;
        }

        if (tokens[0] == ".BYTE") {
            if (tokens.size() != 2) {
                cerr << "Error: .BYTE requiere un valor en linea " << sourceNumber << "\n";
                return 1;
            }
            if (address >= 65536) {
                cerr << "Error: desborda memoria en linea " << sourceNumber << "\n";
                return 1;
            }
            if (!labelName.empty() &&
                !bindLabel(labelName, static_cast<uint16_t>(address))) return 1;
            for (const string& pending : pendingLabels)
                if (!bindLabel(pending, static_cast<uint16_t>(address))) return 1;
            pendingLabels.clear();
            lines.push_back({static_cast<uint16_t>(address), tokens});
            ++address;
        } else if (tokens[0] == ".FILL") {
            if (tokens.size() != 2) {
                cerr << "Error: .FILL requiere un valor o etiqueta en linea "
                     << sourceNumber << "\n";
                return 1;
            }
            if (address % 2 != 0) {
                lines.push_back({static_cast<uint16_t>(address), {".NOP_PADDING"}});
                ++address;
            }
            if (address + 2 > 65536) {
                cerr << "Error: desborda memoria en linea " << sourceNumber << "\n";
                return 1;
            }
            if (!labelName.empty() &&
                !bindLabel(labelName, static_cast<uint16_t>(address))) return 1;
            for (const string& pending : pendingLabels)
                if (!bindLabel(pending, static_cast<uint16_t>(address))) return 1;
            pendingLabels.clear();
            lines.push_back({static_cast<uint16_t>(address), tokens});
            address += 2;
        } else {
            if (address % 2 != 0) {
                lines.push_back({static_cast<uint16_t>(address), {".NOP_PADDING"}});
                ++address;
            }
            if (address + 2 > 65536) {
                cerr << "Error: desborda memoria en linea " << sourceNumber << "\n";
                return 1;
            }
            if (!labelName.empty() &&
                !bindLabel(labelName, static_cast<uint16_t>(address))) return 1;
            for (const string& pending : pendingLabels)
                if (!bindLabel(pending, static_cast<uint16_t>(address))) return 1;
            pendingLabels.clear();
            lines.push_back({static_cast<uint16_t>(address), tokens});
            address += 2;
        }
    }
    input.close();

    if (!hasOrig) {
        cerr << "Error: falta la directiva .ORIG.\n";
        return 1;
    }

    for (const auto& item : labels)
        if (externalSymbols.count(item.first) != 0) {
            cerr << "Error: '" << item.first << "' esta declarado externo y definido localmente.\n";
            return 1;
        }

    array<uint8_t, 65536> memory = {};
    for (const Line& line : lines) {
        const vector<string>& tokens = line.tokens;
        const string& mnemonic = tokens[0];
        uint16_t addressAt = line.address;
        uint16_t instruction = 0;

        if (mnemonic == ".NOP_PADDING") {
            memory[addressAt] = 0;
            continue;
        }
        if (mnemonic == ".BYTE") {
            int value = 0;
            if (!parseSigned(tokens[1], value) || value < -128 || value > 255) {
                cerr << "Error: valor .BYTE fuera de rango en 0x"
                     << hex << uppercase << addressAt << dec << "\n";
                return 1;
            }
            memory[addressAt] = static_cast<uint8_t>(value & 0xFF);
            continue;
        }
        if (mnemonic == ".STRINGZ") {
            const string& text = tokens[1];
            for (char c : text)
                memory[addressAt++] = static_cast<uint8_t>(static_cast<unsigned char>(c));
            memory[addressAt] = 0;
            continue;
        }
        if (mnemonic == ".FILL") {
            int numeric = 0;
            uint16_t value = 0;
            if (labels.count(tokens[1])) value = labels.at(tokens[1]);
            else if (parseSigned(tokens[1], numeric) &&
                     numeric >= -32768 && numeric <= 65535)
                value = static_cast<uint16_t>(numeric & 0xFFFF);
            else {
                cerr << "Error: etiqueta o valor desconocido en .FILL: "
                     << tokens[1] << "\n";
                return 1;
            }
            if (!addWord(memory, addressAt, value, ".FILL")) return 1;
            continue;
        }
        if (OPCODES.count(mnemonic) == 0 && mnemonic.rfind("BR", 0) != 0) {
            cerr << "Error: instruccion desconocida '" << mnemonic << "' en 0x"
                 << hex << uppercase << addressAt << dec << "\n";
            return 1;
        }

        if (mnemonic.rfind("BR", 0) == 0) {
            if (mnemonic != "BR" && mnemonic != "BRN" && mnemonic != "BRZ" &&
                mnemonic != "BRP" && mnemonic != "BRNZ" && mnemonic != "BRNP" &&
                mnemonic != "BRZP" && mnemonic != "BRNZP") {
                cerr << "Error: condicion BR desconocida '" << mnemonic << "' en 0x"
                     << hex << uppercase << addressAt << dec << "\n";
                return 1;
            }
            uint16_t condition = 0;
            if (mnemonic.find('N') != string::npos) condition |= 4;
            if (mnemonic.find('Z') != string::npos) condition |= 2;
            if (mnemonic.find('P') != string::npos) condition |= 1;
            if (mnemonic == "BR") condition = 7;
            if (tokens.size() != 2) {
                cerr << "Error: " << mnemonic << " requiere una etiqueta en 0x"
                     << hex << uppercase << addressAt << dec << "\n";
                return 1;
            }
            if (!labels.count(tokens[1])) {
                cerr << "Error: etiqueta desconocida '" << tokens[1]
                     << "' en 0x" << hex << uppercase << addressAt << dec << "\n";
                return 1;
            }
            int offset = static_cast<int>(labels.at(tokens[1]) -
                                          (addressAt + 2)) / 2;
            if (!rangeSigned(offset, 8)) {
                cerr << "Error: BR excede el offset PC de 8 bits en 0x"
                     << hex << uppercase << addressAt << dec << "\n";
                return 1;
            }
            instruction = (condition << 8) | (offset & 0xFF);
        } else {
            uint16_t opcode = OPCODES.at(mnemonic);
            instruction = opcode << 11;

            if (mnemonic == "ADD" || mnemonic == "AND" || mnemonic == "SUB" ||
                mnemonic == "MUL" || mnemonic == "DIV" || mnemonic == "OR" ||
                mnemonic == "XOR") {
                if (tokens.size() != 4) {
                    cerr << "Error: " << mnemonic << " requiere DR, SR1 y SR2/imm4.\n";
                    return 1;
                }
                uint16_t dr = 0, sr1 = 0;
                if (!parseRegister(tokens[1], dr) || !parseRegister(tokens[2], sr1)) {
                    cerr << "Error: registro invalido en " << mnemonic << ".\n";
                    return 1;
                }
                instruction |= dr << 8 | sr1 << 5;
                uint16_t sr2 = 0;
                if (parseRegister(tokens[3], sr2)) instruction |= sr2;
                else {
                    int immediate = 0;
                    if (!parseSigned(tokens[3], immediate) ||
                        !rangeImmediate4(immediate)) {
                        cerr << "Error: inmediato invalido para " << mnemonic << ".\n";
                        return 1;
                    }
                    instruction |= 1 << 4 | (immediate & 0xF);
                }
            } else if (mnemonic == "NOT") {
                if (tokens.size() != 3) {
                    cerr << "Error: NOT requiere DR y SR.\n";
                    return 1;
                }
                uint16_t dr = 0, sr = 0;
                if (!parseRegister(tokens[1], dr) || !parseRegister(tokens[2], sr)) {
                    cerr << "Error: registro invalido en NOT.\n";
                    return 1;
                }
                instruction |= dr << 8 | sr << 5 | 0x1F;
            } else if (mnemonic == "LD" || mnemonic == "LDW" ||
                       mnemonic == "ST" || mnemonic == "STW" ||
                       mnemonic == "LDB" || mnemonic == "STB" ||
                       mnemonic == "LEA") {
                if (tokens.size() != 3) {
                    cerr << "Error: operandos invalidos para " << mnemonic << ".\n";
                    return 1;
                }
                uint16_t dr = 0;
                if (!parseRegister(tokens[1], dr)) {
                    cerr << "Error: registro invalido para " << mnemonic << ".\n";
                    return 1;
                }
                int offset = 0;
                if (labels.count(tokens[2]))
                    offset = mnemonic == "LDB" || mnemonic == "STB"
                        ? static_cast<int>(labels.at(tokens[2]) - (addressAt + 2))
                        : static_cast<int>(labels.at(tokens[2]) - (addressAt + 2)) / 2;
                else if (!parseSigned(tokens[2], offset)) {
                    cerr << "Error: operando invalido para " << mnemonic << ".\n";
                    return 1;
                }
                if (!rangeSigned(offset, 8)) {
                    cerr << "Error: PC-offset fuera de rango para " << mnemonic << ".\n";
                    return 1;
                }
                instruction |= dr << 8 | (offset & 0xFF);
            } else if (mnemonic == "LDR" || mnemonic == "LDRW" ||
                       mnemonic == "STR" || mnemonic == "STRW" ||
                       mnemonic == "LDRB" || mnemonic == "STRB") {
                if (tokens.size() != 4) {
                    cerr << "Error: operandos invalidos para " << mnemonic << ".\n";
                    return 1;
                }
                uint16_t dr = 0, base = 0;
                int offset = 0;
                if (!parseRegister(tokens[1], dr) || !parseRegister(tokens[2], base) ||
                    !parseSigned(tokens[3], offset) || !rangeSigned(offset, 6)) {
                    cerr << "Error: operandos invalidos para " << mnemonic << ".\n";
                    return 1;
                }
                instruction |= dr << 8 | base << 5 | (offset & 0x1F);
            } else if (mnemonic == "LDI" || mnemonic == "LDIW" ||
                       mnemonic == "STI" || mnemonic == "STIW" ||
                       mnemonic == "LDIB" || mnemonic == "STIB") {
                if (tokens.size() != 3) {
                    cerr << "Error: operandos invalidos para " << mnemonic << ".\n";
                    return 1;
                }
                uint16_t dr = 0;
                if (!parseRegister(tokens[1], dr)) {
                    cerr << "Error: registro invalido para " << mnemonic << ".\n";
                    return 1;
                }
                int offset = 0;
                if (labels.count(tokens[2]))
                    offset = mnemonic == "LDIB" || mnemonic == "STIB"
                        ? static_cast<int>(labels.at(tokens[2]) - (addressAt + 2))
                        : static_cast<int>(labels.at(tokens[2]) - (addressAt + 2)) / 2;
                else if (!parseSigned(tokens[2], offset)) {
                    cerr << "Error: operando invalido para " << mnemonic << ".\n";
                    return 1;
                }
                if (!rangeSigned(offset, 8)) {
                    cerr << "Error: PC-offset fuera de rango para " << mnemonic << ".\n";
                    return 1;
                }
                instruction |= dr << 8 | (offset & 0xFF);
            } else if (mnemonic == "JMP" || mnemonic == "RET") {
                if (mnemonic == "RET" && tokens.size() != 1) {
                    cerr << "Error: RET no tiene operandos.\n";
                    return 1;
                }
                if (mnemonic == "JMP" && tokens.size() != 2) {
                    cerr << "Error: JMP requiere un registro.\n";
                    return 1;
                }
                uint16_t base = 7;
                if (mnemonic == "JMP" && !parseRegister(tokens[1], base)) {
                    cerr << "Error: registro invalido para JMP.\n";
                    return 1;
                }
                instruction |= base << 5;
            } else if (mnemonic == "JSR" || mnemonic == "JSRR") {
                if (tokens.size() != 2) {
                    cerr << "Error: " << mnemonic << " requiere un destino.\n";
                    return 1;
                }
                uint16_t base = 0;
                if (parseRegister(tokens[1], base)) instruction |= base << 5;
                else {
                    if (!labels.count(tokens[1]) || externalSymbols.count(tokens[1]) != 0) {
                        cerr << "Error: destino JSR desconocido o externo '" << tokens[1] << "'.\n";
                        return 1;
                    }
                    int offset = static_cast<int>(labels.at(tokens[1]) -
                                                  (addressAt + 2)) / 2;
                    if (!rangeSigned(offset, 10)) {
                        cerr << "Error: JSR excede el offset de 10 bits.\n";
                        return 1;
                    }
                    instruction |= 1 << 10 | (offset & 0x3FF);
                }
            } else if (mnemonic == "TRAP") {
                if (tokens.size() != 2) {
                    cerr << "Error: TRAP requiere trapvect8.\n";
                    return 1;
                }
                int vector = 0;
                if (!parseSigned(tokens[1], vector) || vector < 0 || vector > 255) {
                    cerr << "Error: trapvect8 invalido.\n";
                    return 1;
                }
                instruction |= vector & 0xFF;
            } else if (mnemonic == "CMP") {
                if (tokens.size() != 3) {
                    cerr << "Error: CMP requiere SR1 y SR2/imm4.\n";
                    return 1;
                }
                uint16_t sr1 = 0;
                if (!parseRegister(tokens[1], sr1)) {
                    cerr << "Error: registro invalido para CMP.\n";
                    return 1;
                }
                instruction |= sr1 << 5;
                uint16_t sr2 = 0;
                if (parseRegister(tokens[2], sr2)) instruction |= sr2;
                else {
                    int immediate = 0;
                    if (!parseSigned(tokens[2], immediate) ||
                        !rangeImmediate4(immediate)) {
                        cerr << "Error: inmediato invalido para CMP.\n";
                        return 1;
                    }
                    instruction |= 1 << 4 | (immediate & 0xF);
                }
            } else if (mnemonic == "SHF") {
                if (tokens.size() != 4 && tokens.size() != 5) {
                    cerr << "Error: operandos invalidos para SHF.\n";
                    return 1;
                }
                uint16_t dr = 0, sr = 0;
                if (!parseRegister(tokens[1], dr) || !parseRegister(tokens[2], sr)) {
                    cerr << "Error: registro invalido para SHF.\n";
                    return 1;
                }
                string direction = tokens.size() == 5 ? tokens[3] : "LSHF";
                string amountText = tokens.size() == 5 ? tokens[4] : tokens[3];
                uint16_t dir = 0;
                if (direction == "RSHF") dir = 1;
                else if (direction == "ARSHF") dir = 3;
                else if (direction != "LSHF") {
                    cerr << "Error: direccion SHF desconocida '" << direction << "'.\n";
                    return 1;
                }
                int amount = 0;
                if (!parseSigned(amountText, amount) || amount < 0 || amount > 7) {
                    cerr << "Error: cantidad SHF fuera de rango.\n";
                    return 1;
                }
                instruction |= dr << 8 | sr << 5 | dir << 3 | amount;
            } else if (mnemonic == "RTI") {
                if (tokens.size() != 1) {
                    cerr << "Error: RTI no tiene operandos.\n";
                    return 1;
                }
            }
        }

        if (!addWord(memory, addressAt, instruction, mnemonic)) return 1;
    }

    ofstream output(outputName);
    if (!output) {
        cerr << "Error: no se pudo crear el archivo de salida '" << outputName << "'\n";
        return 1;
    }
    output << setfill('0') << setw(4) << hex << uppercase << startAddress << "\n";
    for (uint32_t i = startAddress; i < address; i += 2) {
        if (i + 1 >= 65536) break;
        uint16_t word = static_cast<uint16_t>((memory[i] << 8) | memory[i + 1]);
        output << setfill('0') << setw(4) << hex << uppercase << word << "\n";
    }
    output.close();
    cout << "Ensamblado exitoso. Se genero el archivo: " << outputName << "\n";
    return 0;
}

