"""Render a zoomed-in view of the color co-occurrence network.

The full network (color_network.png) shows the entire giant component from
far away. This re-lays-out the same graph (same seed, so the layout matches),
renders it larger and crops the central region, giving an up-close view of the
network's core. Node/edge sizes are scaled with the zoom so it reads as a true
camera zoom rather than a sparse re-fit.

Reads data/palettes.json and writes plots/color_network_zoom.png.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # scripts/shared -> graph.py

import graph_tool.all as gt
from PIL import Image

from graph import (DATA_DIR, PLOTS_DIR, build_graph, centrality, draw,
                   giant_component, layout, load_palettes, to_graph_tool,
                   vertex_rgba)

# ---- config (mirrors network.py so the layout is identical) ----------------
INPUT = os.path.join(DATA_DIR, "palettes.json")
GIANT_ONLY = True          # keep only the giant connected component
SIZE_BY = "betweenness"    # "degree" | "betweenness"
SIZE = dict(mi=2, ma=45, power=0.8)
BG = [0.07, 0.07, 0.07, 1.0]
SEED = 42
NUM_ITERS = 1000

ZOOM = 2.0                 # magnification relative to the full view
FULL_SIZE = 6000           # render the full graph at this square size
CROP_SIZE = 3000           # crop the central square (CROP_SIZE = FULL_SIZE / ZOOM)
OUTPUT = os.path.join(PLOTS_DIR, "color_network_zoom.png")


def main():
    palettes = load_palettes(INPUT)
    G = build_graph(palettes)
    if GIANT_ONLY:
        G = giant_component(G)

    g, nodes, idx = to_graph_tool(G)
    v_rgba = vertex_rgba(g, nodes)
    central = centrality(g, SIZE_BY)
    # Scale node size with the zoom so the crop reads as a true zoom.
    size = gt.prop_to_size(central, mi=SIZE["mi"] * ZOOM,
                           ma=SIZE["ma"] * ZOOM, power=SIZE["power"])
    pos = layout(g, SEED, NUM_ITERS)

    tmp = os.path.join(PLOTS_DIR, "_zoom_full.png")
    draw(g, pos, v_rgba, size, BG, (FULL_SIZE, FULL_SIZE), tmp,
         edge_pen_width=0.3 * ZOOM)

    im = Image.open(tmp).convert("RGB")
    left = (FULL_SIZE - CROP_SIZE) // 2
    im.crop((left, left, left + CROP_SIZE, left + CROP_SIZE)).save(OUTPUT)
    os.remove(tmp)

    print(f"{g.num_vertices()} vertices | {g.num_edges()} edges "
          f"-> {OUTPUT} ({ZOOM}x zoom)")


if __name__ == "__main__":
    main()
