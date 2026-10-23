"""Local HTTP server for the OBS browser source: the overlay page and its JSON feed."""

import json
import logging
import threading
from collections.abc import Callable
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
PAGES = {"/": "overlay.html", "/overlay": "overlay.html"}


class OverlayServer:
    def __init__(self, port: int, get_state: Callable[[], dict]):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                path = urlsplit(self.path).path
                if path == "/api/state":
                    self._send(json.dumps(get_state()).encode("utf-8"), "application/json; charset=utf-8")
                elif path in PAGES:
                    self._send((STATIC_DIR / PAGES[path]).read_bytes(), "text/html; charset=utf-8")
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)

            def _send(self, body: bytes, content_type: str):
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                logger.debug("%s - %s", self.address_string(), format % args)

        # Loopback only: the page is meant for OBS on the same machine.
        self._httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self._httpd.daemon_threads = True
        self.port = self._httpd.server_address[1]

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"

    def start(self) -> None:
        threading.Thread(target=self._httpd.serve_forever, name="overlay-http", daemon=True).start()
        logger.info("Overlay server listening on %s", self.url)

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
