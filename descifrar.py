"""
Script para descifrar el archivo cifrado con un cifrado tipo César.

Estructura detectada en el archivo:
  - Byte 10  → salto de línea
  - Byte 11  → espacio
  - Bytes 20–45 → letras (rango de 26 valores, exactamente el alfabeto)
  - Bytes 50–53, 70 → caracteres especiales (letras acentuadas, puntuación, etc.)
"""

import os

CARPETA = os.path.join(os.path.dirname(__file__), "binarios")

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


def descifrar_limpio(datos: bytes, offset: int) -> str:
    """Reconstruye el texto aplicando el offset y la tabla de modificadores diacríticos."""
    resultado = []
    for b in datos:
        if b == 10:
            resultado.append("\n")
        elif b == 11:
            resultado.append(" ")
        elif b == 70:
            resultado.append(".")
        elif b == 52:
            if resultado and resultado[-1] in ENIE:
                resultado[-1] = ENIE[resultado[-1]]
            else:
                resultado.append("ñ")
        elif b == 50:
            if resultado and resultado[-1] in ACENTO:
                resultado[-1] = ACENTO[resultado[-1]]
            else:
                resultado.append("´")
        elif b == 51:
            if resultado and resultado[-1] in DIERESIS:
                resultado[-1] = DIERESIS[resultado[-1]]
            else:
                resultado.append("¨")
        elif b == 53:
            if resultado:
                resultado[-1] = resultado[-1].upper()
        else:
            resultado.append(chr(b + offset))
    return "".join(resultado)


def procesar_archivo(ruta: str) -> None:
    nombre = os.path.basename(ruta)
    print("\n" + "█" * 70)
    print(f"  ARCHIVO: {nombre}")
    print("█" * 70)

    with open(ruta, "rb") as f:
        datos = f.read()

    print(f"  Bytes: {len(datos)} | Valores únicos: {sorted(set(datos))}\n")

    # ── Buscar el mejor offset probando 0–255 ────────────────────────────────
    candidatos = []
    for offset in range(256):
        texto = decodificar_cesar_bytes(datos, offset)
        puntos = puntuar(texto)
        imprimibles = sum(1 for c in texto if c.isprintable() or c in "\n ")
        ratio = imprimibles / max(len(texto), 1)
        if ratio >= 0.70:
            candidatos.append((puntos, offset, texto))

    if not candidatos:
        print("  [!] No se encontró ningún offset válido (archivo posiblemente corrupto o con otro esquema).")
        print(f"  Bytes en crudo: {list(datos)}")
        return

    candidatos.sort(reverse=True)

    print("  Top 3 candidatos (César sobre bytes):")
    for puntos, offset, texto in candidatos[:3]:
        print(f"    Offset={offset:3d} | Puntuación={puntos} | {repr(texto[:80])}")

    mejor_puntos, mejor_offset, _ = candidatos[0]

    print(f"\n  ── Decodificación con offset={mejor_offset} ──")
    print(descifrar_limpio(datos, mejor_offset))


def main():
    archivos = sorted(
        os.path.join(CARPETA, f)
        for f in os.listdir(CARPETA)
        if f.endswith(".bin")
    )

    if not archivos:
        print(f"No se encontraron archivos .bin en {CARPETA}")
        return

    for ruta in archivos:
        procesar_archivo(ruta)



if __name__ == "__main__":
    main()
