"""Normalización de texto para buscar etiquetas sin depender de tildes, espacios ni mayúsculas."""
import re
import unicodedata


def norm(text) -> str:
    if text is None:
        return ""
    s = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


def col_letter(c: int) -> str:
    s = ""
    while c:
        c, rem = divmod(c - 1, 26)
        s = chr(65 + rem) + s
    return s


def cell_ref(r: int, c: int) -> str:
    return f"{col_letter(c)}{r}"
