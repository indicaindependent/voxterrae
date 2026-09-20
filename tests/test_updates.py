"""H3 unit tests: version ordering + feed parsing against a local HTTP server (no network)."""
import json, threading, http.server
from voxterrae.app import updates as U

def test_version_order():
    assert U.is_newer("0.1.1", "0.1.0") and U.is_newer("0.2.0", "0.1.9") and U.is_newer("1.0.0", "0.9.9")
    assert not U.is_newer("0.1.0", "0.1.0") and not U.is_newer("0.0.9", "0.1.0")
    assert U.is_newer("0.1.0", "0.1.0-rc1") and not U.is_newer("0.1.0-rc1", "0.1.0")   # pre-release sorts below final
    assert U.is_newer("v0.1.1", "0.1.0")

def _serve(payload, status=200):
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            self.send_response(status); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(body)
        def log_message(self, *a): pass
    srv = http.server.HTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}/api/latest.json"

def test_feed_newer_current_unknown():
    srv, url = _serve({"version": "0.1.1", "url": "https://voxterrae.app/releases/0.1.1"})
    r = U.check("0.1.0", url); assert r == {"status": "newer", "latest": "0.1.1", "url": "https://voxterrae.app/releases/0.1.1"}
    r = U.check("0.1.1", url); assert r["status"] == "current"
    srv.shutdown()
    srv, url = _serve(b"<html>not json</html>"); assert U.check("0.1.0", url)["status"] == "unknown"; srv.shutdown()
    srv, url = _serve({"nope": 1}); assert U.check("0.1.0", url)["status"] == "unknown"; srv.shutdown()
    assert U.check("0.1.0", "http://127.0.0.1:9/x", timeout=0.5)["status"] == "unknown"   # connection refused -> unknown, never raises
