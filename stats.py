"""Statistics of the color co-occurrence network.

Plots:
  - stats_degree.png                top colors by degree (descending)
  - stats_betweenness.png           top colors by betweenness (descending)
  - stats_degree_vs_betweenness.png scatter, one point per color

In every plot, a mark is filled with the color it represents.
Reads palettes.json (from data.py).
"""

import json
from itertools import combinations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import graph_tool.all as gt

# ---- config ----------------------------------------------------------------
INPUT = "palettes.json"
TOP = 25
GIANT_ONLY = True       # rank within the giant component (as rendered in network.py)

# rank plots (light theme)
EDGE = "#8a8a8a"        # bar outline: keeps near-white / near-black bars visible
TEXT = "#1a1a1a"        # neutral ink for labels
BAR_H = 0.72            # bar thickness (leaves a gap between bars)

# scatter (dark theme, echoing the network figure)
SIZE_BY = "degree"      # point area scales with "degree" or "betweenness"
SIZE = dict(mi=8, ma=220, power=0.5)
LOG_X = True            # degree is heavy-tailed -> log x axis
LOG_Y = True           # log y axis too (drops zero-betweenness nodes)
SC_BG = "#0d0d0d"
SC_TEXT = "#d9d9d9"
SC_TICK = "#9a9a9a"
SC_GRID = "#2b2b2b"
SC_SPINE = "#4a4a4a"
SC_EDGE = "#ffffff"     # thin outline so near-black points stay visible
SC_ALPHA = 0.85


def build_graph(path):
    with open(path) as f:
        palettes = json.load(f)
    G = nx.Graph()
    for cs in palettes:
        G.add_edges_from(combinations(cs, 2))
    if GIANT_ONLY:
        G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    return G


def betweenness(G):
    """Node betweenness via graph-tool (fast)."""
    nodes = list(G)
    idx = {c: i for i, c in enumerate(nodes)}
    g = gt.Graph(directed=False)
    g.add_vertex(len(nodes))
    g.add_edge_list([(idx[u], idx[v]) for u, v in G.edges()])
    vb, _ = gt.betweenness(g)
    return {c: vb[idx[c]] for c in nodes}


def rank_plot(pairs, title, path, fmt, xlabel):
    """Horizontal bars, largest at the top, each filled with its own hex."""
    colors = [c for c, _ in pairs]          # pairs already sorted descending
    values = [v for _, v in pairs]
    y = range(len(pairs))

    fig, ax = plt.subplots(figsize=(9, 0.42 * len(pairs) + 1.6))
    ax.barh(y, values, color=colors, edgecolor=EDGE, linewidth=0.8,
            height=BAR_H, zorder=3)

    ax.set_yticks(list(y))
    ax.set_yticklabels(colors, fontsize=10)
    ax.invert_yaxis()                        # largest moves to the top

    for yi, v in zip(y, values):             # value at the end of each bar
        ax.text(v, yi, f" {fmt(v)}", va="center", ha="left", fontsize=9, color=TEXT)

    ax.set_xlim(0, max(values) * 1.18)
    ax.set_xlabel(xlabel, color=TEXT)
    ax.set_title(title, loc="left", fontweight="bold", color=TEXT)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#d0d0d0")
    ax.spines["bottom"].set_color("#d0d0d0")
    ax.tick_params(colors="#666666", length=0)
    ax.grid(axis="x", color="#ececec", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)
    print(f"{title} -> {path}")


def scatter_plot(deg, btw, path):
    """Betweenness vs degree; one point per color, area = SIZE_BY, fill = hex."""
    nodes = list(deg)
    x = [deg[c] for c in nodes]
    y = [btw[c] for c in nodes]

    if LOG_Y:                                # log y can't show zero-betweenness nodes
        keep = [i for i, v in enumerate(y) if v > 0]
        print(f"  log y: dropped {len(nodes) - len(keep)} zero-betweenness nodes")
        nodes = [nodes[i] for i in keep]
        x = [x[i] for i in keep]
        y = [y[i] for i in keep]

    vals = [deg[c] for c in nodes] if SIZE_BY == "degree" else [btw[c] for c in nodes]
    vmin, vmax = min(vals), max(vals)
    if vmax == vmin:
        vmax = vmin + 1
    s = [SIZE["mi"] + (SIZE["ma"] - SIZE["mi"]) * ((v - vmin) / (vmax - vmin)) ** SIZE["power"]
         for v in vals]

    fig, ax = plt.subplots(figsize=(11, 8), facecolor=SC_BG)
    ax.set_facecolor(SC_BG)
    ax.scatter(x, y, s=s, c=nodes, edgecolor=SC_EDGE, linewidth=0.6, alpha=SC_ALPHA)

    if LOG_X:
        ax.set_xscale("log")
    if LOG_Y:
        ax.set_yscale("log")
    ax.set_xlabel("degree", color=SC_TEXT, fontsize=12)
    ax.set_ylabel("betweenness centrality", color=SC_TEXT, fontsize=12)
    ax.set_title(f"Betweenness vs degree  (point area ~ {SIZE_BY})",
                 loc="left", fontweight="bold", color=SC_TEXT, fontsize=13)

    ax.tick_params(colors=SC_TICK, labelsize=10)
    for sp in ax.spines.values():
        sp.set_color(SC_SPINE)
    ax.grid(color=SC_GRID, linewidth=0.7, alpha=0.6)
    ax.set_axisbelow(True)

    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SC_BG)
    plt.close(fig)
    print(f"Betweenness vs degree -> {path}")


def main():
    G = build_graph(INPUT)

    deg = dict(G.degree())
    btw = betweenness(G)

    top_deg = sorted(deg.items(), key=lambda kv: kv[1], reverse=True)[:TOP]
    top_btw = sorted(btw.items(), key=lambda kv: kv[1], reverse=True)[:TOP]

    rank_plot(top_deg, f"Top {TOP} colors by degree", "stats_degree.png",
              lambda v: f"{v:,}", "degree")
    rank_plot(top_btw, f"Top {TOP} colors by betweenness", "stats_betweenness.png",
              lambda v: f"{v:.4f}", "betweenness centrality")
    scatter_plot(deg, btw, "stats_degree_vs_betweenness.png")


if __name__ == "__main__":
    main()
