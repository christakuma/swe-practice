"""The checkout service. Prices a basket and would charge it.

The payments key comes from the environment at run time -- in production from
the orchestrator's secret store, on a laptop from `--env-file .env`. The image
should never need to hold it.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from pricing import total_pence


class Checkout(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        configured = bool(os.environ.get("PAYMENTS_API_KEY"))
        body = json.dumps(
            {"basket_total_pence": total_pence([250, 1199, 75]), "payments": configured}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print("checkout listening on 0.0.0.0:8000", flush=True)
    HTTPServer(("0.0.0.0", 8000), Checkout).serve_forever()
