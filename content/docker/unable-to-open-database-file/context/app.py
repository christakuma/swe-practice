"""The uploads service. Keeps a ledger of what it has been sent, in SQLite.

The ledger lives under `data/` next to this file. The directory is created at
start-up if it is missing, so a fresh container needs nothing prepared for it.
"""

import json
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"


def open_ledger() -> sqlite3.Connection:
    DATA.mkdir(parents=True, exist_ok=True)
    ledger = sqlite3.connect(DATA / "ledger.db")
    ledger.execute("CREATE TABLE IF NOT EXISTS uploads (name TEXT, size INTEGER)")
    ledger.commit()
    return ledger


LEDGER = open_ledger()


class Uploads(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        size = int(self.headers.get("Content-Length", 0))
        self.rfile.read(size)
        LEDGER.execute("INSERT INTO uploads VALUES (?, ?)", (self.path, size))
        LEDGER.commit()
        self.reply({"stored": self.path, "bytes": size})

    def do_GET(self) -> None:
        (count,) = LEDGER.execute("SELECT COUNT(*) FROM uploads").fetchone()
        self.reply({"uploads": count})

    def reply(self, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print("uploads listening on 0.0.0.0:8000", flush=True)
    HTTPServer(("0.0.0.0", 8000), Uploads).serve_forever()
