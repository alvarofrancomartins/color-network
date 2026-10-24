"""Serve the palette-review pages and save liked palettes to results/.

Run from the repo root:

    python scripts/palette/review_server.py [port]

Routes:
  /             the 100-palette review page; POST /save writes the liked
                palettes to results/selected_palettes_{i}.json (``i``
                auto-increments, so each pass never overwrites an earlier one).
  /final        the final page (pick 10 of the common palettes); POST
                /save-final writes the chosen 10 to results/final_palettes.json.
"""

import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # scripts/palette/ -> repo root
HTML = ROOT / "review" / "palette_review.html"
FINAL_HTML = ROOT / "review" / "palette_final.html"
RESULTS_DIR = ROOT / "results"

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000


def next_index():
    """Smallest unused i for results/selected_palettes_{i}.json."""
    used = []
    for f in RESULTS_DIR.glob("selected_palettes_*.json"):
        m = re.fullmatch(r"selected_palettes_(\d+)\.json", f.name)
        if m:
            used.append(int(m.group(1)))
    return (max(used) + 1) if used else 1


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = HTML.read_bytes()
        elif self.path in ("/final", "/final.html"):
            body = FINAL_HTML.read_bytes()
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path == "/save":
            self._save()
        elif self.path == "/save-final":
            self._save_final()
        else:
            self.send_error(404)

    def _read_palettes(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            palettes = json.loads(self.rfile.read(length))["palettes"]
            assert isinstance(palettes, list)
            return palettes
        except Exception:
            return None

    def _save(self):
        palettes = self._read_palettes()
        if palettes is None:
            self._json(400, {"error": 'expected JSON body {"palettes": [...]}'})
            return
        RESULTS_DIR.mkdir(exist_ok=True)
        out = RESULTS_DIR / f"selected_palettes_{next_index()}.json"
        out.write_text(json.dumps(palettes, indent=2) + "\n")
        self._json(200, {"file": str(out), "count": len(palettes)})

    def _save_final(self):
        palettes = self._read_palettes()
        if palettes is None:
            self._json(400, {"error": 'expected JSON body {"palettes": [...]}'})
            return
        RESULTS_DIR.mkdir(exist_ok=True)
        out = RESULTS_DIR / "final_palettes.json"
        out.write_text(json.dumps(palettes, indent=2) + "\n")
        self._json(200, {"file": str(out), "count": len(palettes)})

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        sys.stderr.write("[review_server] %s\n" % (fmt % args))


def main():
    print(f"Serving {HTML.name} at http://localhost:{PORT}")
    print(f"Final selection:   http://localhost:{PORT}/final")
    print(f"Saves liked palettes to {RESULTS_DIR}/selected_palettes_{{i}}.json")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
