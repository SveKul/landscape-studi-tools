# Studi-Tools – TH Köln, Campus Gummersbach

Interaktive Online-Version der Plattform-Übersicht für Studierende: ein
graphbasiertes Schaubild mit zentralem Knoten, der relevantesten Tools und den Fragen,
die sie beantworten.

* **Downloads:** SVG (Vektor) und PDF (A3 quer, mit klickbaren Links)


## Schnellstart

```bash
git clone <repo-url>
cd studi-tools
python src/build.py            # baut nach docs/
python -m http.server -d docs  # Vorschau: http://localhost:8000
```

Python ≥ 3.9, **keine Pakete installieren** – nur Standardbibliothek.

## Inhalte pflegen

Alles Inhaltliche steckt in `data/tools.json`:

```jsonc
{
  "id": "ilu",                                  // eindeutig, klein geschrieben
  "name": "ILU",                                // Text im Kreis und in der Karte
  "color": "teal",                              // Schlüssel aus theme.json -> palette
  "question": "Wo finde ich die Inhalte zum Studium?",  // Beschriftung der Kante
  "summary": "Lernplattform der TH Köln ...",   // Fließtext in der Karte
  "features": ["Modulinhalte", "Gruppenarbeit"],// die kleinen Chips
  "zugang": ["campus"],                         // ids aus "zugaenge"
  "url": "https://ilu.th-koeln.de/"             // null, wenn (noch) kein Link existiert
}
```

Danach `python src/build.py` – fertig. Die Reihenfolge im Array bestimmt die
Position im Ring (im Uhrzeigersinn ab 12 Uhr). Ein Tool zu löschen oder
einzufügen verschiebt automatisch alle anderen.

Der Build prüft die Daten vorab und meldet z. B. doppelte `id`s, unbekannte
Farben oder fehlende Felder im Klartext. Passt eine Karte nicht mehr auf die
Fläche, warnt er und nennt die Stellschraube.


### Aussehen ändern

`data/theme.json` steuert Leinwandgröße, Ringradien, Kartenbreite, Schrift und
alle Farben. Häufige Fälle:

* **Mehr Platz** (z. B. ab ~16 Tools): `canvas.width/height` und
  `layout.cardRingA/cardRingB` proportional erhöhen.
* **Andere Hausfarben:** `palette` anpassen – je Farbe `base` (Kreis),
  `dark` (Überschrift) und `tint` (Kartenfläche).
* **Andere Schrift:** `font.family` gilt für das Web. `font.pdfRegular/pdfBold`
  sind PDF-Standardschriften; werden sie geändert, stimmen die Zeilenumbrüche
  im PDF nur noch, wenn auch die Breitentabellen in `src/metrics.py` passen.

## Projektstruktur

```
data/tools.json      Inhalte (das, was ihr regelmäßig ändert)
data/theme.json      Farben, Maße, Typografie
src/build.py         Einstiegspunkt: liest Daten, schreibt docs/
src/layout.py        radiales Layout, Kartenaufbau, Kollisionsprüfung
src/scene.py         Zeichenmodell (Kreis, Ellipse, Rechteck, Linie, Text, Gruppe)
src/render_svg.py    Zeichenmodell -> SVG
src/render_pdf.py    Zeichenmodell -> PDF (A3 quer), ohne externe Bibliothek
src/metrics.py       Textbreiten (Helvetica/Arial) für exakte Umbrüche
src/template.html    HTML-Rahmen der Seite
docs/                Build-Ergebnis = das, was GitHub Pages ausliefert
```

Layout und Ausgabe sind getrennt: `layout.py` erzeugt eine Liste einfacher
Formen, die Renderer kennen nur diese. Ein weiteres Ausgabeformat (z. B. PNG)
ergänzt man, ohne das Layout anzufassen.

## GitHub Pages einrichten

1. Repository auf GitHub anlegen und pushen.
2. **Settings → Pages → Source: „GitHub Actions“.**
3. Fertig: `.github/workflows/pages.yml` baut bei jedem Push auf `main` und
   veröffentlicht `docs/`.

Alternative ohne Actions: **Settings → Pages → Deploy from a branch →
`main` / `/docs`**. Dann muss der Ordner `docs/` mitcommittet werden (er ist
es bereits) und nach jeder Änderung lokal neu gebaut werden.

