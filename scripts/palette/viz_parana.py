"""Render the selected palettes on a Paraná municipality choropleth.

Colors are assigned along a leaned axis (x + TILT*y), quantile-binned into
5 bands, so each palette color forms a slightly diagonal strip across the
state and all 5 colors are used equally.

Reads data/parana_municipalities.geojson and writes plots/maps/palette_viz_parana.html.
`build_rows()` is shared with build_palette_pdf.py, which renders the same map
into the print PDF.
"""

import json
import math
import os
from pathlib import Path

from shapely.geometry import shape

PALETTES = [
    {"index": 28, "colors": ["#303040", "#806040", "#A0C0E0", "#F0E0C0", "#E06040"]},
    {"index": 47, "colors": ["#404050", "#80A0C0", "#FFC0A0", "#608050", "#D04070"]},
    {"index": 80, "colors": ["#80A090", "#D0C090", "#403020", "#A09030", "#D08050"]},
]

ROOT = str(Path(__file__).resolve().parents[2])
GEOJSON = os.path.join(ROOT, "data", "parana_municipalities.geojson")
OUT = os.path.join(ROOT, "plots", "maps", "palette_viz_parana.html")

# ---- config ----------------------------------------------------------------
LAT_CENTER = -24.5       # Paraná's mid latitude
SIMPLIFY = 0.004         # degrees (~440 m), keeps 399 polygons small
TARGET_W = 740.0
MARGIN = 12.0
N_COLORS = len(PALETTES[0]["colors"])  # 5
TILT = 0.5                # strip lean: 0 = vertical, 1 = 45°


def polygons(g):
    return list(g.geoms) if g.geom_type == "MultiPolygon" else [g]


def proj_raw(pt):
    lon, lat = pt
    return lon * math.cos(math.radians(LAT_CENTER)), -lat  # y flips for SVG


def project():
    """Return (rings, color, viewbox) for the Paraná map.

    ``rings[i]`` is municipality i's list of ``(is_hole, [(x, y), ...])`` rings
    in projected SVG coordinates (y points down); ``color[i]`` is its 0-based
    band index from the leaned strips (five equal bands); ``viewbox`` fits the
    whole state. Shared by the HTML page (build_rows) and the PNG renderer.
    """
    data = json.load(open(GEOJSON))
    feats = [f for f in data["features"] if f["geometry"] is not None]
    geoms = [shape(f["geometry"]).simplify(SIMPLIFY, preserve_topology=True) for f in feats]
    n = len(geoms)

    # ---- color: leaned strips -------------------------------------------------
    # Bands run along x + TILT*y so they lean across the state rather than
    # cutting it straight up-and-down.
    xs = [g.centroid.x for g in geoms]
    ys = [g.centroid.y for g in geoms]
    u = [(x - min(xs)) / (max(xs) - min(xs)) for x in xs]
    v = [(y - min(ys)) / (max(ys) - min(ys)) for y in ys]
    order = sorted(range(n), key=lambda i: u[i] + TILT * v[i])
    color = [0] * n
    for rank, i in enumerate(order):
        color[i] = min(N_COLORS - 1, rank * N_COLORS // n)

    # bounding box (projected)
    minx = miny = float("inf")
    maxx = maxy = float("-inf")
    for g in geoms:
        for poly in polygons(g):
            for x, y in map(proj_raw, poly.exterior.coords):
                minx, maxx = min(minx, x), max(maxx, x)
                miny, maxy = min(miny, y), max(maxy, y)

    scale = (TARGET_W - 2 * MARGIN) / (maxx - minx)
    height = (maxy - miny) * scale + 2 * MARGIN
    viewbox = f"0 0 {TARGET_W:.0f} {height:.0f}"

    def tf(pt):
        x, y = proj_raw(pt)
        return (x - minx) * scale + MARGIN, (y - miny) * scale + MARGIN

    rings = []
    for g in geoms:
        grings = []
        for poly in polygons(g):
            grings.append((False, [tf(pt) for pt in poly.exterior.coords]))
            for hole in poly.interiors:
                grings.append((True, [tf(pt) for pt in hole.coords]))
        rings.append(grings)

    return rings, color, viewbox


def build_rows():
    """Return ([(path_d, color_index), ...], viewbox) for the Paraná map."""
    rings, color, viewbox = project()

    def ring_str(coords):
        cs = [p for p in coords]
        if cs and cs[0] == cs[-1]:
            cs = cs[:-1]
        return "M" + " ".join(f"{x:.1f},{y:.1f}" for x, y in cs) + "Z"

    rows = [("".join(ring_str(cs) for _, cs in g), color[i])
            for i, g in enumerate(rings)]
    return rows, viewbox


def main():
    rows, viewbox = build_rows()
    paths = ",\n    ".join(f'["{d}",{c}]' for d, c in rows)
    html = (HTML_TEMPLATE
            .replace("__SUBTITLE__", "3 palettes · applied to Paraná municipalities (399 cities)")
            .replace("__PATHS__", paths)
            .replace("__VIEWBOX__", viewbox))
    with open(OUT, "w") as f:
        f.write(html)

    print(f"{len(rows)} municipalities -> {OUT}")


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Selected Palettes</title>
<style>
  :root {
    --bg: #f4f2ee; --surface: #ffffff; --fg: #1a1a1a; --muted: #6f6a63;
    --border: #e2ded6; --chip-border: rgba(0,0,0,0.14); --accent: #3b5bdb;
    --map-stroke: #ffffff;
    color-scheme: light;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg: #171719; --surface: #232326; --fg: #ececea; --muted: #a09b92;
      --border: #3a3a3f; --chip-border: rgba(255,255,255,0.18); --accent: #7c93ff;
      --map-stroke: #232326;
      color-scheme: dark;
    }
  }
  :root[data-theme="dark"] {
    --bg: #171719; --surface: #232326; --fg: #ececea; --muted: #a09b92;
    --border: #3a3a3f; --chip-border: rgba(255,255,255,0.18); --accent: #7c93ff;
    --map-stroke: #232326;
    color-scheme: dark;
  }

  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--fg);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    padding: 32px 16px 48px; -webkit-font-smoothing: antialiased;
  }
  .wrap { width: 100%; max-width: 860px; margin: 0 auto; }
  .head { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 8px; }
  h1 { font-size: 24px; font-weight: 600; letter-spacing: -0.01em; margin: 0; }
  .sub { color: var(--muted); font-size: 14px; margin: 4px 0 22px; }

  .ctl-group { display: inline-flex; gap: 4px; }
  .seg {
    border: 1px solid var(--border); background: var(--surface); color: var(--muted);
    font: inherit; font-size: 13px; padding: 6px 12px; border-radius: 999px; cursor: pointer;
  }
  .seg:hover { color: var(--fg); }
  .seg.active { background: var(--accent); border-color: var(--accent); color: #fff; }
  .seg:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 20px; margin-bottom: 22px; }
  .card h2 { font-size: 16px; font-weight: 600; margin: 0 0 12px; }
  .map { width: 100%; height: auto; display: block; }
  .state { stroke: rgba(0,0,0,0.35); stroke-width: 0.7; vector-effect: non-scaling-stroke; fill-rule: evenodd; }

  .legend { display: flex; flex-wrap: wrap; gap: 8px 16px; margin-top: 12px; }
  .lg { display: flex; align-items: center; gap: 7px; }
  .lg .chip { width: 16px; height: 16px; border-radius: 4px; border: 1px solid var(--chip-border); }
  .lg .hex { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 12px; color: var(--muted); font-variant-numeric: tabular-nums; }
</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <h1>Selected palettes</h1>
    <div class="ctl-group" id="grp-theme">
      <button class="seg active" data-theme="auto">Auto</button>
      <button class="seg" data-theme="light">Light</button>
      <button class="seg" data-theme="dark">Dark</button>
    </div>
  </div>
  <p class="sub">__SUBTITLE__</p>
  <main id="cards"></main>
</div>

<script>
const PALETTES = [{"index":28,"colors":["#303040","#806040","#A0C0E0","#F0E0C0","#E06040"]},{"index":47,"colors":["#404050","#80A0C0","#FFC0A0","#608050","#D04070"]},{"index":80,"colors":["#80A090","#D0C090","#403020","#A09030","#D08050"]}];
const PATHS = [
    __PATHS__
];
const TRANSFORM = "";
const $ = (id) => document.getElementById(id);

function card(p) {
  let s = '<svg class="map" viewBox="__VIEWBOX__" role="img" aria-label="Palette ' + p.index + '"><g transform="' + TRANSFORM + '">';
  for (let i = 0; i < PATHS.length; i++) {
    s += '<path class="state" d="' + PATHS[i][0] + '" fill="' + p.colors[PATHS[i][1]] + '"/>';
  }
  s += '</g></svg>';
  let lg = '<div class="legend">';
  for (let j = 0; j < p.colors.length; j++) {
    lg += '<div class="lg"><span class="chip" style="background:' + p.colors[j] + '"></span><span class="hex">' + p.colors[j] + '</span></div>';
  }
  lg += '</div>';
  return '<section class="card"><h2>Palette ' + p.index + '</h2>' + s + lg + '</section>';
}

function render() { $("cards").innerHTML = PALETTES.map(card).join(""); }

function setTheme(t) { if (t === "auto") delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = t; }
$("grp-theme").addEventListener("click", (e) => {
  const b = e.target.closest("[data-theme]"); if (!b) return;
  document.querySelectorAll("#grp-theme .seg").forEach((x) => x.classList.remove("active"));
  b.classList.add("active");
  setTheme(b.dataset.theme);
});

render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
