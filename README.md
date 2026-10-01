# Color Co-occurrence Network

Color palettes connect colors and different color palettes may share some of the same colors. Hence, this can be seen as a network. What does that network look like?

![Color co-occurrence network](color_network.png)

To answer my curiosity, I built this. A network of colors built from the [pypalettes](https://github.com/JosephBARBIERDARNAL/pypalettes) dataset: two colors are linked when they appear together in the same palette. Each node is drawn in its own color and sized by its centrality.

Run:

```bash
python data.py && python network.py
```
