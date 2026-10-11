"""Visualize the k-core of the color co-occurrence network.

The k-core is the maximal subgraph in which every node has degree >= k:
nodes are iteratively removed until all remaining have degree >= k.
Reads palettes.json (from data.py) and writes kcore.png.
"""

import networkx as nx
import graph_tool.all as gt

from graph import (build_graph, centrality, draw, giant_component, layout,
                   load_palettes, to_graph_tool, vertex_rgba)

# ---- config ----------------------------------------------------------------
INPUT = "palettes.json"
K = 30               # core number: keep nodes with degree >= K
GIANT_ONLY = False   # keep only the giant component of the k-core
SIZE_BY = "degree"   # "degree" | "betweenness"
SIZE = dict(mi=2, ma=45, power=0.8)
BG = [0.07, 0.07, 0.07, 1.0]
SEED = 42
OUTPUT = "kcore.png"
OUTPUT_SIZE = (3000, 3000)
NUM_ITERS   = 1000

def main():
    palettes = load_palettes(INPUT)
    G = build_graph(palettes)

    core = nx.core_number(G)
    print(f"max core number: {max(core.values())}")

    # k-core: maximal subgraph with min degree >= K
    G = nx.k_core(G, K)
    if G.number_of_nodes() == 0:
        raise SystemExit(f"empty k-core for k={K} (max core number = {max(core.values())})")
    if GIANT_ONLY:
        G = giant_component(G)

    g, nodes, idx = to_graph_tool(G)

    v_rgba = vertex_rgba(g, nodes)
    central = centrality(g, SIZE_BY)
    size = gt.prop_to_size(central, **SIZE)

    pos = layout(g, SEED, NUM_ITERS)
    draw(g, pos, v_rgba, size, BG, OUTPUT_SIZE, OUTPUT, edge_pen_width=None)

    print(f"k-core (k={K}): {g.num_vertices()} vertices | {g.num_edges()} edges -> {OUTPUT}")


if __name__ == "__main__":
    main()
