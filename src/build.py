#!/usr/bin/env python3
"""Baut die Studi-Tools-Übersicht.

    python src/build.py            # baut nach docs/
    python src/build.py --out dist # anderes Zielverzeichnis

Erzeugt:
    docs/index.html        einzelne, in sich geschlossene Seite (kein CDN, kein JS)
    docs/studi-tools.svg   Vektorgrafik zum Download
    docs/studi-tools.pdf   A3 quer, mit klickbaren Links

Nur Python-Standardbibliothek. Getestet ab Python 3.9.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import render_pdf                   # noqa: E402
import render_svg                   # noqa: E402
from layout import Layout, hostname  # noqa: E402
from scene import mix               # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def clean(text):
    """Weiche Trennzeichen aus HTML-Text entfernen (dort bricht der Browser selbst)."""
    return esc(text).replace("­", "")


def validate(data, theme):
    """Frühe, verständliche Fehlermeldungen statt kaputter Grafik."""
    problems = []
    for key in ("meta", "zugaenge", "tools"):
        if key not in data:
            problems.append("data/tools.json: Abschnitt '%s' fehlt." % key)
    if problems:
        return problems

    known_zugang = {z["id"] for z in data["zugaenge"]}
    seen = set()
    for i, tool in enumerate(data["tools"], 1):
        where = "Tool %d (%s)" % (i, tool.get("name", "ohne Namen"))
        for key in ("id", "name", "question", "summary"):
            if not tool.get(key):
                problems.append("%s: Feld '%s' fehlt oder ist leer." % (where, key))
        if tool.get("id") in seen:
            problems.append("%s: id '%s' kommt doppelt vor." % (where, tool["id"]))
        seen.add(tool.get("id"))
        color = tool.get("color", "teal")
        if color not in theme["palette"]:
            problems.append("%s: Farbe '%s' gibt es nicht in theme.json -> palette (%s)."
                            % (where, color, ", ".join(sorted(theme["palette"]))))
        for zugang in tool.get("zugang", []):
            if zugang not in known_zugang:
                problems.append("%s: Zugang '%s' ist in 'zugaenge' nicht definiert." % (where, zugang))
    for zugang in data["zugaenge"]:
        if zugang["id"] not in theme.get("zugangColors", {}):
            problems.append("theme.json: Farbe für Zugang '%s' fehlt." % zugang["id"])
    return problems


def build_list(data, theme):
    """Barrierearme, mobiltaugliche Textfassung derselben Daten."""
    labels = {z["id"]: z["label"] for z in data["zugaenge"]}
    zug_style = {}
    for zid, color in theme.get("zugangColors", {}).items():
        zug_style[zid] = "background:%s;border-color:%s;color:%s" % (
            color["tint"], mix(color["base"], "#FFFFFF", 0.6),
            mix(color["base"], "#000000", 0.2))
    out = []
    for tool in data["tools"]:
        url = tool.get("url")
        name = clean(tool["name"])
        heading = ('<a href="%s" target="_blank" rel="noopener">%s</a>' % (esc(url), name)
                   if url else name)
        tags = "".join("<li>%s</li>" % clean(f) for f in tool.get("features", []))
        tags += "".join('<li class="zug" style="%s">%s</li>'
                        % (zug_style.get(z, ""), clean(labels.get(z, z)))
                        for z in tool.get("zugang", []))
        foot = hostname(url) if url else tool.get("urlLabel", "")
        out.append(
            '      <article class="card">\n'
            '        <h3>%s</h3>\n'
            '        <p class="q">%s</p>\n'
            '        <p class="s">%s</p>\n'
            '        <ul class="tags">%s</ul>\n'
            '        %s\n'
            '      </article>' % (
                heading, clean(tool["question"]), clean(tool["summary"]), tags,
                ('<a class="url" href="%s" target="_blank" rel="noopener">%s</a>'
                 % (esc(url), clean(foot)) if url else '<span class="url">%s</span>' % clean(foot))))
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="Studi-Tools-Übersicht bauen")
    parser.add_argument("--out", default="docs", help="Zielverzeichnis (Standard: docs)")
    parser.add_argument("--page", default="A3-landscape",
                        choices=sorted(render_pdf.PAGE_SIZES), help="PDF-Seitenformat")
    args = parser.parse_args()

    data = json.loads((ROOT / "data" / "tools.json").read_text(encoding="utf-8"))
    theme = json.loads((ROOT / "data" / "theme.json").read_text(encoding="utf-8"))

    problems = validate(data, theme)
    if problems:
        print("Daten sind noch nicht baubar:")
        for problem in problems:
            print("  - " + problem)
        return 2

    layout = Layout(data, theme)
    scene = layout.build()

    meta = data["meta"]
    alt = "%s – %s" % (meta["title"], meta["subtitle"])
    font = theme["font"]["family"]

    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    svg_file = render_svg.render(scene, font, standalone=True, title=alt)
    (out_dir / "studi-tools.svg").write_text(svg_file, encoding="utf-8")

    pdf_bytes = render_pdf.render(scene, page=args.page)
    (out_dir / "studi-tools.pdf").write_bytes(pdf_bytes)

    template = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
    html = (template
            .replace("{{TITLE}}", clean(meta["title"]))
            .replace("{{SUBTITLE}}", clean(meta["subtitle"]))
            .replace("{{STAND}}", clean(meta["stand"]))
            .replace("{{KONTAKT}}", clean(meta.get("kontakt", "")))
            .replace("{{FONT}}", font)
            .replace("{{LIST}}", build_list(data, theme))
            .replace("{{SVG}}", render_svg.render(scene, font, standalone=False, title=alt)))
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")

    for warning in layout.warnings:
        print("  ! " + warning)

    print("Tools:      %d" % len(data["tools"]))
    for name, path in (("index.html", out_dir / "index.html"),
                       ("studi-tools.svg", out_dir / "studi-tools.svg"),
                       ("studi-tools.pdf", out_dir / "studi-tools.pdf")):
        print("  %-16s %6.1f KB" % (name, path.stat().st_size / 1024))
    return 1 if layout.warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
