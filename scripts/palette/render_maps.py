"""Render each selected palette's Paraná choropleth as a standalone PNG.

Reuses the exact geometry + leaned-strip colouring from viz_parana.py (via
``project()``) and draws one clean flat image per palette: the map plus a
legend of its five colours. These are meant to be embedded in the README,
unlike the interactive HTML page or the print PDF.

    python scripts/palette/render_maps.py
"""

import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))  # scripts/palette -> viz_parana.py

from viz_parana import PALETTES, project

ROOT = str(Path(__file__).resolve().parents[2])
OUT_DIR = os.path.join(ROOT, "plots", "maps")

# Municipality colours that get a white edge instead of a dark one (they don't
# contrast with a dark stroke). Matches build_palette_pdf.py's WHITE_EDGE.
WHITE_EDGE = ["#303040", "#404050", "#403020", "#806040"]
EDGE_LIGHT = "#6f6a63"   # stroke on pale municipalities
EDGE_DARK = "#ffffff"    # stroke on dark municipalities
BG = "#ffffff"


def stroke_for(hex_color):
    return EDGE_DARK if hex_color.upper() in WHITE_EDGE else EDGE_LIGHT


def render(palette, rings, color, viewbox, out):
    w, h = (float(x) for x in viewbox.split()[2:])

    # Reserve a top strip for the title and a bottom strip for the legend,
    # sized in the same (SVG) units as the map so the map stays undistorted.
    TITLE = 30
    LEGEND = 72
    fig = plt.figure(figsize=(w / 120, (h + TITLE + LEGEND) / 120), dpi=180)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w)
    ax.set_ylim(-TITLE, h + LEGEND)
    ax.invert_yaxis()          # SVG y runs downward
    ax.axis("off")

    colors = palette["colors"]
    for grings, ci in zip(rings, color):
        fill = colors[ci]
        for is_hole, pts in grings:
            ax.add_patch(Polygon(
                pts, closed=True,
                facecolor=BG if is_hole else fill,
                edgecolor=None if is_hole else stroke_for(fill),
                linewidth=0.35, joinstyle="round"))

    # title (top-left, aligned with the map's left edge)
    ax.text(12, -18, f"Palette {palette['index']}", fontsize=15,
            fontweight="bold", ha="left", va="center", color="#1a1a1a")

    # legend (centred under the map)
    n = len(colors)
    chip = 24.0
    gap = 16.0
    x0 = (w - (n * chip + (n - 1) * gap)) / 2
    for j, c in enumerate(colors):
        x = x0 + j * (chip + gap)
        ax.add_patch(Rectangle((x, h + 18), chip, chip, facecolor=c,
                               edgecolor=(0, 0, 0, 0.2), linewidth=0.8))
        ax.text(x + chip / 2, h + 52, c, ha="center", va="top",
                fontsize=10, family="monospace", color="#555555")

    fig.savefig(out, dpi=180, facecolor=BG)
    plt.close(fig)
    # Flatten RGBA -> RGB on white (matplotlib writes an alpha channel whenever
    # any artist has alpha, e.g. the chip borders).
    Image.open(out).convert("RGB").save(out)
    print(f"palette {palette['index']} -> {out}")


def main():
    rings, color, viewbox = project()
    os.makedirs(OUT_DIR, exist_ok=True)
    for pal in PALETTES:
        render(pal, rings, color, viewbox,
               os.path.join(OUT_DIR, f"palette_{pal['index']}.png"))


if __name__ == "__main__":
    main()
