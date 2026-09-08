"""Renderer-unabhängiges Zeichenmodell.

Das Layout erzeugt eine flache Liste solcher Formen; die Renderer (SVG, PDF)
kennen nur diese wenigen Typen. Wer eine neue Ausgabe bauen will, muss nur
diese Klassen unterstützen.

Koordinatensystem: Ursprung oben links, y wächst nach unten (wie in SVG).
Text-y ist immer die Grundlinie (Baseline).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Rect:
    x: float
    y: float
    w: float
    h: float
    r: float = 0.0
    fill: Optional[str] = None
    stroke: Optional[str] = None
    stroke_width: float = 1.0


@dataclass
class Circle:
    cx: float
    cy: float
    r: float
    fill: Optional[str] = None
    stroke: Optional[str] = None
    stroke_width: float = 1.0


@dataclass
class Ellipse:
    cx: float
    cy: float
    rx: float
    ry: float
    fill: Optional[str] = None
    stroke: Optional[str] = None
    stroke_width: float = 1.0


@dataclass
class Line:
    x1: float
    y1: float
    x2: float
    y2: float
    stroke: str = "#000000"
    stroke_width: float = 1.0
    cap: str = "round"


@dataclass
class Text:
    x: float
    y: float
    text: str
    size: float = 14.0
    bold: bool = False
    fill: str = "#111111"
    anchor: str = "start"          # start | middle | end
    rotate: float = 0.0            # Grad, im Uhrzeigersinn um (x, y)
    halo: Optional[str] = None     # Farbe einer Kontur hinter dem Text
    halo_width: float = 5.0


@dataclass
class Group:
    """Bündelt Formen, optional als Hyperlink und/oder mit CSS-Klasse."""
    children: List[object] = field(default_factory=list)
    href: Optional[str] = None
    cls: Optional[str] = None
    title: Optional[str] = None

    def add(self, *shapes):
        self.children.extend(shapes)
        return self


@dataclass
class Scene:
    width: float
    height: float
    background: str = "#FFFFFF"
    children: List[object] = field(default_factory=list)

    def add(self, *shapes):
        self.children.extend(shapes)
        return self


# ---------------------------------------------------------------- Farbhilfen

def hex_to_rgb(color: str) -> Tuple[float, float, float]:
    color = color.lstrip("#")
    if len(color) == 3:
        color = "".join(c * 2 for c in color)
    return tuple(int(color[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def mix(color: str, other: str, t: float) -> str:
    """Mischt zwei Farben (t = 0 -> color, t = 1 -> other) und gibt Hex zurück.

    Wird benutzt statt Transparenz, damit SVG und PDF garantiert gleich aussehen.
    """
    a, b = hex_to_rgb(color), hex_to_rgb(other)
    out = [round(255 * (a[i] + (b[i] - a[i]) * t)) for i in range(3)]
    return "#%02X%02X%02X" % tuple(out)
