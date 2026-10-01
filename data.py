"""Fetch pypalettes and save the normalized palettes used by the network.

Output: palettes.json -- a list of palettes, each a sorted, deduped list of
        7-char uppercase hex colors (alpha byte dropped unless KEEP_ALPHA).
"""

import ast
import json
from importlib.resources import files

import pandas as pd

# ---- config ----------------------------------------------------------------
KEEP_ALPHA = False          # True keeps the trailing alpha byte, e.g. #FED789FF
MIN_SIZE, MAX_SIZE = 2, 50  # skip palettes outside this size range
OUTPUT = "palettes.json"


def normalize(s):
    """One palette -> sorted, deduped list of hex colors."""
    cs = [c.upper() if KEEP_ALPHA else c[:7].upper() for c in ast.literal_eval(s)]
    return sorted(set(cs))


def main():
    df = pd.read_csv(files("pypalettes") / "palettes.csv")
    palettes = [normalize(s) for s in df["palette"]]
    palettes = [cs for cs in palettes if MIN_SIZE <= len(cs) <= MAX_SIZE]

    with open(OUTPUT, "w") as f:
        json.dump(palettes, f)

    print(f"{len(palettes)} palettes -> {OUTPUT}")


if __name__ == "__main__":
    main()
