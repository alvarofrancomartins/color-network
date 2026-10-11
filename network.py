"""Build the color co-occurrence network and render it.

Two colors are linked when they appear in the same palette.
Reads palettes.json (from data.py) and writes color_network.png.
"""

import graph_tool.all as gt

from graph import (build_graph, centrality, draw, giant_component, layout,
                   load_palettes, to_graph_tool, vertex_rgba)

# ---- config ----------------------------------------------------------------
INPUT = "palettes.json"
GIANT_ONLY  = True          # keep only the giant connected component
DROP_HUBS   = None          # e.g. 500 -> drop colors with degree > 500
SIZE_BY     = "betweenness"      # "degree" | "betweenness"
SIZE        = dict(mi=2, ma=45, power=0.8)
BG          = [0.07, 0.07, 0.07, 1.0]
SEED        = 42
OUTPUT      = "color_network.png"
OUTPUT_SIZE = (3000, 3000)
NUM_ITERS   = 1000

def main():
    palettes = load_palettes(INPUT)
    G = build_graph(palettes)

    if GIANT_ONLY:
        G = giant_component(G)
    if DROP_HUBS:
        G.remove_nodes_from([c for c, d in G.degree() if d > DROP_HUBS])

    g, nodes, idx = to_graph_tool(G)

    v_rgba = vertex_rgba(g, nodes)
    central = centrality(g, SIZE_BY)
    size = gt.prop_to_size(central, **SIZE)   # node size grows with centrality

    pos = layout(g, SEED, NUM_ITERS)
    draw(g, pos, v_rgba, size, BG, OUTPUT_SIZE, OUTPUT)

    print(f"{g.num_vertices()} vertices | {g.num_edges()} edges -> {OUTPUT}")


if __name__ == "__main__":
    main()
