"""Imagen de memoria: lo que produce el ensamblador y lo que carga el simulador.

Una imagen es una dirección de origen y una secuencia de bytes que se carga a partir
de ese origen. Los formatos de archivo son (en todos, los primeros 16 bits son el
origen):

  .bin   binario crudo: origen (2 bytes, little-endian) y luego los bytes de memoria
  .hex   texto: una palabra de 16 bits en hexadecimal por token, la primera es el origen
  .dec   texto: una palabra de 16 bits en decimal (sin signo) por token, la primera es el origen
  .bits  texto: una palabra de 16 bits en binario por línea, la primera es el origen

En los formatos de texto cada palabra se escribe con su valor (el byte de la dirección
par es el menos significativo), y se ignora lo que sigue a un ';'.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

FORMATS = ("bin", "hex", "dec", "bits")


class ImageError(ValueError):
    pass


@dataclass
class Image:
    origin: int
    data: bytes

    def __post_init__(self):
        if not 0 <= self.origin <= 0xFFFF:
            raise ImageError(f"origen fuera de rango: {self.origin}")
        if self.origin % 2:
            raise ImageError(f"el origen debe ser una dirección par (x{self.origin:04X})")
        if len(self.data) % 2:
            raise ImageError("la imagen debe tener una cantidad par de bytes")
        if self.origin + len(self.data) > 0x10000:
            raise ImageError("la imagen no entra en la memoria de 64 KiB")

    def words(self) -> list[int]:
        return [self.data[i] | self.data[i + 1] << 8 for i in range(0, len(self.data), 2)]

    # ------------------------------------------------------------------ guardar
    def to_bytes(self) -> bytes:
        return bytes([self.origin & 0xFF, self.origin >> 8]) + self.data

    def to_text(self, fmt: str) -> str:
        words = [self.origin] + self.words()
        if fmt == "hex":
            lines = [" ".join(f"{w:04X}" for w in words[i:i + 8]) for i in range(0, len(words), 8)]
        elif fmt == "dec":
            lines = [" ".join(str(w) for w in words[i:i + 8]) for i in range(0, len(words), 8)]
        elif fmt == "bits":
            lines = [f"{w:016b}" for w in words]
        else:
            raise ImageError(f"formato de texto desconocido: {fmt}")
        return "\n".join(lines) + "\n"

    def save(self, path: str | Path, fmt: str | None = None) -> None:
        path = Path(path)
        fmt = fmt or path.suffix.lstrip(".").lower() or "bin"
        if fmt == "bin":
            path.write_bytes(self.to_bytes())
        else:
            path.write_text(self.to_text(fmt), encoding="ascii")

    # ------------------------------------------------------------------- cargar
    @classmethod
    def from_bytes(cls, raw: bytes) -> "Image":
        if len(raw) < 2:
            raise ImageError("archivo binario demasiado corto")
        return cls(raw[0] | raw[1] << 8, bytes(raw[2:]))

    @classmethod
    def from_words(cls, words: list[int]) -> "Image":
        if not words:
            raise ImageError("archivo vacío")
        data = bytearray()
        for w in words[1:]:
            data += bytes([w & 0xFF, w >> 8 & 0xFF])
        return cls(words[0], bytes(data))

    @classmethod
    def from_text(cls, text: str, fmt: str) -> "Image":
        words: list[int] = []
        for ln, line in enumerate(text.splitlines(), 1):
            line = line.split(";", 1)[0].strip()
            for tok in line.split():
                try:
                    if fmt == "hex":
                        v = int(tok, 16)
                    elif fmt == "dec":
                        v = int(tok, 10)
                    elif fmt == "bits":
                        if len(tok) != 16 or set(tok) - {"0", "1"}:
                            raise ValueError
                        v = int(tok, 2)
                    else:
                        raise ImageError(f"formato de texto desconocido: {fmt}")
                except ValueError:
                    raise ImageError(f"línea {ln}: valor inválido para formato {fmt}: {tok!r}") from None
                if not 0 <= v <= 0xFFFF:
                    raise ImageError(f"línea {ln}: valor fuera de 16 bits: {tok!r}")
                words.append(v)
        return cls.from_words(words)

    @classmethod
    def load(cls, path: str | Path, fmt: str | None = None) -> "Image":
        path = Path(path)
        fmt = fmt or path.suffix.lstrip(".").lower()
        if fmt == "bin":
            return cls.from_bytes(path.read_bytes())
        if fmt in FORMATS:
            return cls.from_text(path.read_text(encoding="ascii"), fmt)
        raise ImageError(f"no se reconoce el formato de {path.name}; use .bin, .hex, .dec o .bits (o --format)")
