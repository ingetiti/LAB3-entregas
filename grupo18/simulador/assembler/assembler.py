"""
assembler.py - Orquestador del ensamblador (ISA Lab 3c). Etapa 5.5.

Una única función pública, assemble(), que encadena las tres etapas ya
construidas y probadas:

    texto --parse_program--> Program --build_symbol_table--> SymbolTable
          --encode_program (+ símbolos externos)--> EncodedProgram

RESPONSABILIDAD
---------------
Solo COORDINAR. No analiza texto, no calcula direcciones, no codifica y no
toca el AST ni la tabla de símbolos: cada etapa recibe exactamente el objeto
que produjo la anterior. Si mañana cambia cómo se calculan las direcciones, este
archivo no cambia.

ERRORES
-------
Las excepciones de cada etapa se propagan TAL CUAL (mismo objeto, mismo tipo,
con todas sus líneas y textos fuente): no se capturan, no se envuelven ni se
traducen. Que una etapa posterior no corra cuando una anterior falla no
requiere ningún `if`: la excepción corta el flujo.

  ParseErrors   sintaxis, etiquetas duplicadas, un solo .ORIG, nada tras .END
  SymbolErrors  layout: .ORIG impar o ausente, referencias a etiquetas inexistentes,
                programa que no cabe en memoria
  EncodeErrors  rangos de offsets, alineación de destinos, símbolos externos

Para capturar cualquiera de ellas a la vez se exporta ASSEMBLY_ERRORS, una tupla
utilizable directamente en `except ASSEMBLY_ERRORS:`.

SÍMBOLOS EXTERNOS
-----------------
`external_symbols` (mapping nombre -> dirección, opcional) se entrega sin
modificar a encode_program, que es quien define y valida su semántica. Los
nombres se declaran en el Assembly con .EXTERNAL.
"""

from assembler.encoder import EncodeErrors, encode_program
from assembler.parser import ParseErrors, parse_program
from assembler.symbols import SymbolErrors, build_symbol_table

__all__ = ["ASSEMBLY_ERRORS", "assemble"]

ASSEMBLY_ERRORS = (ParseErrors, SymbolErrors, EncodeErrors)


def assemble(source, external_symbols=None):
    """Ensambla `source` (texto Assembly) y devuelve su EncodedProgram.

    external_symbols  mapping opcional nombre -> dirección para los símbolos
                      declarados con .EXTERNAL (ver encoder.encode_program).

    Lanza ParseErrors, SymbolErrors o EncodeErrors según la primera etapa que
    falle; ver el docstring del módulo.
    """
    program = parse_program(source)
    symbol_table = build_symbol_table(program)
    return encode_program(program, symbol_table, external_symbols=external_symbols)
