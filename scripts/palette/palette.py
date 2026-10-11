"""Discover new color palettes via link prediction + clique completion.

A palette is a clique in the co-occurrence graph (data.py links every pair
in a palette). Link prediction finds the missing edges: pairs of colors that
share a crowd of common neighbors but never appear together. Closing such an
edge turns a near-clique into a clique, i.e. a candidate new palette.

Reads data/palettes.json (from data.py); prints indexed 5-color palettes,
renders them as swatches in plots/new_palettes/, and writes
results/new_palettes.json.
"""

import colorsys
import json
import math
import os
import sys
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))  # scripts/shared -> graph.py

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from graph import (DATA_DIR, PLOTS_DIR, RESULTS_DIR, build_graph,
                   giant_component, load_palettes, quantize_color)

# ---- config ----------------------------------------------------------------
INPUT = os.path.join(DATA_DIR, "palettes.json")
GIANT_ONLY = True         # predict inside the giant component (dense, predictable)
QUANTIZE = True           # collapse near-identical hexes before building the graph
QUANT_STEP = 16           # RGB grid step for quantization
MIN_SAT = 0.15            # neutral mask: skip near-gray colors
MAX_DEG = None            # optional hub cap on endpoints (None = off)
ANCHOR_CAP = 100          # only common neighbors with degree <= this count as evidence
PREDICTOR = "ra"          # "ra" (resource allocation) | "aa" (adamic-adar) | "cn"
MIN_PAIR_DIST = 0.22      # reject colors closer than this (full-HSV distance)
CROSS_JACCARD = 0.6       # reject a palette that shares >= this with an emitted one
TOP_EDGES = 20000         # predicted missing edges to inspect
SIZE = (5, 5)             # exactly 5 colors per palette
N_OUT = 100               # how many candidate palettes to emit
NOVELTY = 0.7             # reject if an existing palette already contains >= this fraction
OUTPUT_DIR = os.path.join(PLOTS_DIR, "new_palettes")  # folder for the rendered images
PER_IMAGE = 5             # palettes per image
OUTPUT_JSON = os.path.join(RESULTS_DIR, "new_palettes.json")


@lru_cache(maxsize=None)
def rgb(c):
    return int(c[1:3], 16) / 255, int(c[3:5], 16) / 255, int(c[5:7], 16) / 255


@lru_cache(maxsize=None)
def hsv(c):
    return colorsys.rgb_to_hsv(*rgb(c))


def sat(c):
    return hsv(c)[1]


def hue(c):
    return hsv(c)[0]


def hue_dist(a, b):
    d = abs(a - b)
    return min(d, 1.0 - d)


def hsv_dist(a, b):
    """Full HSV distance (hue weighted 2x, circular).

    Catches same-hue value/lightness duplicates that a hue-only measure
    misses, e.g. three near-identical cyans.
    """
    ha, sa, va = hsv(a)
    hb, sb, vb = hsv(b)
    return math.sqrt((2 * hue_dist(ha, hb)) ** 2 + (sa - sb) ** 2 + (va - vb) ** 2)


def eligible(G, c):
    return sat(c) >= MIN_SAT and (MAX_DEG is None or G.degree(c) <= MAX_DEG)


def predict_missing_edges(G):
    """Rank missing edges among eligible nodes by a link-prediction heuristic.

    Returns [(score, u, v), ...] sorted by score descending. Each common
    neighbor w of (u, v) contributes 1/deg(w) ("ra"), 1/log(deg(w)) ("aa") or
    1 ("cn"); hubs barely count, so the ranking stays specific instead of
    collapsing into the neutral backbone.
    """
    weight = {"cn": lambda d: 1.0,
              "aa": lambda d: 1.0 / math.log(d) if d > 1 else 0.0,
              "ra": lambda d: 1.0 / d}[PREDICTOR]

    score = defaultdict(float)
    for w in G.nodes():
        dw = G.degree(w)
        if dw < 2 or dw > ANCHOR_CAP:
            continue
        nbrs = [x for x in G[w] if eligible(G, x)]
        for i in range(len(nbrs)):
            for j in range(i + 1, len(nbrs)):
                u, v = nbrs[i], nbrs[j]
                if G.has_edge(u, v):
                    continue
                if u > v:
                    u, v = v, u
                score[(u, v)] += weight(dw)
    return sorted(((s, u, v) for (u, v), s in score.items()), reverse=True)


def assemble(G, u, v):
    """Clique completion: {u, v} + diverse common neighbors -> palette (or None)."""
    pool = [c for c in set(G[u]) & set(G[v]) if eligible(G, c)]
    target = min(SIZE[1], 2 + len(pool))
    chosen = [u, v]

    while len(chosen) < target and pool:
        # candidates far enough (in HSV) from everything already chosen
        cands = [c for c in pool
                 if min(hsv_dist(c, x) for x in chosen) >= MIN_PAIR_DIST]
        if not cands:
            break
        # then spread: add the candidate farthest from its nearest chosen color
        best = max(cands, key=lambda c: min(hsv_dist(c, x) for x in chosen))
        chosen.append(best)
        pool.remove(best)

    return chosen if len(chosen) >= SIZE[0] else None


def jaccard_sets(a, b):
    return len(a & b) / len(a | b)


def is_novel(pal, palette_sets):
    s = set(pal)
    return all(len(s & p) / len(s) < NOVELTY for p in palette_sets)


def render_page(pals, path):
    """One row per palette: index label, then its 5 color chips."""
    n = len(pals)
    fig, axes = plt.subplots(n, 1, figsize=(8, 1.0 * n), squeeze=False)
    for ax, (i, pal) in zip(axes[:, 0], pals):
        ax.set_xlim(-1, len(pal))
        ax.set_ylim(0, 1)
        for j, c in enumerate(pal):
            ax.add_patch(plt.Rectangle((j, 0), 1, 1, facecolor=c,
                                       edgecolor="#bbbbbb", linewidth=0.3))
        ax.text(-0.5, 0.5, str(i), ha="center", va="center",
                fontsize=12, color="#333333")
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)


def render_pages(found, out_dir, per_image):
    """Split the palettes into images of `per_image` rows each."""
    os.makedirs(out_dir, exist_ok=True)
    idx_pals = [(i, pal) for i, (_, _, _, pal) in enumerate(found, 1)]
    for start in range(0, len(idx_pals), per_image):
        chunk = idx_pals[start:start + per_image]
        lo, hi = chunk[0][0], chunk[-1][0]
        name = f"{lo:03d}-{hi:03d}.png" if lo != hi else f"{lo:03d}.png"
        render_page(chunk, os.path.join(out_dir, name))
        print(f"-> {os.path.join(out_dir, name)}")


def main():
    palettes = load_palettes(INPUT)
    if QUANTIZE:
        palettes = [sorted({quantize_color(c, QUANT_STEP) for c in p}) for p in palettes]

    G = build_graph(palettes)
    if GIANT_ONLY:
        G = giant_component(G)

    palette_sets = [set(p) for p in palettes]
    ranked = predict_missing_edges(G)
    print(f"{len(ranked)} predicted missing edges\n")

    found, found_sets = [], []
    for s, u, v in ranked[:TOP_EDGES]:
        if hsv_dist(u, v) < MIN_PAIR_DIST:
            continue
        pal = assemble(G, u, v)
        if pal is None:
            continue
        ps = frozenset(pal)
        if not is_novel(pal, palette_sets):
            continue
        if any(jaccard_sets(ps, f) >= CROSS_JACCARD for f in found_sets):
            continue
        found_sets.append(ps)
        found.append((s, u, v, pal))
        if len(found) >= N_OUT:
            break

    print(f"emitted {len(found)} palettes\n")
    for i, (_, _, _, pal) in enumerate(found, 1):
        print(f"{i:3d}  {' '.join(pal)}")

    render_pages(found, OUTPUT_DIR, PER_IMAGE)
    out = [{"index": i, "colors": pal, "seed": [u, v], "score": round(s, 4)}
           for i, (s, u, v, pal) in enumerate(found, 1)]
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n-> {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
