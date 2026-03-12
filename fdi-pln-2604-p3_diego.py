# /// script
# requires-python = ">=3.10"
# dependencies = ["typer"]
# ///
"""Conversor entre codificación PLNCG26 (FDI-PLN Criptoglifos 2026) y texto UTF-8."""

import sys
from pathlib import Path

import typer

app = typer.Typer(help="Conversor PLNCG26 ↔ UTF-8")

# ── Constantes de bytes PLNCG26 ─────────────────────────────────────

_NUEVA_LINEA = 10  # salto de línea
_ESPACIO = 11  # espacio en blanco
_LETRA_A = 20  # 'a' .. 'z' = bytes 20..45
_LETRA_Z = 45
_MOD_ACENTO = 50  # modificador de acento (á é í ó ú)
_MOD_DIERESIS = 51  # modificador de diéresis (ü)
_MOD_ENIE = 52  # modificador de eñe (ñ)
_MOD_MAYUS = 53  # modificador de mayúscula
_DIG_CERO = 60  # '0' .. '9' = bytes 60..69
_DIG_NUEVE = 69
_COMILLA_ANG = 80  # comilla angular: alterna « / »

# Tabla de puntuación y caracteres especiales (byte → carácter)
_PUNTUACION: dict[int, str] = {
    70: ".",
    71: ",",
    72: ";",
    73: ":",
    74: "¡",
    75: "!",
    76: "¿",
    77: "?",
    78: "-",
    79: "'",
    # 80 = comilla angular (se gestiona por separado)
    81: "(",
    82: ")",
    100: "#",
    101: '"',
}

# Tabla inversa para codificación (carácter → byte)
_CHAR_A_BYTE: dict[str, int] = {car: byte for byte, car in _PUNTUACION.items()}
_CHAR_A_BYTE["\n"] = _NUEVA_LINEA
_CHAR_A_BYTE[" "] = _ESPACIO

# Tablas de decodificación de modificadores (incluyen variantes en mayúscula)
_ACENTO_DEC: dict[str, str] = {
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
_DIERESIS_DEC: dict[str, str] = {"u": "ü", "U": "Ü"}
_ENIE_DEC: dict[str, str] = {"n": "ñ", "N": "Ñ"}

# Tablas de codificación de modificadores (carácter acentuado → letra base)
_ACENTO_ENC: dict[str, str] = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u"}
_ACENTO_MAY_ENC: dict[str, str] = {
    "Á": "a",
    "É": "e",
    "Í": "i",
    "Ó": "o",
    "Ú": "u",
}

# Conjunto de todos los valores de byte válidos en PLNCG26
_BYTES_VALIDOS: set[int] = (
    {_NUEVA_LINEA, _ESPACIO, _COMILLA_ANG}
    | set(range(_LETRA_A, _LETRA_Z + 1))
    | {_MOD_ACENTO, _MOD_DIERESIS, _MOD_ENIE, _MOD_MAYUS}
    | set(range(_DIG_CERO, _DIG_NUEVE + 1))
    | set(_PUNTUACION)
)


# ── Codec ────────────────────────────────────────────────────────────


def plncg26_decode(datos: bytes) -> str:
    """Decodifica bytes PLNCG26 a cadena UTF-8."""
    resultado: list[str] = []
    comilla_abierta = False

    for byte in datos:
        if _LETRA_A <= byte <= _LETRA_Z:
            # Letra: posición en el alfabeto = byte - 20
            resultado.append(chr(ord("a") + byte - _LETRA_A))
        elif _DIG_CERO <= byte <= _DIG_NUEVE:
            # Dígito: valor = byte - 60
            resultado.append(chr(ord("0") + byte - _DIG_CERO))
        elif byte == _MOD_ACENTO:
            # Modifica la vocal anterior añadiendo tilde
            if resultado and resultado[-1] in _ACENTO_DEC:
                resultado[-1] = _ACENTO_DEC[resultado[-1]]
        elif byte == _MOD_DIERESIS:
            # Modifica la 'u' anterior añadiendo diéresis
            if resultado and resultado[-1] in _DIERESIS_DEC:
                resultado[-1] = _DIERESIS_DEC[resultado[-1]]
        elif byte == _MOD_ENIE:
            # Modifica la 'n' anterior convirtiéndola en 'ñ'
            if resultado and resultado[-1] in _ENIE_DEC:
                resultado[-1] = _ENIE_DEC[resultado[-1]]
            else:
                resultado.append("ñ")
        elif byte == _MOD_MAYUS:
            # Convierte el carácter anterior a mayúscula
            if resultado:
                resultado[-1] = resultado[-1].upper()
        elif byte == _COMILLA_ANG:
            # Alterna entre comilla de apertura « y de cierre »
            resultado.append("«" if not comilla_abierta else "»")
            comilla_abierta = not comilla_abierta
        elif byte == _NUEVA_LINEA:
            resultado.append("\n")
        elif byte == _ESPACIO:
            resultado.append(" ")
        elif byte in _PUNTUACION:
            resultado.append(_PUNTUACION[byte])

    return "".join(resultado)


def plncg26_encode(texto: str) -> bytes:
    """Codifica cadena UTF-8 a bytes PLNCG26."""
    resultado = bytearray()

    for caracter in texto:
        if caracter == "\r":
            # Ignorar retorno de carro (saltos de línea Windows)
            continue
        elif "a" <= caracter <= "z":
            resultado.append(_LETRA_A + ord(caracter) - ord("a"))
        elif "A" <= caracter <= "Z":
            # Mayúscula: emitir letra base seguida del modificador de mayúscula
            resultado.append(_LETRA_A + ord(caracter.lower()) - ord("a"))
            resultado.append(_MOD_MAYUS)
        elif caracter in _ACENTO_ENC:
            # Vocal acentuada minúscula: letra base + modificador de acento
            resultado.append(_LETRA_A + ord(_ACENTO_ENC[caracter]) - ord("a"))
            resultado.append(_MOD_ACENTO)
        elif caracter in _ACENTO_MAY_ENC:
            # Vocal acentuada mayúscula: letra base + mayúscula + acento
            resultado.append(_LETRA_A + ord(_ACENTO_MAY_ENC[caracter]) - ord("a"))
            resultado.append(_MOD_MAYUS)
            resultado.append(_MOD_ACENTO)
        elif caracter == "ñ":
            resultado.append(_LETRA_A + ord("n") - ord("a"))
            resultado.append(_MOD_ENIE)
        elif caracter == "Ñ":
            resultado.append(_LETRA_A + ord("n") - ord("a"))
            resultado.append(_MOD_MAYUS)
            resultado.append(_MOD_ENIE)
        elif caracter == "ü":
            resultado.append(_LETRA_A + ord("u") - ord("a"))
            resultado.append(_MOD_DIERESIS)
        elif caracter == "Ü":
            resultado.append(_LETRA_A + ord("u") - ord("a"))
            resultado.append(_MOD_MAYUS)
            resultado.append(_MOD_DIERESIS)
        elif "0" <= caracter <= "9":
            resultado.append(_DIG_CERO + int(caracter))
        elif caracter in ("«", "»"):
            resultado.append(_COMILLA_ANG)
        elif caracter in _CHAR_A_BYTE:
            resultado.append(_CHAR_A_BYTE[caracter])
        # Variantes Unicode comunes → equivalente PLNCG26
        elif caracter in ("\u2018", "\u2019"):  # comillas simples tipográficas → apostrofo
            resultado.append(79)
        elif caracter in ("\u201c", "\u201d"):  # comillas dobles tipográficas
            resultado.append(101)
        elif caracter in ("\u2013", "\u2014"):  # guion medio / guion largo → guion
            resultado.append(78)

    return bytes(resultado)


def plncg26_detect(datos: bytes) -> float:
    """Devuelve la probabilidad [0, 1] de que *datos* contenga texto PLNCG26."""
    if not datos:
        return 0.0

    total = len(datos)

    # 1) Todos los bytes deben pertenecer al conjunto válido PLNCG26
    num_validos = sum(1 for byte in datos if byte in _BYTES_VALIDOS)
    ratio_validos = num_validos / total
    if ratio_validos < 1.0:
        # Presencia de bytes ilegales → probabilidad muy baja
        return ratio_validos * 0.3

    # 2) Densidad de letras (un texto español natural supera el 50 %)
    num_letras = sum(1 for byte in datos if _LETRA_A <= byte <= _LETRA_Z)
    ratio_letras = num_letras / total

    # 3) Coherencia de modificadores: deben seguir siempre a una letra u otro modificador
    modificadores = {_MOD_ACENTO, _MOD_DIERESIS, _MOD_ENIE, _MOD_MAYUS}
    mod_correctos = 0
    mod_total = 0
    for i, byte in enumerate(datos):
        if byte in modificadores:
            mod_total += 1
            if i > 0 and (_LETRA_A <= datos[i - 1] <= _LETRA_Z or datos[i - 1] in modificadores):
                mod_correctos += 1
    ratio_mod = mod_correctos / mod_total if mod_total > 0 else 1.0

    # 4) Frecuencia de espacios y saltos de línea (texto natural ≈ 15–20 %)
    num_espacios = sum(1 for byte in datos if byte in (_NUEVA_LINEA, _ESPACIO))
    ratio_espacios = num_espacios / total

    puntuacion = (
        0.3 * ratio_validos
        + 0.3 * min(ratio_letras / 0.5, 1.0)
        + 0.2 * ratio_mod
        + 0.2 * min(ratio_espacios / 0.1, 1.0)
    )
    return min(puntuacion, 1.0)


# ── CLI ──────────────────────────────────────────────────────────────


@app.command()
def decode(fichero: Path) -> None:
    """Decodifica un fichero PLNCG26 a texto UTF-8 (salida por stdout)."""
    datos: bytes = fichero.read_bytes()
    texto = plncg26_decode(datos)
    sys.stdout.buffer.write(texto.encode("utf-8"))


@app.command()
def encode(fichero: Path) -> None:
    """Codifica un fichero UTF-8 a PLNCG26 (salida binaria por stdout)."""
    texto = fichero.read_text(encoding="utf-8")
    datos: bytes = plncg26_encode(texto)
    sys.stdout.buffer.write(datos)


@app.command()
def detect(fichero: Path) -> None:
    """Calcula la probabilidad de que un fichero contenga texto PLNCG26."""
    datos: bytes = fichero.read_bytes()
    prob = plncg26_detect(datos)
    typer.echo(f"Probabilidad PLNCG26: {prob:.1%}")


if __name__ == "__main__":
    app()
