"""Visualize the k-core of the color co-occurrence network.

The k-core is the maximal subgraph in which every node has degree >= k:
nodes are iteratively removed until all remaining have degree >= k.
Reads palettes.json (from data.py) and writes kcore.png.
"""

import json
from itertools import combinations

import networkx as nx
import graph_tool.all as gt

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
    with open(INPUT) as f:
        palettes = json.load(f)

    # unweighted co-occurrence graph: edge iff two colors share a palette
    G = nx.Graph()
    for cs in palettes:
        G.add_edges_from(combinations(cs, 2))

    core = nx.core_number(G)
    print(f"max core number: {max(core.values())}")

    # k-core: maximal subgraph with min degree >= K
    G = nx.k_core(G, K)
    if G.number_of_nodes() == 0:
        raise SystemExit(f"empty k-core for k={K} (max core number = {max(core.values())})")
    if GIANT_ONLY:
        G = G.subgraph(max(nx.connected_components(G), key=len)).copy()

    # graph-tool graph (low degree first -> hubs drawn on top)
    nodes = sorted(G, key=lambda c: G.degree(c))
    idx = {c: i for i, c in enumerate(nodes)}

    g = gt.Graph(directed=False)
    g.add_vertex(len(nodes))
    g.add_edge_list([(idx[u], idx[v]) for u, v in G.edges()])

    v_rgba = g.new_vp("vector<double>",
                      [[int(c[1:3], 16) / 255, int(c[3:5], 16) / 255,
                        int(c[5:7], 16) / 255, 1.0] for c in nodes])

    central = g.degree_property_map("total") if SIZE_BY == "degree" else gt.betweenness(g)[0]
    size = gt.prop_to_size(central, **SIZE)

    gt.seed_rng(SEED)
    pos = gt.sfdp_layout(g, verbose=False, max_iter = NUM_ITERS)

    gt.graph_draw(
        g, pos=pos,
        vertex_fill_color=v_rgba,     # node color = its own hex
        vertex_color=[0, 0, 0, 0],    # no outline
        vertex_size=size,
        vertex_pen_width=0,
        edge_color=[1, 1, 1, 0.04],
        #edge_pen_width=0.3,
        bg_color=BG,
        output_size=OUTPUT_SIZE,
        adjust_aspect=False,          # honour OUTPUT_SIZE exactly
        output=OUTPUT,
    )
    print(f"k-core (k={K}): {g.num_vertices()} vertices | {g.num_edges()} edges -> {OUTPUT}")


if __name__ == "__main__":
    main()
