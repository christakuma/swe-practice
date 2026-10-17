"""The orders API. Waits for its database, then serves `/health`.

It retries for thirty seconds before giving up, so a database that is
merely slow to start is not an outage. A database it cannot reach at all
still is, and that is what the log will say.
"""

import json
import os
import socket
import sys
import time
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
    for attempt in range(1, 31):
        if reachable():
            print(f"connected to the database at {HOST}:{PORT}", flush=True)
            break
        print(
            f"database {HOST}:{PORT} refused the connection (attempt {attempt}/30)",
            flush=True,
        )
        time.sleep(1)
    else:
        print("giving up: no database", flush=True)
        sys.exit(1)
    print("orders API listening on 0.0.0.0:8000", flush=True)
    HTTPServer(("0.0.0.0", 8000), Health).serve_forever()
