"""Textmetrik für Helvetica / Arial (metrisch kompatibel).

Die Breitentabellen stammen aus den Adobe-AFM-Daten der PDF-Standardschriften
(Zeichen 32..255, WinAnsi/cp1252-Kodierung, Einheit: 1/1000 em).

Weil SVG-Ausgabe und PDF-Ausgabe dieselbe Metrik benutzen, sind Zeilenumbrüche
in beiden Formaten exakt identisch.
"""

_HELV = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584, 761, 556, 761, 222, 556, 333, 1000, 556, 556, 333, 1000, 667, 333, 1000, 761, 611, 761, 761, 222, 222, 333, 333, 350, 556, 1000, 333, 1000, 500, 333, 944, 761, 500, 667, 278, 333, 556, 556, 556, 556, 260, 556, 333, 737, 370, 556, 584, 333, 737, 333, 400, 584, 333, 333, 333, 556, 537, 278, 333, 333, 365, 556, 834, 834, 834, 611, 667, 667, 667, 667, 667, 667, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278, 722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611, 556, 556, 556, 556, 556, 556, 889, 500, 556, 556, 556, 556, 278, 278, 278, 278, 556, 556, 556, 556, 556, 556, 556, 584, 611, 556, 556, 556, 556, 500, 556, 500]
_HELV_B = [278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611, 975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556, 333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611, 611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584, 761, 556, 761, 278, 556, 500, 1000, 556, 556, 333, 1000, 667, 333, 1000, 761, 611, 761, 761, 278, 278, 500, 500, 350, 556, 1000, 333, 1000, 556, 333, 944, 761, 500, 667, 278, 333, 556, 556, 556, 556, 280, 556, 333, 737, 370, 556, 584, 333, 737, 333, 400, 584, 333, 333, 333, 611, 556, 278, 333, 333, 365, 556, 834, 834, 834, 611, 722, 722, 722, 722, 722, 722, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278, 722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611, 556, 556, 556, 556, 556, 556, 889, 556, 556, 556, 556, 556, 278, 278, 278, 278, 611, 611, 611, 611, 611, 611, 611, 584, 611, 611, 611, 611, 611, 556, 611, 556]

# Zeichen, die WinAnsi (cp1252) nicht kennt, werden ersetzt.
_FALLBACK = {
    "\u2011": "-",   # non-breaking hyphen
    "\u00ad": "",    # weiches Trennzeichen (nur Umbruchhinweis, siehe wrap())
    "\u00a0": " ",   # geschütztes Leerzeichen
    "\u2009": " ",   # schmales Leerzeichen
    "\u202f": " ",   # schmales geschütztes Leerzeichen
}


def sanitize(text: str) -> str:
    """Ersetzt Zeichen, die WinAnsi nicht darstellen kann.

    WinAnsi kennt mehr als reines Latin-1 (Gedankenstrich, typografische
    Anführungszeichen, Euro-Zeichen ...), deshalb wird zeichenweise geprüft.
    """
    for src, dst in _FALLBACK.items():
        text = text.replace(src, dst)
    out = []
    for ch in text:
        try:
            ch.encode("cp1252")
        except UnicodeEncodeError:
            ch = "?"
        out.append(ch)
    return "".join(out)


def winansi_code(ch: str) -> int:
    """WinAnsi-Bytewert eines Zeichens (Grundlage der Breitentabelle)."""
    try:
        return ch.encode("cp1252")[0]
    except UnicodeEncodeError:
        return 63  # '?'


def char_width(ch: str, bold: bool) -> float:
    code = winansi_code(ch)
    if code < 32:
        code = 32
    table = _HELV_B if bold else _HELV
    return table[code - 32] / 1000.0



def text_width(text: str, size: float, bold: bool = False) -> float:
    return sum(char_width(c, bold) for c in text) * size


def wrap(text: str, size: float, max_width: float, bold: bool = False):
    """Bricht Text auf max_width um. Weiche Trennstellen: Leerzeichen und
    weiches Trennzeichen (U+00AD, in JSON als \\u00ad)."""
    words = text.split(" ")
    lines, current = [], ""
    for word in words:
        candidate = word if not current else current + " " + word
        if text_width(sanitize(candidate), size, bold) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)

    # Zu lange Einzelwörter an weichem Trennzeichen brechen
    result = []
    for line in lines:
        if text_width(sanitize(line), size, bold) <= max_width or "­" not in line:
            result.append(line.replace("­", ""))
            continue
        parts = line.split("­")
        buf = ""
        for i, part in enumerate(parts):
            test = buf + part
            nxt = "-" if i < len(parts) - 1 else ""
            if buf and text_width(sanitize(test + nxt), size, bold) > max_width:
                result.append(buf + "-")
                buf = part
            else:
                buf = test
        if buf:
            result.append(buf)
    return result
