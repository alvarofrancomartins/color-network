"""Generate the two review pages from the results JSON.

The review pages are the interactive selection tool (palette_review.html:
like/dislike the 100 predicted palettes; palette_final.html: pick 10 of the
common ones). Their embedded PALETTES data is derived from results/, so this
script re-derives it and rewrites the ``const PALETTES = [...]`` line in each
page in place, keeping the pages in sync with the results.

    python scripts/palette/build_review_pages.py
"""

import json
import os
import re
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[2])   # scripts/palette/ -> repo root
RESULTS_DIR = os.path.join(ROOT, "results")
REVIEW_DIR = os.path.join(ROOT, "review")

# (results file, output page). The pages' CSS/JS lives in review/ and is static;
# only the PALETTES const is regenerated here.
PAGES = [
    ("new_palettes.json", "palette_review.html"),
    ("common_palettes.json", "palette_final.html"),
]


def slim(entries):
    """results entries -> [{i, colors, seed, score}] (drop the review-only fields)."""
    return [{"i": p["index"], "colors": p["colors"], "seed": p["seed"], "score": p["score"]}
            for p in entries]


def main():
    os.makedirs(REVIEW_DIR, exist_ok=True)
    for name, page in PAGES:
        with open(os.path.join(RESULTS_DIR, name)) as f:
            results = json.load(f)
        entries = results if name == "new_palettes.json" else results["common_palettes"]
        palettes = slim(entries)

        path = os.path.join(REVIEW_DIR, page)
        html = open(path).read()
        line = "const PALETTES = " + json.dumps(palettes, separators=(",", ":")) + ";"
        html, n = re.subn(r"const PALETTES = \[.*?\];", lambda m: line, html,
                          count=1, flags=re.DOTALL)
        if n != 1:
            raise SystemExit(f"could not find `const PALETTES` in {path}")
        with open(path, "w") as f:
            f.write(html)
        print(f"{len(palettes)} palettes -> {path}")


if __name__ == "__main__":
    main()
