#!/usr/bin/env python3
"""Build palettes.pdf from a palette-viz HTML file and the zoomed network image.

One page per palette (each palette's choropleth map is embedded as vector SVG),
plus a final dark page with the "Infered from:" title above the close-up color
network.

The source HTML supplies the palette/map data (PALETTES, PATHS, TRANSFORM) and
its map styling (viewBox + path class), so the same script works for any
plots/maps/palette_viz*.html — e.g. palette_viz.html or palette_viz_parana.html.

Requires:
  - the palette-viz HTML under plots/maps/ (default: plots/maps/palette_viz_parana.html)
  - plots/color_network_zoom.png (see scripts/network/network_zoom.py)
  - a headless Chrome/Chromium binary (``google-chrome`` on PATH)

Usage:  python3 scripts/palette/build_palette_pdf.py [plots/maps/palette_viz.html]
Writes plots/maps/palettes.pdf.
"""

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # scripts/palette/ -> repo root
SRC = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "plots/maps/palette_viz_parana.html")
PNG = ROOT / "plots" / "color_network_zoom.png"
OUT_PDF = ROOT / "plots" / "maps" / "palettes.pdf"

# Palette colors whose municipalities get a white edge instead of the default
# dark stroke (they don't contrast well with black). Add hex codes as needed.
WHITE_EDGE = ["#303040", "#404050", "#403020", "#806040"]

CHROME = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")

src = SRC.read_text(encoding="utf-8")


def extract(var):
    """Pull the ``const VAR = ...;`` literal out of the source's script."""
    m = re.search(r"const\s+" + var + r"\s*=([^;]*);", src, re.DOTALL)
    if not m:
        raise SystemExit(f"could not find `{var}` in {SRC}")
    return m.group(1).strip()


def extract_one(pattern, what):
    m = re.search(pattern, src)
    if not m:
        raise SystemExit(f"could not find {what} in {SRC}")
    return m.group(1)


palettes = extract("PALETTES")
paths = extract("PATHS")
transform = extract("TRANSFORM")

viewbox = extract_one(r'viewBox="([^"]+)"', "the SVG viewBox")
cls = extract_one(r'<path class="([^"]+)"', "the map path class")
cls_rule = extract_one(r"\.%s\s*\{([^}]*)\}" % re.escape(cls), f"the `.{cls}` CSS rule")

# Size the map as large as the landscape page allows, preserving its aspect.
m = re.match(r"0 0 ([\d.]+) ([\d.]+)", viewbox)
map_w = float(m.group(1))
map_h_src = float(m.group(2))
MAP_H_MM = 175.0
MAP_W_MM = round(MAP_H_MM * map_w / map_h_src, 1)

b64 = base64.b64encode(PNG.read_bytes()).decode("ascii")

html = """<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="UTF-8">
<title>Palettes</title>
<style>
  :root {
    --bg: #f4f2ee; --surface: #ffffff; --fg: #1a1a1a; --muted: #6f6a63;
    --border: #e2ded6; --chip-border: rgba(0,0,0,0.14);
    color-scheme: light;
  }
  * { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  html, body { margin: 0; padding: 0; }
  body {
    background: var(--bg); color: var(--fg);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    -webkit-font-smoothing: antialiased;
  }

  @page { size: A4 landscape; margin: 0; }

  .page {
    width: 297mm; height: 210mm;
    display: flex; align-items: center; justify-content: center;
    page-break-after: always; break-after: page;
    overflow: hidden;
  }
  .page:last-child { page-break-after: auto; break-after: auto; }

  .card {
    background: var(--surface); border: 1px solid var(--border); border-radius: 16px;
    padding: 18px; width: auto; max-width: 100%;
  }
  .card h2 { font-size: 18px; font-weight: 600; margin: 0 0 12px; }
  .map { display: block; width: __MAP_W__mm; height: __MAP_H__mm; margin: 0 auto; }
  .__CLS__ { __CLS_RULE__ }

  .legend { display: flex; flex-wrap: wrap; gap: 8px 18px; margin-top: 14px; justify-content: center; }
  .lg { display: flex; align-items: center; gap: 7px; }
  .lg .chip { width: 16px; height: 16px; border-radius: 4px; border: 1px solid var(--chip-border); }
  .lg .hex { font-family: ui-monospace, Menlo, monospace; font-size: 13px; color: var(--muted); font-variant-numeric: tabular-nums; }

  .page.network { background: #111; flex-direction: column; gap: 16mm; padding: 10mm; }
  .page.network h2 { color: #ffffff; font-size: 26px; font-weight: 600; margin: 0; letter-spacing: 0.01em; }
  .page.network img { height: 172mm; width: auto; max-width: 100%; }
</style>
</head>
<body>
<main id="cards"></main>
<div class="page network">
  <h2>Infered from:</h2>
  <img src="data:image/png;base64,__B64__" alt="Color network">
</div>
<script>
const PALETTES = __PALETTES__;
const PATHS = __PATHS__;
const TRANSFORM = __TRANSFORM__;
const $ = (id) => document.getElementById(id);
const WHITE_EDGE = __WHITE_EDGE__;
function edge(hex) {
  return WHITE_EDGE.indexOf(hex.toUpperCase()) >= 0 ? '#ffffff' : null;
}
function card(p) {
  var edges = p.colors.map(edge);
  let s = '<svg class="map" viewBox="__VIEWBOX__" role="img" aria-label="Palette ' + p.index + '"><g transform="' + TRANSFORM + '">';
  for (let i = 0; i < PATHS.length; i++) {
    var ci = PATHS[i][1];
    var st = edges[ci] ? ' style="stroke:' + edges[ci] + '"' : '';
    s += '<path class="__CLS__"' + st + ' d="' + PATHS[i][0] + '" fill="' + p.colors[ci] + '"/>';
  }
  s += '</g></svg>';
  let lg = '<div class="legend">';
  for (let j = 0; j < p.colors.length; j++) {
    lg += '<div class="lg"><span class="chip" style="background:' + p.colors[j] + '"></span><span class="hex">' + p.colors[j] + '</span></div>';
  }
  lg += '</div>';
  return '<section class="page"><div class="card"><h2>Palette ' + p.index + '</h2>' + s + lg + '</div></section>';
}
$("cards").innerHTML = PALETTES.map(card).join("");
</script>
</body>
</html>
"""

html = (html.replace("__PALETTES__", palettes)
           .replace("__PATHS__", paths)
           .replace("__TRANSFORM__", transform)
           .replace("__VIEWBOX__", viewbox)
           .replace("__MAP_W__", str(MAP_W_MM))
           .replace("__MAP_H__", str(MAP_H_MM))
           .replace("__WHITE_EDGE__", json.dumps(WHITE_EDGE))
           .replace("__CLS__", cls)
           .replace("__CLS_RULE__", cls_rule)
           .replace("__B64__", b64))

if not CHROME:
    raise SystemExit("no headless Chrome/Chromium found on PATH")

with tempfile.NamedTemporaryFile("w", suffix=".html", encoding="utf-8", delete=False) as f:
    f.write(html)
    out_html = f.name

cmd = [
    CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
    "--no-pdf-header-footer", "--virtual-time-budget=8000",
    "--print-to-pdf=" + str(OUT_PDF),
    "file://" + out_html,
]
r = subprocess.run(cmd, capture_output=True, text=True)
os.remove(out_html)
if r.returncode != 0:
    print(r.stderr[-2000:], file=sys.stderr)
    sys.exit(r.returncode)
print(f"wrote {OUT_PDF}")
