"""
Script para descifrar el archivo cifrado con un cifrado tipo César.

Estructura detectada en el archivo:
  - Byte 10  → salto de línea
  - Byte 11  → espacio
  - Bytes 20–45 → letras (rango de 26 valores, exactamente el alfabeto)
  - Bytes 50–53, 70 → caracteres especiales (letras acentuadas, puntuación, etc.)
"""

import os
from collections import Counter

ARCHIVO = os.path.join(os.path.dirname(__file__), "binarios", "principal.bin")

# Palabras españolas comunes para puntuar candidatos
# Bytes especiales (detectados analizando el contexto del texto)
# 50 = diacrítico de tilde (modifica la vocal anterior: a→á, e→é, i→í, o→ó, u→ú)
# 51 = diacrítico de diéresis (modifica la vocal anterior: u→ü)
# 52 = ñ  (carácter independiente)
# 53 = mayúscula (modifica la letra anterior convirtiéndola en mayúscula)
# 70 = punto '.'
ACENTO  = {'a': 'á', 'e': 'é', 'i': 'í', 'o': 'ó', 'u': 'ú'}
DIERESIS = {'u': 'ü'}
ENIE    = {'n': 'ñ'}  # 52 convierte n→ñ (como 50/51 convierten vocales)

PALABRAS_COMUNES = {
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "de", "del", "en", "a", "y", "que", "se", "es", "su",
    "con", "por", "como", "no", "si", "lo", "le", "me",
    "te", "mi", "tu", "al", "más", "pero", "o", "ni",
    "ha", "hay", "fue", "son",
}

def puntuar(texto: str) -> int:
    """Puntuación: cuenta cuántas palabras comunes aparecen en el texto."""
    palabras = texto.lower().split()
    return sum(1 for p in palabras if p.strip(".,;:!¡?¿-") in PALABRAS_COMUNES)


def decodificar_cesar_bytes(datos: bytes, offset: int) -> str:
    """
    Cifrado César puro sobre bytes:
      - 10 y 11 se tratan como salto de línea y espacio respectivamente.
      - El resto: decoded_byte = (byte + offset) % 256
    """
    resultado = []
    for b in datos:
        if b == 10:
            resultado.append("\n")
        elif b == 11:
            resultado.append(" ")
        else:
            c = (b + offset) % 256
            try:
                resultado.append(chr(c))
            except Exception:
                resultado.append("?")
    return "".join(resultado)


def decodificar_cesar_letras(datos: bytes, offset: int) -> str:
    """
    Cifrado César solo sobre el rango de letras (módulo 26).
    Asume que los valores del archivo en rango [20,45] son letras a-z desplazadas.
    offset aquí representa el desplazamiento dentro del alfabeto (0–25).
    """
    resultado = []
    for b in datos:
        if b == 10:
            resultado.append("\n")
        elif b == 11:
            resultado.append(" ")
        elif 20 <= b <= 45:
            # letra codificada: posición = b - 20  (0=a, 25=z)
            pos = (b - 20 + offset) % 26
            resultado.append(chr(ord("a") + pos))
        else:
            # byte especial (acentos, puntuación…): intentar desplazamiento simple
            c = (b + offset) % 256
            try:
                resultado.append(chr(c))
            except Exception:
                resultado.append("?")
    return "".join(resultado)


def main():
    with open(ARCHIVO, "rb") as f:
        datos = f.read()

    print(f"Archivo: {ARCHIVO}")
    print(f"Bytes totales: {len(datos)}")
    print(f"Valores únicos: {sorted(set(datos))}\n")

    # ─── MÉTODO 1: César puro sobre bytes (offset 0–255) ─────────────────────
    print("=" * 70)
    print("MÉTODO 1 — César sobre bytes completos (offset aditivo mod 256)")
    print("=" * 70)

    candidatos_bytes = []
    for offset in range(256):
        texto = decodificar_cesar_bytes(datos, offset)
        puntos = puntuar(texto)
        # filtro: al menos el 70% de los chars deben ser imprimibles
        imprimibles = sum(1 for c in texto if c.isprintable() or c in "\n ")
        if imprimibles / max(len(texto), 1) >= 0.70:
            candidatos_bytes.append((puntos, offset, texto))

    candidatos_bytes.sort(reverse=True)
    for puntos, offset, texto in candidatos_bytes[:5]:
        print(f"\n  Offset={offset:3d} | Puntuación={puntos}")
        print(f"  {repr(texto[:120])}")

    # ─── MÉTODO 2: César solo sobre letras (módulo 26) ───────────────────────
    print("\n" + "=" * 70)
    print("MÉTODO 2 — César sobre letras (mod 26, rango [20–45] → a–z)")
    print("=" * 70)

    candidatos_letras = []
    for offset in range(26):
        texto = decodificar_cesar_letras(datos, offset)
        puntos = puntuar(texto)
        candidatos_letras.append((puntos, offset, texto))

    candidatos_letras.sort(reverse=True)
    for puntos, offset, texto in candidatos_letras[:5]:
        print(f"\n  Offset={offset:2d} | Puntuación={puntos}")
        print(f"  {repr(texto[:120])}")

    # ─── MEJOR CANDIDATO GLOBAL ───────────────────────────────────────────────
    todos = candidatos_bytes + candidatos_letras
    todos.sort(reverse=True)
    mejor_puntos, mejor_offset, mejor_texto = todos[0]

    print("\n" + "=" * 70)
    print("MEJOR CANDIDATO GLOBAL")
    print("=" * 70)
    print(f"Offset={mejor_offset} | Puntuación={mejor_puntos}")
    print()
    print(mejor_texto)

    # ─── DECODIFICACIÓN LIMPIA CON TABLA DE ESPECIALES ────────────────────────
    print("\n" + "=" * 70)
    print("DECODIFICACIÓN LIMPIA (offset=77 + modificadores diacríticos)")
    print("=" * 70)

    OFFSET = 77
    resultado_limpio = []
    i = 0
    while i < len(datos):
        b = datos[i]
        if b == 10:
            resultado_limpio.append("\n")
        elif b == 11:
            resultado_limpio.append(" ")
        elif b == 70:
            resultado_limpio.append(".")
        elif b == 52:
            # eñe: convierte n→ñ en la letra anterior
            if resultado_limpio and resultado_limpio[-1] in ENIE:
                resultado_limpio[-1] = ENIE[resultado_limpio[-1]]
            else:
                resultado_limpio.append("ñ")
        elif b == 50:
            # tilde sobre la vocal anterior
            if resultado_limpio and resultado_limpio[-1] in ACENTO:
                resultado_limpio[-1] = ACENTO[resultado_limpio[-1]]
            else:
                resultado_limpio.append("´")  # acento suelto si no hay vocal previa
        elif b == 51:
            # diéresis sobre la vocal anterior
            if resultado_limpio and resultado_limpio[-1] in DIERESIS:
                resultado_limpio[-1] = DIERESIS[resultado_limpio[-1]]
            else:
                resultado_limpio.append("¨")
        elif b == 53:
            # mayúscula de la letra anterior
            if resultado_limpio:
                resultado_limpio[-1] = resultado_limpio[-1].upper()
        else:
            resultado_limpio.append(chr(b + OFFSET))
        i += 1

    texto_final = "".join(resultado_limpio)
    print(texto_final)
    print(f"\nOffset correcto: {OFFSET}")


if __name__ == "__main__":
    main()
