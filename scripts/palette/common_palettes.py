"""Extract the palettes chosen in common across the selected-palette files.

Each results/selected_palettes_{i}.json is one pass over the same 100 predicted
palettes (the review tool resets and lets you go over them again). A palette's
``index`` is its stable id across files, so the palettes you chose "in common"
are those whose index shows up in several of the files — by default, in ALL of
them (your consistently liked palettes).

    python scripts/palette/common_palettes.py
"""

import glob
import json
import os
from collections import OrderedDict
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[2])          # scripts/palette/ -> repo root
RESULTS_DIR = os.path.join(ROOT, "results")
OUTPUT = os.path.join(RESULTS_DIR, "common_palettes.json")
PATTERN = os.path.join(RESULTS_DIR, "selected_palettes_*.json")
MIN_FILES = None   # None = chosen in every file; set to 2 for "chosen in >= 2 files"


def load_by_index(pattern):
    """Map palette index -> full palette, plus how many files chose it and which."""
    by_index = OrderedDict()
    files = []
    for path in sorted(glob.glob(pattern)):
        files.append(os.path.basename(path))
        with open(path) as f:
            seen = set()
            for pal in json.load(f):
                i = pal["index"]
                if i in seen:          # a file should list a palette once
                    continue
                seen.add(i)
                entry = by_index.setdefault(i, dict(pal, count=0, files=[]))
                entry["count"] += 1
                entry["files"].append(os.path.basename(path))
    return by_index, files


def main():
    by_index, files = load_by_index(PATTERN)
    if not files:
        print(f"No files found under {PATTERN}")
        return

    min_files = len(files) if MIN_FILES is None else MIN_FILES
    common = [by_index[i] for i in sorted(by_index) if by_index[i]["count"] >= min_files]

    out = {
        "source_files": files,
        "min_files": min_files,
        "common_palettes": common,
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(out, f, indent=2)

    print(f"{len(common)} palettes chosen in >= {min_files} of {len(files)} files -> {OUTPUT}")


if __name__ == "__main__":
    main()
