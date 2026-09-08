"""Radiales Graph-Layout.

Alle Positionen werden berechnet – in den Daten stehen keine Koordinaten.
Neues Tool in data/tools.json eintragen, neu bauen, fertig: der Ring ordnet
sich selbst neu.
"""

import math
from urllib.parse import urlparse

import metrics
from scene import Circle, Ellipse, Group, Line, Rect, Scene, Text, mix

WHITE = "#FFFFFF"


# --------------------------------------------------------------- Hilfsmittel

def fit_lines_in_circle(text, radius, max_size, min_size, bold=True, max_lines=3):
    """Größte Schriftgröße finden, bei der der Text in den Kreis passt."""
    size = max_size
    while size >= min_size:
        line_height = size * 1.15
        for lines_allowed in range(1, max_lines + 1):
            usable = _chord_width(radius, lines_allowed, line_height) - 8
            lines = metrics.wrap(text, size, usable, bold)
            if len(lines) <= lines_allowed and all(
                metrics.text_width(metrics.sanitize(l), size, bold) <= usable for l in lines
            ):
                return lines, size, line_height
        size -= 1
    return metrics.wrap(text, min_size, radius * 1.5, bold), min_size, min_size * 1.15


def _chord_width(radius, line_count, line_height):
    """Nutzbare Breite im Kreis für die äußerste von `line_count` Zeilen."""
    outer = (line_count - 1) / 2 * line_height + line_height * 0.5
    inner = max(radius ** 2 - outer ** 2, radius ** 2 * 0.16)
    return 2 * math.sqrt(inner)


def ray_rect_exit(cx, cy, dx, dy, rect):
    """Schnittpunkt eines Strahls (vom Knoten Richtung Karte) mit dem Rechteck."""
    x, y, w, h = rect
    best = None
    for edge_t in _edge_params(cx, cy, dx, dy, x, x + w, y, y + h):
        if edge_t is not None and edge_t > 0 and (best is None or edge_t < best):
            best = edge_t
    if best is None:
        return cx, cy
    return cx + dx * best, cy + dy * best


def _edge_params(cx, cy, dx, dy, left, right, top, bottom):
    out = []
    for value, delta, origin, lo, hi, other_o, other_d in (
        (left, dx, cx, top, bottom, cy, dy),
        (right, dx, cx, top, bottom, cy, dy),
        (top, dy, cy, left, right, cx, dx),
        (bottom, dy, cy, left, right, cx, dx),
    ):
        if abs(delta) < 1e-9:
            out.append(None)
            continue
        t = (value - origin) / delta
        pos = other_o + other_d * t
        out.append(t if lo - 0.5 <= pos <= hi + 0.5 else None)
    return out


def hostname(url):
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


# ------------------------------------------------------------------- Layout

class Layout:
    def __init__(self, data, theme):
        self.data = data
        self.theme = theme
        self.canvas = theme["canvas"]
        self.geo = theme["layout"]
        self.colors = theme["colors"]
        self.type = theme["type"]
        self.width = self.canvas["width"]
        self.height = self.canvas["height"]
        self.cx = self.width / 2
        self.cy = self.height / 2
        self.warnings = []
        self.card_rects = []

    # -- öffentliche API ---------------------------------------------------

    def build(self):
        scene = Scene(self.width, self.height, self.canvas["background"])
        tools = self.data["tools"]
        placements = [self._placement(i, len(tools)) for i in range(len(tools))]

        if self.geo.get("showGuideRing"):
            scene.add(Ellipse(self.cx, self.cy, self.geo["nodeRingA"], self.geo["nodeRingB"],
                              stroke=mix(self.colors["hairline"], WHITE, 0.35), stroke_width=1.4))

        edges, cards, nodes, labels = Group(cls="edges"), Group(cls="cards"), Group(cls="nodes"), Group(cls="labels")
        for tool, place in zip(tools, placements):
            self._tool(tool, place, edges, cards, nodes, labels)

        scene.add(edges, cards, nodes, labels)
        scene.add(self._hub())
        scene.add(self._header())
        scene.add(self._zugang_box())
        scene.add(self._legend_box())
        self._check_overlaps()
        return scene

    # -- Geometrie ---------------------------------------------------------

    def _placement(self, index, count):
        angle = math.radians(self.geo["startAngle"] + index * 360.0 / count)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        node = (self.cx + self.geo["nodeRingA"] * cos_a,
                self.cy + self.geo["nodeRingB"] * sin_a)
        card = (self.cx + self.geo["cardRingA"] * cos_a,
                self.cy + self.geo["cardRingB"] * sin_a)
        return {"angle": angle, "node": node, "card": card}

    def _palette(self, tool):
        return self.theme["palette"][tool.get("color", "teal")]

    # -- Bausteine ---------------------------------------------------------

    def _tool(self, tool, place, edges, cards, nodes, labels):
        pal = self._palette(tool)
        nx, ny = place["node"]
        node_r = self.geo["nodeRadius"]

        # Speiche Hub -> Knoten
        dx, dy = nx - self.cx, ny - self.cy
        dist = math.hypot(dx, dy) or 1
        ux, uy = dx / dist, dy / dist
        hub_r = self.geo["hubRadius"]
        x1, y1 = self.cx + ux * (hub_r + 6), self.cy + uy * (hub_r + 6)
        x2, y2 = nx - ux * node_r, ny - uy * node_r
        edges.add(Line(x1, y1, x2, y2, mix(pal["base"], WHITE, 0.45), 3.0))
        edges.add(Circle(x1, y1, 4.5, fill=mix(pal["base"], WHITE, 0.25)))

        # Frage entlang der Speiche
        self._question(tool, (x1, y1), (x2, y2), labels)

        # Karte
        card_shapes, rect = self._card(tool, place["card"])
        self.card_rects.append((tool["name"], rect))

        # Verbinder Knoten -> Karte
        ex, ey = ray_rect_exit(nx, ny, ux, uy, rect)
        edges.add(Line(nx + ux * node_r, ny + uy * node_r, ex, ey,
                       mix(pal["base"], WHITE, 0.55), 1.6))

        href = tool.get("url")
        group = Group(cls="tool", href=href, title=tool["name"])
        group.add(*card_shapes)
        cards.add(group)

        # Knoten
        node_group = Group(cls="node", href=href, title=tool["name"])
        node_group.add(Circle(nx, ny, node_r, fill=pal["base"]))
        lines, size, line_height = fit_lines_in_circle(
            tool["name"], node_r - 6, self.type["node"]["size"], 12)
        start = ny - (len(lines) - 1) * line_height / 2 + size * 0.34
        for i, line in enumerate(lines):
            node_group.add(Text(nx, start + i * line_height, line.replace("­", ""),
                                size=size, bold=True, fill=WHITE, anchor="middle"))
        nodes.add(node_group)

    def _question(self, tool, start, end, labels):
        style = self.type["question"]
        (x1, y1), (x2, y2) = start, end
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        flip = 90 < abs(angle) <= 180
        draw_angle = angle + 180 if flip else angle

        available = math.hypot(x2 - x1, y2 - y1) - 34
        lines = metrics.wrap(tool["question"], style["size"], available)
        # Nicht mehr als zwei Zeilen: notfalls enger umbrechen
        if len(lines) > 2:
            lines = metrics.wrap(tool["question"], style["size"], available * 1.0)[:2]

        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        # senkrecht zur Speiche versetzen, damit die Zeilen sauber stapeln
        rad = math.radians(draw_angle)
        px, py = -math.sin(rad), math.cos(rad)
        offset = -(len(lines) - 1) * style["lineHeight"] / 2
        for i, line in enumerate(lines):
            shift = offset + i * style["lineHeight"]
            labels.add(Text(mx + px * shift, my + py * shift + style["size"] * 0.34, line,
                            size=style["size"], fill=self.colors["body"],
                            anchor="middle", rotate=draw_angle,
                            halo=self.canvas["background"], halo_width=5))

    # -- Karte -------------------------------------------------------------

    def _card(self, tool, center):
        pal = self._palette(tool)
        width = self.geo["cardWidth"]
        pad = 18
        inner = width - 2 * pad

        title = self.type["cardTitle"]
        body = self.type["cardBody"]
        chip = self.type["chip"]

        title_lines = metrics.wrap(tool["name"], title["size"], inner, True)
        body_lines = metrics.wrap(tool["summary"], body["size"], inner)
        chip_rows = self._flow(tool.get("features", []), chip["size"], inner)
        zug_rows = self._flow([self._zugang_label(z) for z in tool.get("zugang", [])],
                              chip["size"], inner)

        height = pad
        height += len(title_lines) * (title["size"] * 1.2)
        height += 10
        height += len(body_lines) * body["lineHeight"]
        if chip_rows:
            height += 12 + len(chip_rows) * 28
        if zug_rows:
            height += 10 + len(zug_rows) * 28
        height += 8 + 18          # Fußzeile (Domain)
        height += pad - 4

        x = center[0] - width / 2
        y = center[1] - height / 2
        shapes = [
            Rect(x, y, width, height, r=16,
                 fill=pal["tint"], stroke=mix(pal["base"], WHITE, 0.6), stroke_width=1.4),
        ]

        cursor = y + pad
        for line in title_lines:
            cursor += title["size"] * 0.95
            shapes.append(Text(x + pad, cursor, line.replace("­", ""),
                               size=title["size"], bold=True, fill=pal["dark"]))
            cursor += title["size"] * 0.25
        cursor += 10

        for line in body_lines:
            cursor += body["size"] * 0.9
            shapes.append(Text(x + pad, cursor, line, size=body["size"],
                               fill=self.colors["body"]))
            cursor += body["lineHeight"] - body["size"] * 0.9

        if chip_rows:
            cursor += 12
            cursor = self._draw_chips(shapes, chip_rows, x + pad, cursor, chip["size"],
                                      WHITE, mix(pal["base"], WHITE, 0.55), pal["dark"])
        if zug_rows:
            cursor += 10
            cursor = self._draw_chips(shapes, zug_rows, x + pad, cursor, chip["size"],
                                      mix(pal["base"], WHITE, 0.82),
                                      mix(pal["base"], WHITE, 0.5), pal["dark"], dot=pal["base"])

        cursor += 8 + 12
        foot = hostname(tool.get("url")) or tool.get("urlLabel", "")
        if foot:
            shapes.append(Text(x + pad, cursor, foot, size=self.type["footnote"]["size"],
                               fill=mix(pal["dark"], WHITE, 0.45)))

        return shapes, (x, y, width, height)

    def _zugang_label(self, zid):
        for z in self.data["zugaenge"]:
            if z["id"] == zid:
                return z["label"]
        return zid

    def _flow(self, labels, size, max_width):
        """Chips zeilenweise anordnen; gibt Zeilen mit (Text, Breite) zurück."""
        rows, row, used = [], [], 0.0
        for label in labels:
            w = metrics.text_width(metrics.sanitize(label), size) + 22
            if row and used + w + 6 > max_width:
                rows.append(row)
                row, used = [], 0.0
            row.append((label, w))
            used += w + 6
        if row:
            rows.append(row)
        return rows

    def _draw_chips(self, shapes, rows, x, y, size, fill, stroke, text_color, dot=None):
        for row in rows:
            cursor_x = x
            for label, w in row:
                extra = 12 if dot else 0
                shapes.append(Rect(cursor_x, y, w + extra, 22, r=11,
                                   fill=fill, stroke=stroke, stroke_width=1))
                if dot:
                    shapes.append(Circle(cursor_x + 12, y + 11, 4, fill=dot))
                shapes.append(Text(cursor_x + 11 + extra, y + 15, label,
                                   size=size, fill=text_color))
                cursor_x += w + extra + 6
            y += 28
        return y

    # -- Hub, Kopf, Boxen --------------------------------------------------

    def _hub(self):
        group = Group(cls="hub")
        r = self.geo["hubRadius"]
        group.add(Circle(self.cx, self.cy, r + 12, fill=mix(self.colors["hub"], WHITE, 0.92)))
        group.add(Circle(self.cx, self.cy, r, fill=self.colors["hub"]))
        lines = self.data["meta"]["hub"]
        style = self.type["hub"]
        size = style["size"]
        while size > 12:
            widths = [metrics.text_width(metrics.sanitize(l), size, True) for l in lines]
            usable = _chord_width(r - 10, len(lines), size * 1.22)
            if max(widths) <= usable:
                break
            size -= 1
        line_height = size * 1.22
        start = self.cy - (len(lines) - 1) * line_height / 2 + size * 0.34
        for i, line in enumerate(lines):
            group.add(Text(self.cx, start + i * line_height, line, size=size, bold=True,
                           fill=self.colors["hubText"], anchor="middle"))
        return group

    def _header(self):
        meta = self.data["meta"]
        m = self.canvas["margin"]
        group = Group(cls="header")
        group.add(Text(m, m + 44, meta["title"], size=self.type["header"]["size"],
                       bold=True, fill=self.colors["ink"]))
        group.add(Rect(m + 2, m + 60, 64, 5, r=2.5, fill=self.colors["accent"]))
        group.add(Text(m, m + 96, meta["subtitle"], size=self.type["subheader"]["size"],
                       fill=self.colors["muted"]))
        group.add(Text(self.width - m, m + 44, "TH Köln · Campus Gummersbach",
                       size=self.type["subheader"]["size"], bold=True,
                       fill=self.colors["ink"], anchor="end"))
#        group.add(Text(self.width - m, m + 72, "Stand: " + meta["stand"],
#                       size=self.type["footnote"]["size"], fill=self.colors["muted"],
#                      anchor="end"))
        return group

    def _zugang_box(self):
        m = self.canvas["margin"]
        width = 470
        pad = 20
        style = self.type["boxBody"]
        blocks = []
        for z in self.data["zugaenge"]:
            lines = metrics.wrap(z["text"], style["size"], width - 2 * pad)
            blocks.append((z, lines))
        height = pad + 26
        for _, lines in blocks:
            height += 26 + len(lines) * style["lineHeight"] + 14
        height += pad - 14

        x, y = m, self.height - m - height
        group = Group(cls="box")
        group.add(Rect(x, y, width, height, r=16, fill=self.colors["surface"],
                       stroke=self.colors["hairline"], stroke_width=1.4))
        cursor = y + pad + 20
        group.add(Text(x + pad, cursor, "Zugänge", size=self.type["boxTitle"]["size"],
                       bold=True, fill=self.colors["ink"]))
        cursor += 12
        for z, lines in blocks:
            cursor += 22
            color = self.theme["zugangColors"][z["id"]]
            label_w = metrics.text_width(metrics.sanitize(z["label"]), self.type["chip"]["size"]) + 34
            group.add(Rect(x + pad, cursor - 15, label_w, 22, r=11,
                           fill=color["tint"], stroke=mix(color["base"], WHITE, 0.6)))
            group.add(Circle(x + pad + 12, cursor - 4, 4, fill=color["base"]))
            group.add(Text(x + pad + 23, cursor, z["label"], size=self.type["chip"]["size"],
                           fill=mix(color["base"], "#000000", 0.15)))
            cursor += 12
            for line in lines:
                cursor += style["size"] * 0.9
                group.add(Text(x + pad, cursor, line, size=style["size"],
                               fill=self.colors["body"]))
                cursor += style["lineHeight"] - style["size"] * 0.9
            cursor += 8
        return group

    def _legend_box(self):
        m = self.canvas["margin"]
        width = 470
        pad = 20
        style = self.type["boxBody"]
        rows = [
            ("circle", "Tool – klickbar, führt direkt zur Plattform"),
            ("line", "Frage, die das Tool beantwortet"),
            ("chip", "Funktion des Tools"),
            ("badge", "Zugang, den du dafür brauchst"),
        ]
        height = pad + 26 + len(rows) * 34 + pad - 6
        x = self.width - m - width
        y = self.height - m - height
        group = Group(cls="box")
        group.add(Rect(x, y, width, height, r=16, fill=self.colors["surface"],
                       stroke=self.colors["hairline"], stroke_width=1.4))
        cursor = y + pad + 20
        group.add(Text(x + pad, cursor, "Legende", size=self.type["boxTitle"]["size"],
                       bold=True, fill=self.colors["ink"]))
        cursor += 18
        sample = self.theme["palette"]["cyan"]
        for kind, label in rows:
            cursor += 30
            icon_x = x + pad + 22
            if kind == "circle":
                group.add(Circle(icon_x, cursor - 5, 12, fill=sample["base"]))
            elif kind == "line":
                group.add(Line(icon_x - 14, cursor - 5, icon_x + 14, cursor - 5,
                               mix(sample["base"], WHITE, 0.45), 3))
            elif kind == "chip":
                group.add(Rect(icon_x - 16, cursor - 16, 32, 22, r=11, fill=WHITE,
                               stroke=mix(sample["base"], WHITE, 0.55)))
            else:
                group.add(Rect(icon_x - 16, cursor - 16, 32, 22, r=11,
                               fill=mix(sample["base"], WHITE, 0.82),
                               stroke=mix(sample["base"], WHITE, 0.5)))
                group.add(Circle(icon_x - 5, cursor - 5, 4, fill=sample["base"]))
            group.add(Text(x + pad + 50, cursor, label, size=style["size"],
                           fill=self.colors["body"]))
        return group

    # -- Kollisionsprüfung -------------------------------------------------

    def _check_overlaps(self):
        for i in range(len(self.card_rects)):
            for j in range(i + 1, len(self.card_rects)):
                name_a, a = self.card_rects[i]
                name_b, b = self.card_rects[j]
                if (a[0] < b[0] + b[2] and b[0] < a[0] + a[2]
                        and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]):
                    self.warnings.append(
                        f"Karten überlappen: {name_a} / {name_b}. "
                        f"cardRingA/cardRingB in data/theme.json erhöhen.")
        for name, rect in self.card_rects:
            m = self.canvas["margin"] / 2
            if (rect[0] < m or rect[1] < m
                    or rect[0] + rect[2] > self.width - m
                    or rect[1] + rect[3] > self.height - m):
                self.warnings.append(
                    f"Karte '{name}' ragt über den Rand. canvas.width/height erhöhen.")
