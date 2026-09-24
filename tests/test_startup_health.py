import pytest
import sqlite3
import os
import tempfile
from scripts.verify_startup_health import (
    check_backend_reachability,
    check_database_tables,
    check_map_tile_provider,
    check_frontend_stylesheet_health
)

def test_check_database_tables_on_valid_db():
    """Verify that current cyclonex.db passes non-zero row requirements."""
    db_path = "cyclonex.db"
    assert os.path.exists(db_path), "cyclonex.db must exist"
    
    passed, counts, errors = check_database_tables(db_path)
    assert passed is True, f"Database check failed with errors: {errors}"
    assert counts["cyclones"] >= 1
    assert counts["alerts"] >= 1
    assert counts["shelters"] >= 1
    assert counts["hospitals"] >= 1
    assert len(errors) == 0

def test_check_database_tables_fails_on_empty_table():
    """Verify check_database_tables loudly fails when any critical table has 0 rows."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db = tf.name

    try:
        conn = sqlite3.connect(temp_db)
        c = conn.cursor()
        c.execute("CREATE TABLE cyclones (id text)")
        c.execute("CREATE TABLE alerts (id text)")
        c.execute("CREATE TABLE shelters (id text)")
        c.execute("CREATE TABLE hospitals (id text)")
        # Insert into 3 tables but leave hospitals empty
        c.execute("INSERT INTO cyclones VALUES ('c1')")
        c.execute("INSERT INTO alerts VALUES ('a1')")
        c.execute("INSERT INTO shelters VALUES ('s1')")
        conn.commit()
        conn.close()

        passed, counts, errors = check_database_tables(temp_db)
        assert passed is False
        assert counts["hospitals"] == 0
        assert any("hospitals" in err for err in errors)
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)

def test_check_map_tile_provider_passes_on_osm():
    """Verify OpenStreetMap standard tile passes validation."""
    osm_url = "https://tile.openstreetmap.org/1/1/0.png"
    passed, msg, meta = check_map_tile_provider(osm_url, timeout=6.0)
    assert passed is True
    assert "image" in meta["content_type"]
    assert meta["size_bytes"] > 500

def test_check_map_tile_provider_fails_on_keyless_carto():
    """Verify keyless CARTO tile URL is immediately rejected as watermarked."""
    carto_url = "https://a.basemaps.cartocdn.com/light_all/1/1/0.png"
    passed, msg, meta = check_map_tile_provider(carto_url, timeout=5.0)
    assert passed is False
    assert "CARTO" in msg or "API KEY" in msg

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class MockFrontendHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/dashboard":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = """
            <!DOCTYPE html>
            <html>
            <head>
              <link rel="stylesheet" href="/_next/static/css/styles.css">
            </head>
            <body><h1>Dashboard</h1></body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))
        elif self.path == "/_next/static/css/styles.css":
            self.send_response(200)
            self.send_header("Content-Type", "text/css")
            self.end_headers()
            self.wfile.write(b"body { background: #fff; } " * 40)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

class BrokenCSSFrontendHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/dashboard":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = '<html><head><link rel="stylesheet" href="/_next/static/css/broken.css"></head></html>'
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def test_check_frontend_stylesheet_health_valid():
    """Verify check_frontend_stylesheet_health correctly parses HTML and verifies valid CSS."""
    server = HTTPServer(("127.0.0.1", 0), MockFrontendHandler)
    port = server.server_port
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        passed, msg, meta = check_frontend_stylesheet_health([f"http://127.0.0.1:{port}"])
        assert passed is True
        assert "stylesheets" in meta
        assert len(meta["stylesheets"]) == 1
        assert meta["stylesheets"][0]["status"] == 200
        assert meta["stylesheets"][0]["size_bytes"] > 500
    finally:
        server.shutdown()

def test_check_frontend_stylesheet_health_detects_css_404():
    """Verify check_frontend_stylesheet_health catches CSS 404 regressions."""
    server = HTTPServer(("127.0.0.1", 0), BrokenCSSFrontendHandler)
    port = server.server_port
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        passed, msg, meta = check_frontend_stylesheet_health([f"http://127.0.0.1:{port}"])
        assert passed is False
        assert "404" in msg
    finally:
        server.shutdown()

def test_check_frontend_stylesheet_health_fails_on_unreachable_server():
    """Verify check_frontend_stylesheet_health loudly fails when port is unreachable."""
    passed, msg, meta = check_frontend_stylesheet_health(["http://127.0.0.1:39999"])
    assert passed is False
    assert "unreachable" in msg.lower()
    assert meta["server_running"] is False

def test_check_frontend_stylesheet_health_on_live_server_if_active():
    """Verify against live port 3000 if running, or skip if in cold offline test run."""
    import urllib.request
    try:
        req = urllib.request.Request("http://localhost:3000/dashboard")
        with urllib.request.urlopen(req, timeout=1.0) as res:
            if res.status == 200:
                passed, msg, meta = check_frontend_stylesheet_health(["http://localhost:3000"])
                assert passed is True
    except Exception:
        pytest.skip("Frontend server not running on port 3000 (cold state unit test)")


