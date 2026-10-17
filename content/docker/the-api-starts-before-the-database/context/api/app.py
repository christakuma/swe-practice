"""The orders API. Connects to its database once, at startup.

No retry loop, deliberately: the team's rule is that a service which cannot
reach its dependencies should fail loudly and let the orchestrator decide.
Which means the orchestrator has to decide well.
"""

import json
import os
import socket
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlsplit

URL = urlsplit(os.environ["DATABASE_URL"])
HOST, PORT = URL.hostname, URL.port or 5432


class Health(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = json.dumps({"database": f"{HOST}:{PORT}", "reachable": reachable()})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode() + b"\n")

    def log_message(self, *args: object) -> None:
        pass


def reachable() -> bool:
    try:
        socket.create_connection((HOST, PORT), timeout=2).close()
    except OSError:
        return False
    return True


if __name__ == "__main__":
    if not reachable():
        print(f"FATAL: could not connect to the database at {HOST}:{PORT}", flush=True)
        sys.exit(1)
    print(f"connected to the database at {HOST}:{PORT}", flush=True)
    print("orders API listening on 0.0.0.0:8000", flush=True)
    HTTPServer(("0.0.0.0", 8000), Health).serve_forever()
