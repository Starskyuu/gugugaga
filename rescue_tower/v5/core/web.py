"""提供状态 API、任务控制、手动控制和最新相机画面。"""

from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import config
from core.mission import MissionController
from core.state import SystemState


STATIC_HTML = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "index.html")


def make_handler(state: SystemState, mission: MissionController):
    class Handler(BaseHTTPRequestHandler):
        def _headers(self, code=200, content_type="application/json; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def _json(self, data, code=200):
            self._headers(code)
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

        def do_OPTIONS(self):
            self._headers(204)

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/status":
                self._json(state.snapshot())
            elif path in {"/F", "/B", "/L", "/R", "/S"}:
                command = path[1:]
                ok = mission.manual(command)
                self._headers(200 if ok else 502, "text/plain; charset=utf-8")
                self.wfile.write(command.encode())
            elif path == "/video":
                self._video()
            elif path == "/":
                self._headers(200, "text/html; charset=utf-8")
                with open(STATIC_HTML, "rb") as page:
                    self.wfile.write(page.read())
            else:
                self._json({"error": "not found"}, 404)

        def do_POST(self):
            path = urlparse(self.path).path
            if path == "/api/mission/start":
                self._json({"ok": mission.start(False)})
            elif path == "/api/mission/test":
                self._json({"ok": mission.start(True)})
            elif path == "/api/mission/reset":
                mission.reset(); self._json({"ok": True})
            elif path == "/api/estop":
                mission.abort("网页紧急停车"); self._json({"ok": True})
            elif path == "/api/lift/up":
                self._json({"ok": mission.lift.send("U")})
            elif path == "/api/lift/down":
                self._json({"ok": mission.lift.send("D")})
            else:
                self._json({"error": "not found"}, 404)

        def _video(self):
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            last_mtime = 0.0
            try:
                while True:
                    try:
                        mtime = os.path.getmtime(config.VISION_JPEG)
                        if mtime != last_mtime:
                            with open(config.VISION_JPEG, "rb") as image:
                                data = image.read()
                            self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + data + b"\r\n")
                            self.wfile.flush(); last_mtime = mtime
                    except FileNotFoundError:
                        pass
                    time.sleep(0.08)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, fmt, *args):
            return
    return Handler


def serve(state: SystemState, mission: MissionController) -> None:
    server = ThreadingHTTPServer((config.WEB_HOST, config.WEB_PORT), make_handler(state, mission))
    print(f"网页/API：http://0.0.0.0:{config.WEB_PORT}")
    server.serve_forever()
