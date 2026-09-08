"""Scene -> SVG."""

from scene import Circle, Ellipse, Group, Line, Rect, Scene, Text

CSS = """
.tool, .node { cursor: pointer; }
.tool rect:first-of-type, .node circle { transition: transform .12s ease, filter .12s ease; }
.tool:hover rect:first-of-type, .node:hover circle:first-of-type { filter: brightness(.96); }
.node:focus-visible circle, .tool:focus-visible rect:first-of-type {
  outline: 3px solid #111827; outline-offset: 3px;
}
a { text-decoration: none; }
text { font-family: %s; }
"""


def num(value):
    if value == int(value):
        return str(int(value))
    return ("%.2f" % value).rstrip("0").rstrip(".")


def esc(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))


def render(scene: Scene, font_family: str, standalone: bool = True, title: str = "") -> str:
    body = "".join(_shape(child) for child in scene.children)
    head = [
        'viewBox="0 0 %s %s"' % (num(scene.width), num(scene.height)),
        'width="100%"',
        'role="img"',
    ]
    if title:
        head.append('aria-label="%s"' % esc(title))
    if standalone:
        head.insert(0, 'xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"')
    out = ["<svg %s>" % " ".join(head)]
    if title:
        out.append("<title>%s</title>" % esc(title))
    out.append("<style>%s</style>" % (CSS % font_family).strip())
    out.append('<rect width="%s" height="%s" fill="%s"/>'
               % (num(scene.width), num(scene.height), scene.background))
    out.append(body)
    out.append("</svg>")
    return "".join(out)


def _shape(shape) -> str:
    if isinstance(shape, Group):
        inner = "".join(_shape(child) for child in shape.children)
        attrs = ""
        if shape.cls:
            attrs += ' class="%s"' % shape.cls
        if shape.href:
            title = "<title>%s</title>" % esc(shape.title) if shape.title else ""
            return '<a href="%s" target="_blank" rel="noopener"%s>%s%s</a>' % (
                esc(shape.href), attrs, title, inner)
        return "<g%s>%s</g>" % (attrs, inner)

    if isinstance(shape, Rect):
        parts = ['x="%s" y="%s" width="%s" height="%s"' % (
            num(shape.x), num(shape.y), num(shape.w), num(shape.h))]
        if shape.r:
            parts.append('rx="%s"' % num(shape.r))
        parts.append('fill="%s"' % (shape.fill or "none"))
        if shape.stroke:
            parts.append('stroke="%s" stroke-width="%s"' % (shape.stroke, num(shape.stroke_width)))
        return "<rect %s/>" % " ".join(parts)

    if isinstance(shape, Circle):
        parts = ['cx="%s" cy="%s" r="%s"' % (num(shape.cx), num(shape.cy), num(shape.r))]
        parts.append('fill="%s"' % (shape.fill or "none"))
        if shape.stroke:
            parts.append('stroke="%s" stroke-width="%s"' % (shape.stroke, num(shape.stroke_width)))
        return "<circle %s/>" % " ".join(parts)

    if isinstance(shape, Ellipse):
        parts = ['cx="%s" cy="%s" rx="%s" ry="%s"' % (
            num(shape.cx), num(shape.cy), num(shape.rx), num(shape.ry))]
        parts.append('fill="%s"' % (shape.fill or "none"))
        if shape.stroke:
            parts.append('stroke="%s" stroke-width="%s"' % (shape.stroke, num(shape.stroke_width)))
        return "<ellipse %s/>" % " ".join(parts)

    if isinstance(shape, Line):
        return ('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" '
                'stroke-linecap="%s"/>' % (num(shape.x1), num(shape.y1), num(shape.x2),
                                           num(shape.y2), shape.stroke,
                                           num(shape.stroke_width), shape.cap))

    if isinstance(shape, Text):
        parts = ['x="%s" y="%s"' % (num(shape.x), num(shape.y)),
                 'font-size="%s"' % num(shape.size),
                 'fill="%s"' % shape.fill]
        if shape.bold:
            parts.append('font-weight="700"')
        if shape.anchor != "start":
            parts.append('text-anchor="%s"' % shape.anchor)
        if shape.rotate:
            parts.append('transform="rotate(%s %s %s)"'
                         % (num(shape.rotate), num(shape.x), num(shape.y)))
        if shape.halo:
            parts.append('stroke="%s" stroke-width="%s" stroke-linejoin="round" '
                         'paint-order="stroke"' % (shape.halo, num(shape.halo_width)))
        return "<text %s>%s</text>" % (" ".join(parts), esc(shape.text))

    raise TypeError("Unbekannte Form: %r" % shape)
