"""Shared building blocks for the color co-occurrence network.

Two colors are linked when they appear in the same palette. The scripts in
scripts/network/, scripts/stats/ and scripts/palette/ each compose these pieces
with their own config instead of repeating the graph-building and rendering
logic.
"""

import json
import os
from itertools import combinations
from pathlib import Path

import networkx as nx
import graph_tool.all as gt

# Repository layout: data/ (input), plots/ (figures), results/ (generated data),
# scripts/ (code grouped by goal; this file is the shared module).
ROOT = str(Path(__file__).resolve().parents[2])  # scripts/shared/ -> repo root
DATA_DIR = os.path.join(ROOT, "data")
PLOTS_DIR = os.path.join(ROOT, "plots")
RESULTS_DIR = os.path.join(ROOT, "results")


def load_palettes(path):
    """Read palettes.json -> list of palettes (each a list of hex colors)."""
    with open(path) as f:
        return json.load(f)


def build_graph(palettes):
    """Unweighted co-occurrence graph: edge iff two colors share a palette."""
    G = nx.Graph()
    for cs in palettes:
        G.add_edges_from(combinations(cs, 2))
    return G


def quantize_color(c, step=16):
    """Round each RGB channel to a `step` grid -> canonical hex.

    Collapses near-identical encodings of the same color (e.g. #FF8000 and
    #FF7F00) into one node so they don't masquerade as a "new" pairing.
    """
    r = min(255, round(int(c[1:3], 16) / step) * step)
    g = min(255, round(int(c[3:5], 16) / step) * step)
    b = min(255, round(int(c[5:7], 16) / step) * step)
    return f"#{r:02X}{g:02X}{b:02X}"


def giant_component(G):
    """Largest connected component."""
    return G.subgraph(max(nx.connected_components(G), key=len)).copy()


def to_graph_tool(G):
    """networkx graph -> (graph-tool graph, nodes, idx).

    Nodes are sorted by ascending degree so hubs are added last and drawn
    on top. ``idx`` maps a color back to its graph-tool vertex index.
    """
    nodes = sorted(G, key=lambda c: G.degree(c))
    idx = {c: i for i, c in enumerate(nodes)}

    g = gt.Graph(directed=False)
    g.add_vertex(len(nodes))
    g.add_edge_list([(idx[u], idx[v]) for u, v in G.edges()])
    return g, nodes, idx


def vertex_rgba(g, nodes):
    """Per-vertex fill color: each node drawn in its own hex."""
    return g.new_vp(
        "vector<double>",
        [[int(c[1:3], 16) / 255, int(c[3:5], 16) / 255,
          int(c[5:7], 16) / 255, 1.0] for c in nodes],
    )


def centrality(g, size_by):
    """Vertex centrality property map: "degree" or "betweenness"."""
    if size_by == "degree":
        return g.degree_property_map("total")
    return gt.betweenness(g)[0]


def betweenness_dict(g, nodes, idx):
    """{color: betweenness} mapping, for ranking/scatter plots."""
    vb, _ = gt.betweenness(g)
    return {c: vb[idx[c]] for c in nodes}


def layout(g, seed, max_iter):
    """Seeded force-directed (sfdp) layout."""
    gt.seed_rng(seed)
    return gt.sfdp_layout(g, verbose=False, max_iter=max_iter)


def draw(g, pos, v_rgba, size, bg, output_size, output, edge_pen_width=0.3):
    """Render the graph to a PNG, honouring output_size exactly."""
    kwargs = dict(
        pos=pos,
        vertex_fill_color=v_rgba,     # node color = its own hex
        vertex_color=[0, 0, 0, 0],    # no outline
        vertex_size=size,
        vertex_pen_width=0,
        edge_color=[1, 1, 1, 0.04],
        bg_color=bg,
        output_size=output_size,
        adjust_aspect=False,          # honour output_size exactly
        output=output,
    )
    if edge_pen_width is not None:    # None -> use graph-tool's default width
        kwargs["edge_pen_width"] = edge_pen_width
    gt.graph_draw(g, **kwargs)
