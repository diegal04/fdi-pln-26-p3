#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "typer>=0.12.0",
# ]
# ///
"""Conversor UTF-8 <-> PLNCG26.

PLNCG26 codifica letras/dígitos/puntuación en un plano de bytes específico.
Las mayúsculas y varios diacríticos (tilde, diéresis y ñ) se representan como
modificadores sobre el carácter base inmediatamente anterior.
"""

from __future__ import annotations

from pathlib import Path
import sys

import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)

# --- Bloques base del plano PLNCG26 ---
NEWLINE_BYTE = 10
SPACE_BYTE = 11
LETTER_START = 20
LETTER_END = 45
DIGIT_START = 60
DIGIT_END = 69

MOD_ACUTE = 50
MOD_DIAERESIS = 51
MOD_ENIE = 52
MOD_UPPER = 53
MODIFIER_BYTES = {MOD_ACUTE, MOD_DIAERESIS, MOD_ENIE, MOD_UPPER}

BYTE_TO_PUNCT = {
    70: ".",
    71: ",",
    72: ";",
    73: ":",
    74: "¿",
    75: "?",
    76: "¡",
    77: "!",
    78: "-",
    79: "'",
    80: '"',
    81: "(",
    82: ")",
    100: "#",
    101: "*",
}
PUNCT_TO_BYTE = {char: code for code, char in BYTE_TO_PUNCT.items()}

ACUTE_MAP = {
    "a": "á",
    "e": "é",
    "i": "í",
    "o": "ó",
    "u": "ú",
    "A": "Á",
    "E": "É",
    "I": "Í",
    "O": "Ó",
    "U": "Ú",
}
DIAERESIS_MAP = {
    "u": "ü",
    "U": "Ü",
}
ENIE_MAP = {
    "n": "ñ",
    "N": "Ñ",
}

# (base_letter, needs_upper_modifier, trailing_modifier)
SPECIAL_CHAR_ENCODING = {
    "á": ("a", False, MOD_ACUTE),
    "é": ("e", False, MOD_ACUTE),
    "í": ("i", False, MOD_ACUTE),
    "ó": ("o", False, MOD_ACUTE),
    "ú": ("u", False, MOD_ACUTE),
    "Á": ("a", True, MOD_ACUTE),
    "É": ("e", True, MOD_ACUTE),
    "Í": ("i", True, MOD_ACUTE),
    "Ó": ("o", True, MOD_ACUTE),
    "Ú": ("u", True, MOD_ACUTE),
    "ü": ("u", False, MOD_DIAERESIS),
    "Ü": ("u", True, MOD_DIAERESIS),
    "ñ": ("n", False, MOD_ENIE),
    "Ñ": ("n", True, MOD_ENIE),
}

KNOWN_PLNCG26_BYTES = (
    set(range(LETTER_START, LETTER_END + 1))
    | set(range(DIGIT_START, DIGIT_END + 1))
    | {NEWLINE_BYTE, SPACE_BYTE}
    | MODIFIER_BYTES
    | set(BYTE_TO_PUNCT)
)


class DecodeError(ValueError):
    """Error de decodificación de bytes PLNCG26."""


class EncodeError(ValueError):
    """Error de codificación de UTF-8 a PLNCG26."""


def _append_base_letter(encoded: bytearray, base_letter: str, uppercase: bool) -> None:
    encoded.append(LETTER_START + ord(base_letter) - ord("a"))
    if uppercase:
        encoded.append(MOD_UPPER)


def _decode_non_modifier_byte(byte: int) -> str | None:
    """Decodifica un byte que no sea modificador; devuelve None si no aplica."""
    if byte == NEWLINE_BYTE:
        return "\n"
    if byte == SPACE_BYTE:
        return " "
    if LETTER_START <= byte <= LETTER_END:
        return chr(ord("a") + byte - LETTER_START)
    if DIGIT_START <= byte <= DIGIT_END:
        return chr(ord("0") + byte - DIGIT_START)
    if byte in BYTE_TO_PUNCT:
        return BYTE_TO_PUNCT[byte]
    return None


def _apply_mapped_modifier(
    out: list[str],
    mapping: dict[str, str],
    label: str,
    idx: int,
    byte: int,
    *,
    strict: bool,
) -> bool:
    if out and out[-1] in mapping:
        out[-1] = mapping[out[-1]]
        return True
    if strict:
        raise DecodeError(
            f"modificador de {label} inválido en byte {idx} (valor {byte})"
        )
    return False


def _apply_modifier(out: list[str], byte: int, idx: int, *, strict: bool) -> bool:
    """Aplica un modificador PLNCG26 sobre el último carácter ya decodificado."""
    if byte == MOD_UPPER:
        if out and out[-1].isalpha():
            out[-1] = out[-1].upper()
            return True
        if strict:
            raise DecodeError(
                f"modificador de mayúsculas inválido en byte {idx} (valor {byte})"
            )
        return False

    if byte == MOD_ACUTE:
        return _apply_mapped_modifier(out, ACUTE_MAP, "tilde", idx, byte, strict=strict)

    if byte == MOD_DIAERESIS:
        return _apply_mapped_modifier(
            out, DIAERESIS_MAP, "diéresis", idx, byte, strict=strict
        )

    if byte == MOD_ENIE:
        return _apply_mapped_modifier(out, ENIE_MAP, "ñ", idx, byte, strict=strict)

    raise ValueError(f"byte {byte} no es un modificador")


def decode_plncg26(data: bytes, *, strict: bool = True) -> str:
    """Decodifica bytes PLNCG26 a texto Unicode."""
    out: list[str] = []

    for idx, byte in enumerate(data):
        decoded = _decode_non_modifier_byte(byte)
        if decoded is not None:
            out.append(decoded)
            continue

        if byte in MODIFIER_BYTES:
            _apply_modifier(out, byte, idx, strict=strict)
            continue

        if strict:
            raise DecodeError(f"byte fuera del plano PLNCG26 en posición {idx}: {byte}")

    return "".join(out)


def encode_utf8_to_plncg26(text: str) -> bytes:
    """Codifica texto Unicode en bytes PLNCG26."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    encoded = bytearray()

    for idx, char in enumerate(normalized):
        if char == "\n":
            encoded.append(NEWLINE_BYTE)
            continue

        if char == " ":
            encoded.append(SPACE_BYTE)
            continue

        if "a" <= char <= "z":
            encoded.append(LETTER_START + ord(char) - ord("a"))
            continue

        if "A" <= char <= "Z":
            _append_base_letter(encoded, char.lower(), uppercase=True)
            continue

        if char.isdigit():
            encoded.append(DIGIT_START + ord(char) - ord("0"))
            continue

        if char in PUNCT_TO_BYTE:
            encoded.append(PUNCT_TO_BYTE[char])
            continue

        # En PLNCG26, estas letras se codifican como base + modificador(es).
        if char in SPECIAL_CHAR_ENCODING:
            base, use_upper, modifier = SPECIAL_CHAR_ENCODING[char]
            _append_base_letter(encoded, base, uppercase=use_upper)
            encoded.append(modifier)
            continue

        raise EncodeError(f"carácter no soportado en posición {idx}: {char!r}")

    return bytes(encoded)


def detect_plncg26_probability(data: bytes) -> float:
    """Heurística simple de detección de PLNCG26 (0.0 a 1.0)."""
    if not data:
        return 0.0

    valid_byte_ratio = sum(1 for b in data if b in KNOWN_PLNCG26_BYTES) / len(data)

    modifier_total = 0
    modifier_ok = 0
    preview_out: list[str] = []

    for idx, byte in enumerate(data):
        decoded = _decode_non_modifier_byte(byte)
        if decoded is not None:
            preview_out.append(decoded)
            continue

        if byte in MODIFIER_BYTES:
            modifier_total += 1
            if _apply_modifier(preview_out, byte, idx, strict=False):
                modifier_ok += 1

    modifier_ratio = 1.0 if modifier_total == 0 else modifier_ok / modifier_total

    decoded_preview = decode_plncg26(data, strict=False)
    printable_ratio = sum(
        1 for char in decoded_preview if char.isprintable() or char in {"\n", "\t"}
    ) / max(len(decoded_preview), 1)

    # Peso principal al ajuste al plano de bytes; secundarios a coherencia de
    # modificadores y legibilidad del resultado.
    probability = (
        (0.65 * valid_byte_ratio) + (0.25 * modifier_ratio) + (0.10 * printable_ratio)
    )
    return max(0.0, min(1.0, probability))


def _read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def _fail(message: str) -> None:
    typer.echo(message, err=True)
    raise typer.Exit(code=1)


@app.command("decode")
def decode_command(
    fichero: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
) -> None:
    """Convierte un fichero PLNCG26 a UTF-8 y lo escribe en stdout."""
    try:
        data = _read_bytes(fichero)
        text = decode_plncg26(data, strict=True)
    except OSError as exc:
        _fail(f"decode error: no se pudo leer el fichero ({exc})")
    except DecodeError as exc:
        _fail(f"decode error: {exc}")

    sys.stdout.buffer.write(text.encode("utf-8"))


@app.command("encode")
def encode_command(
    fichero: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
) -> None:
    """Convierte un fichero UTF-8 a PLNCG26 y lo escribe en stdout."""
    try:
        raw = _read_bytes(fichero)
        text = raw.decode("utf-8")
        encoded = encode_utf8_to_plncg26(text)
    except OSError as exc:
        _fail(f"encode error: no se pudo leer el fichero ({exc})")
    except UnicodeDecodeError as exc:
        _fail(f"encode error: el fichero no es UTF-8 válido ({exc})")
    except EncodeError as exc:
        _fail(f"encode error: {exc}")

    sys.stdout.buffer.write(encoded)


@app.command("detect")
def detect_command(
    fichero: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
) -> None:
    """Calcula la probabilidad de que el fichero contenga PLNCG26."""
    try:
        data = _read_bytes(fichero)
    except OSError as exc:
        _fail(f"detect error: no se pudo leer el fichero ({exc})")

    probability = detect_plncg26_probability(data)
    typer.echo(f"{probability:.4f}")


if __name__ == "__main__":
    app()
