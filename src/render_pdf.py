"""Scene -> PDF (Vektor, A3 quer) – ohne externe Bibliotheken.

Erzeugt einen minimalen, aber gültigen PDF-1.4-Datenstrom: eine Seite, ein
komprimierter Content-Stream, die eingebauten Standardschriften Helvetica und
Helvetica-Bold (also keine eingebetteten Fonts -> sehr kleine Datei) sowie
Link-Annotationen für alle klickbaren Elemente.
"""

import math
import zlib

import metrics
from scene import Circle, Ellipse, Group, Line, Rect, Text, hex_to_rgb

KAPPA = 0.5522847498
PAGE_SIZES = {           # Breite x Höhe in Punkt (1 pt = 1/72 Zoll)
    "A3-landscape": (1190.55, 841.89),
    "A2-landscape": (1683.78, 1190.55),
    "A4-landscape": (841.89, 595.28),
}


def render(scene, page="A3-landscape", margin=20.0) -> bytes:
    page_w, page_h = PAGE_SIZES[page]
    scale = min((page_w - 2 * margin) / scene.width,
                (page_h - 2 * margin) / scene.height)
    tx = (page_w - scale * scene.width) / 2
    ty = page_h - (page_h - scale * scene.height) / 2

    def to_pdf(x, y):
        return tx + scale * x, ty - scale * y

    ops = ["q", "%s 0 0 %s %s %s cm" % (_n(scale), _n(-scale), _n(tx), _n(ty))]
    ops.append("%s %s %s rg 0 0 %s %s re f"
               % (_rgb(scene.background) + (_n(scene.width), _n(scene.height))))
    links = []
    for child in scene.children:
        _emit(child, ops, links, None)
    ops.append("Q")

    content = zlib.compress(("\n".join(ops)).encode("latin-1", "replace"))

    annots = []
    for href, rect in links:
        x0, y0 = to_pdf(rect[0], rect[1])
        x1, y1 = to_pdf(rect[0] + rect[2], rect[1] + rect[3])
        annots.append((href, (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))))

    return _assemble(page_w, page_h, content, annots)


# ------------------------------------------------------------- Formen -> Ops

def _emit(shape, ops, links, href):
    if isinstance(shape, Group):
        current = shape.href or href
        bounds = []
        for child in shape.children:
            _emit(child, ops, links, current)
            b = _bounds(child)
            if b:
                bounds.append(b)
        if shape.href and bounds:
            x0 = min(b[0] for b in bounds)
            y0 = min(b[1] for b in bounds)
            x1 = max(b[2] for b in bounds)
            y1 = max(b[3] for b in bounds)
            links.append((shape.href, (x0, y0, x1 - x0, y1 - y0)))
        return

    if isinstance(shape, Rect):
        _round_rect(ops, shape.x, shape.y, shape.w, shape.h, shape.r)
        _paint(ops, shape.fill, shape.stroke, shape.stroke_width)
    elif isinstance(shape, Circle):
        _ellipse(ops, shape.cx, shape.cy, shape.r, shape.r)
        _paint(ops, shape.fill, shape.stroke, shape.stroke_width)
    elif isinstance(shape, Ellipse):
        _ellipse(ops, shape.cx, shape.cy, shape.rx, shape.ry)
        _paint(ops, shape.fill, shape.stroke, shape.stroke_width)
    elif isinstance(shape, Line):
        ops.append("%s %s %s RG %s w 1 J" % (_rgb(shape.stroke) + (_n(shape.stroke_width),)))
        ops.append("%s %s m %s %s l S" % (_n(shape.x1), _n(shape.y1), _n(shape.x2), _n(shape.y2)))
    elif isinstance(shape, Text):
        _text(ops, shape)
    else:
        raise TypeError("Unbekannte Form: %r" % shape)


def _bounds(shape):
    if isinstance(shape, Rect):
        return (shape.x, shape.y, shape.x + shape.w, shape.y + shape.h)
    if isinstance(shape, Circle):
        return (shape.cx - shape.r, shape.cy - shape.r, shape.cx + shape.r, shape.cy + shape.r)
    if isinstance(shape, Group):
        inner = [_bounds(c) for c in shape.children]
        inner = [b for b in inner if b]
        if not inner:
            return None
        return (min(b[0] for b in inner), min(b[1] for b in inner),
                max(b[2] for b in inner), max(b[3] for b in inner))
    return None


def _paint(ops, fill, stroke, width):
    if fill:
        ops.append("%s %s %s rg" % _rgb(fill))
    if stroke:
        ops.append("%s %s %s RG %s w" % (_rgb(stroke) + (_n(width),)))
    if fill and stroke:
        ops.append("B")
    elif fill:
        ops.append("f")
    elif stroke:
        ops.append("S")
    else:
        ops.append("n")


def _round_rect(ops, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    if r <= 0:
        ops.append("%s %s %s %s re" % (_n(x), _n(y), _n(w), _n(h)))
        return
    k = r * KAPPA
    ops.append("%s %s m" % (_n(x + r), _n(y)))
    ops.append("%s %s l" % (_n(x + w - r), _n(y)))
    ops.append("%s %s %s %s %s %s c" % (_n(x + w - r + k), _n(y), _n(x + w), _n(y + r - k),
                                        _n(x + w), _n(y + r)))
    ops.append("%s %s l" % (_n(x + w), _n(y + h - r)))
    ops.append("%s %s %s %s %s %s c" % (_n(x + w), _n(y + h - r + k), _n(x + w - r + k),
                                        _n(y + h), _n(x + w - r), _n(y + h)))
    ops.append("%s %s l" % (_n(x + r), _n(y + h)))
    ops.append("%s %s %s %s %s %s c" % (_n(x + r - k), _n(y + h), _n(x), _n(y + h - r + k),
                                        _n(x), _n(y + h - r)))
    ops.append("%s %s l" % (_n(x), _n(y + r)))
    ops.append("%s %s %s %s %s %s c" % (_n(x), _n(y + r - k), _n(x + r - k), _n(y),
                                        _n(x + r), _n(y)))
    ops.append("h")


def _ellipse(ops, cx, cy, rx, ry):
    kx, ky = rx * KAPPA, ry * KAPPA
    ops.append("%s %s m" % (_n(cx + rx), _n(cy)))
    ops.append("%s %s %s %s %s %s c" % (_n(cx + rx), _n(cy + ky), _n(cx + kx), _n(cy + ry), _n(cx), _n(cy + ry)))
    ops.append("%s %s %s %s %s %s c" % (_n(cx - kx), _n(cy + ry), _n(cx - rx), _n(cy + ky), _n(cx - rx), _n(cy)))
    ops.append("%s %s %s %s %s %s c" % (_n(cx - rx), _n(cy - ky), _n(cx - kx), _n(cy - ry), _n(cx), _n(cy - ry)))
    ops.append("%s %s %s %s %s %s c" % (_n(cx + kx), _n(cy - ry), _n(cx + rx), _n(cy - ky), _n(cx + rx), _n(cy)))
    ops.append("h")


def _text(ops, shape):
    text = metrics.sanitize(shape.text)
    if not text.strip():
        return
    width = metrics.text_width(text, shape.size, shape.bold)
    offset = {"start": 0.0, "middle": -width / 2, "end": -width}[shape.anchor]
    rad = math.radians(shape.rotate)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    x = shape.x + cos_a * offset
    y = shape.y + sin_a * offset
    font = "/F2" if shape.bold else "/F1"
    matrix = "%s %s %s %s %s %s Tm" % (_n(cos_a), _n(sin_a), _n(sin_a), _n(-cos_a), _n(x), _n(y))
    escaped = _pdf_string(text)

    ops.append("BT")
    ops.append("%s %s Tf" % (font, _n(shape.size)))
    if shape.halo:
        # Kontur zuerst (Textrendermodus 1 = nur Strich), damit der Text auf
        # Linien und Flächen lesbar bleibt.
        ops.append(matrix)
        ops.append("%s %s %s RG %s w 1 j 1 J" % (_rgb(shape.halo) + (_n(shape.halo_width),)))
        ops.append("1 Tr")
        ops.append("%s Tj" % escaped)
        ops.append("0 Tr")
    # Tm neu setzen: Tj hat die Textposition weitergeschoben.
    ops.append(matrix)
    ops.append("%s %s %s rg" % _rgb(shape.fill))
    ops.append("%s Tj" % escaped)
    ops.append("ET")


# ------------------------------------------------------------- PDF-Gerüst

def _pdf_string(text):
    data = text.encode("cp1252", "replace")
    out = bytearray(b"(")
    for byte in data:
        if byte in (0x28, 0x29, 0x5C):
            out += b"\\" + bytes([byte])
        elif byte < 32 or byte > 126:
            out += ("\\%03o" % byte).encode("ascii")
        else:
            out.append(byte)
    out += b")"
    return out.decode("latin-1")


def _assemble(page_w, page_h, content, annots):
    objects = {}
    annot_ids = []
    next_id = 7
    for href, rect in annots:
        annot_ids.append(next_id)
        objects[next_id] = (
            "<< /Type /Annot /Subtype /Link /Border [0 0 0] "
            "/Rect [%s %s %s %s] /A << /Type /Action /S /URI /URI %s >> >>"
            % (_n(rect[0]), _n(rect[1]), _n(rect[2]), _n(rect[3]), _pdf_string(href))
        ).encode("latin-1")
        next_id += 1

    annots_ref = ""
    if annot_ids:
        annots_ref = " /Annots [%s]" % " ".join("%d 0 R" % i for i in annot_ids)

    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[2] = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
    objects[3] = ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %s %s] "
                  "/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> "
                  "/Contents 4 0 R%s >>" % (_n(page_w), _n(page_h), annots_ref)).encode("latin-1")
    objects[4] = (b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(content)
                  + content + b"\nendstream")
    objects[5] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    objects[6] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += b"%d 0 obj\n" % num + objects[num] + b"\nendobj\n"

    xref_pos = len(out)
    count = max(objects) + 1
    out += b"xref\n0 %d\n" % count
    out += b"0000000000 65535 f \n"
    for num in range(1, count):
        out += b"%010d 00000 n \n" % offsets.get(num, 0)
    out += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (count, xref_pos))
    return bytes(out)


def _n(value):
    if abs(value) < 1e-6:
        return "0"
    return ("%.3f" % value).rstrip("0").rstrip(".")


def _rgb(color):
    return tuple(_n(c) for c in hex_to_rgb(color))
