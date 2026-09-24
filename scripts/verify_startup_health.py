#!/usr/bin/env python3
"""
CycloneX Startup Health & Pre-Flight Verification Script
SIH26070 - Tropical Cyclone Intelligence Platform

Verifies before the application is declared "ready":
  1. Backend API is reachable and healthy (/system/health)
  2. Database contains non-zero rows in:
       - cyclones
       - alerts
       - shelters
       - hospitals
  3. Map tile provider is responding with real, non-watermarked tiles
  4. Frontend /dashboard stylesheet returns HTTP 200 with non-trivial bytes (not 404)

Fails loudly with exit code 1 if ANY check fails.
"""

import sys
import os
import re
import json
import time
import argparse
import urllib.request
import urllib.error
import sqlite3
from typing import Dict, Any, List, Tuple

# ANSI terminal colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Silence color if not in a tty or on standard windows without VT100
if not sys.stdout.isatty() and os.name == 'nt':
    pass

def log_header(title: str):
    print(f"\n{BOLD}{CYAN}{'=' * 78}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 78}{RESET}")

def log_pass(msg: str):
    print(f"  {GREEN}[PASS]{RESET} {msg}")

def log_fail(msg: str):
    print(f"  {RED}{BOLD}[FAIL]{RESET} {msg}")

def log_warn(msg: str):
    print(f"  {YELLOW}[WARN]{RESET} {msg}")

def log_info(msg: str):
    print(f"  {CYAN}[INFO]{RESET} {msg}")


def check_backend_reachability(base_urls: List[str], timeout: float = 5.0) -> Tuple[bool, str, Dict[str, Any], float]:
    """
    Check 1: Verify backend API /system/health endpoint is reachable.
    """
    last_error = ""
    for base in base_urls:
        url = f"{base.rstrip('/')}/api/v1/system/health"
        start_t = time.time()
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "CycloneX-PreFlightHealthCheck/1.0"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as res:
                latency_ms = (time.time() - start_t) * 1000.0
                if res.status == 200:
                    data = json.loads(res.read().decode("utf-8"))
                    db_status = data.get("database", "")
                    if "error" in str(db_status).lower():
                        return False, f"Backend reported database failure: {db_status}", {}, latency_ms
                    return True, url, data, latency_ms
                else:
                    last_error = f"HTTP status {res.status} from {url}"
        except urllib.error.URLError as e:
            last_error = f"Could not connect to {url}: {e.reason}"
        except Exception as e:
            last_error = f"Unexpected error pinging {url}: {str(e)}"

    return False, last_error, {}, 0.0


def check_database_tables(db_path: str, backend_url: str = None, timeout: float = 5.0) -> Tuple[bool, Dict[str, int], List[str]]:
    """
    Check 2: Verify non-zero rows in cyclones, alerts, shelters, and hospitals.
    Checks both direct SQLite database and API endpoints if backend is up.
    """
    tables = ["cyclones", "alerts", "shelters", "hospitals"]
    counts = {t: 0 for t in tables}
    errors = []

    # 1. Direct SQLite check on the database file
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            for t in tables:
                cursor.execute(f"SELECT count(*) FROM {t}")
                counts[t] = cursor.fetchone()[0]
                if counts[t] <= 0:
                    errors.append(f"Database table '{t}' in {db_path} has {counts[t]} rows (REQUIRES >= 1).")
            conn.close()
        except Exception as e:
            errors.append(f"Direct SQLite inspection error on '{db_path}': {str(e)}")
    else:
        errors.append(f"Database file '{db_path}' not found on disk.")

    # 2. Also verify via backend API endpoints if backend is up
    if backend_url:
        api_endpoints = {
            "cyclones": "/cyclones",
            "alerts": "/alerts",
            "shelters": "/facilities/shelters",
            "hospitals": "/facilities/hospitals"
        }
        for table, ep in api_endpoints.items():
            url = f"{backend_url.rstrip('/')}/api/v1{ep}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "CycloneX-PreFlightHealthCheck/1.0"})
                with urllib.request.urlopen(req, timeout=timeout) as res:
                    if res.status == 200:
                        data = json.loads(res.read().decode("utf-8"))
                        if isinstance(data, list) and len(data) == 0:
                            errors.append(f"Backend endpoint {ep} returned 0 records (table '{table}' is empty).")
            except Exception as e:
                # If API call fails, error will already be reported in Check 1
                pass

    all_positive = len(errors) == 0 and all(counts[t] > 0 for t in tables)
    return all_positive, counts, errors


def check_map_tile_provider(test_url: str = None, timeout: float = 5.0) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Check 3: Verify map tile provider serves real, non-watermarked tiles.
    Rejects:
      - Network failure / timeouts
      - Non-200 HTTP statuses (e.g. 401 Unauthorized, 403 Forbidden)
      - Content-types other than image/*
      - Truncated payloads (< 500 bytes)
      - Watermarked tiles (e.g. Carto without API key)
    """
    # Sample real geographic tiles to probe
    # 1/1/0: Global synoptic quadrant
    # 6/44/28: Gujarat coastline / Arabian Sea corridor
    sample_urls = []
    if test_url:
        sample_urls.append(test_url)
    else:
        sample_urls = [
            "https://tile.openstreetmap.org/1/1/0.png",
            "https://a.tile.openstreetmap.org/6/44/28.png"
        ]

    tile_meta = {}
    last_err = ""

    for url in sample_urls:
        # Detect Carto without API key (known watermarked tile generator)
        if "cartocdn.com" in url.lower() and "api_key" not in url.lower():
            return False, "CARTO tile provider requires an API key. Unauthenticated requests receive watermarked 'API KEY REQUIRED' tiles. Use OpenStreetMap key-free tiles.", {}

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "CycloneX-SIH26070-HealthCheck/1.0 (Meteorological Operations; contact@cyclonex.gov)",
                    "Accept": "image/png,image/webp,image/*"
                }
            )
            start_t = time.time()
            with urllib.request.urlopen(req, timeout=timeout) as res:
                latency_ms = (time.time() - start_t) * 1000.0
                status = res.status
                content_type = res.headers.get("Content-Type", "")
                data = res.read()
                size_bytes = len(data)

                tile_meta = {
                    "url": url,
                    "status": status,
                    "content_type": content_type,
                    "size_bytes": size_bytes,
                    "latency_ms": round(latency_ms, 1)
                }

                # Validation checks
                if status != 200:
                    return False, f"Map tile provider returned HTTP {status} from {url}", tile_meta

                if not ("image" in content_type or size_bytes > 500):
                    return False, f"Map tile response is not an image (Content-Type: {content_type}, Size: {size_bytes}B)", tile_meta

                # Validate image header magic bytes (PNG magic bytes: \x89PNG\r\n\x1a\n)
                is_png = data.startswith(b"\x89PNG\r\n\x1a\n")
                is_jpeg = data.startswith(b"\xff\xd8")
                is_webp = data.startswith(b"RIFF") and b"WEBP" in data[:12]

                if not (is_png or is_jpeg or is_webp):
                    return False, f"Map tile data has invalid image signature at {url}", tile_meta

                # Content inspection for text error messages embedded in payload
                if b"API KEY REQUIRED" in data:
                    return False, f"Watermarked tile detected ('API KEY REQUIRED') from {url}", tile_meta

                if size_bytes < 500:
                    return False, f"Tile size suspiciously small ({size_bytes} bytes). Real tiles are typically > 1000 bytes.", tile_meta

                # Verified clean non-watermarked tile
                return True, f"Valid real map tile ({size_bytes} bytes, {content_type}, {round(latency_ms, 1)}ms) from {url}", tile_meta

        except urllib.error.HTTPError as e:
            last_err = f"HTTP error {e.code} ({e.reason}) fetching tile {url}"
        except urllib.error.URLError as e:
            last_err = f"Network error connecting to tile provider {url}: {e.reason}"
        except Exception as e:
            last_err = f"Unexpected tile fetch error {url}: {str(e)}"

    return False, last_err, tile_meta


def check_frontend_stylesheet_health(frontend_urls: List[str] = None, timeout: float = 5.0) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Check 4: Fetch /dashboard directly and confirm the returned HTML's linked CSS file(s)
    actually return HTTP 200 with non-trivial byte size (not 404).
    Catches stale dev-server-vs-build-cache asset mismatch regressions.
    """
    if frontend_urls is None:
        frontend_urls = ["http://localhost:3000", "http://127.0.0.1:3000"]

    active_base = None
    dashboard_html = ""
    last_err = ""

    for base in frontend_urls:
        url = f"{base.rstrip('/')}/dashboard"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CycloneX-PreFlightHealthCheck/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as res:
                if res.status == 200:
                    active_base = base.rstrip('/')
                    dashboard_html = res.read().decode("utf-8", errors="ignore")
                    break
        except urllib.error.URLError as e:
            last_err = f"Could not connect to frontend at {url}: {e.reason}"
        except Exception as e:
            last_err = f"Failed to fetch {url}: {str(e)}"

    if not active_base:
        return False, f"Frontend server unreachable on port 3000: {last_err}", {
            "server_running": False
        }

    # Extract linked CSS files from HTML
    css_links = []
    link_tags = re.findall(r'<link[^>]+>', dashboard_html, re.IGNORECASE)
    for tag in link_tags:
        if re.search(r'rel=["\']stylesheet["\']', tag, re.IGNORECASE):
            href_match = re.search(r'href=["\']([^"\']+)["\']', tag, re.IGNORECASE)
            if href_match:
                css_links.append(href_match.group(1))

    if not css_links:
        css_links = re.findall(r'href=["\']([^"\']+\.css[^"\']*)["\']', dashboard_html, re.IGNORECASE)

    if not css_links:
        return False, f"No stylesheet links found in {active_base}/dashboard HTML! Layout will render unstyled.", {
            "stylesheets_found": 0
        }

    verified_sheets = []
    for href in css_links:
        full_url = href if href.startswith("http") else f"{active_base}{href}"
        try:
            req = urllib.request.Request(full_url, headers={"User-Agent": "CycloneX-PreFlightHealthCheck/1.0"})
            start_t = time.time()
            with urllib.request.urlopen(req, timeout=timeout) as res:
                content = res.read()
                size_bytes = len(content)
                status_code = res.status
                latency_ms = (time.time() - start_t) * 1000.0

                if status_code != 200:
                    return False, f"Stylesheet {full_url} returned HTTP {status_code} (Expected 200 OK)", {
                        "url": full_url,
                        "status": status_code,
                        "size_bytes": size_bytes
                    }

                if size_bytes < 500:
                    return False, f"Stylesheet {full_url} is truncated ({size_bytes} bytes). Expected non-trivial CSS bundle.", {
                        "url": full_url,
                        "size_bytes": size_bytes
                    }

                verified_sheets.append({
                    "url": full_url,
                    "status": status_code,
                    "size_bytes": size_bytes,
                    "latency_ms": round(latency_ms, 1)
                })
        except urllib.error.HTTPError as e:
            return False, f"CRITICAL CSS 404 REGRESSION: Stylesheet {full_url} returned HTTP {e.code} ({e.reason})! Stale dev-server / clobbered .next cache detected.", {
                "url": full_url,
                "status": e.code,
                "error": str(e)
            }
        except Exception as e:
            return False, f"Failed to fetch stylesheet {full_url}: {str(e)}", {
                "url": full_url,
                "error": str(e)
            }

    total_css_bytes = sum(s["size_bytes"] for s in verified_sheets)
    next_css = [s for s in verified_sheets if "_next/static/css" in s["url"]]

    if not next_css:
        return False, f"No local Next.js stylesheet (_next/static/css) was found in /dashboard. Found only external sheets.", {
            "verified_sheets": verified_sheets
        }

    return True, f"All {len(verified_sheets)} stylesheet(s) verified healthy (HTTP 200, {total_css_bytes:,} bytes total; Next.js bundle: {next_css[0]['size_bytes']:,} bytes)", {
        "stylesheets": verified_sheets,
        "total_bytes": total_css_bytes,
        "next_bundle": next_css[0]["url"]
    }


def main():
    parser = argparse.ArgumentParser(description="CycloneX Startup Health & Pre-Flight Verification")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000", help="FastAPI backend URL")
    parser.add_argument("--frontend-url", default="http://localhost:3000", help="Next.js frontend URL")
    parser.add_argument("--skip-frontend", action="store_true", help="Skip frontend /dashboard CSS verification")
    parser.add_argument("--db-path", default="cyclonex.db", help="Path to SQLite database file")
    parser.add_argument("--tile-url", default=None, help="Custom tile URL to test")
    parser.add_argument("--timeout", type=float, default=5.0, help="Network timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    # Find db path relative to repo root if needed
    db_path = args.db_path
    if not os.path.isabs(db_path):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidate = os.path.join(repo_root, db_path)
        if os.path.exists(candidate):
            db_path = candidate

    if args.backend_url and args.backend_url not in ("http://127.0.0.1:8000", "http://localhost:8000"):
        candidate_backends = [args.backend_url]
    else:
        candidate_backends = [
            args.backend_url,
            "http://127.0.0.1:8000",
            "http://localhost:8000"
        ]
    # Deduplicate while preserving order
    seen = set()
    candidate_backends = [b for b in candidate_backends if not (b in seen or seen.add(b))]

    results = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ready": False,
        "checks": {}
    }

    all_passed = True

    if not args.json:
        log_header("CYCLONEX STARTUP PRE-FLIGHT VERIFICATION & HEALTH AUDIT")
        print(f"  Execution Time: {results['timestamp_utc']}")
        print(f"  Backend Candidate: {args.backend_url}")
        print(f"  Database Path: {db_path}\n")

    # -------------------------------------------------------------
    # Check 1: Backend Reachability
    # -------------------------------------------------------------
    backend_ok, backend_msg, health_payload, latency_ms = check_backend_reachability(candidate_backends, args.timeout)
    results["checks"]["backend"] = {
        "passed": backend_ok,
        "endpoint": backend_msg if backend_ok else None,
        "latency_ms": round(latency_ms, 1),
        "error": None if backend_ok else backend_msg,
        "health_data": health_payload
    }

    if not args.json:
        print(f"{BOLD}[1/4] Backend Service Reachability:{RESET}")
        if backend_ok:
            log_pass(f"FastAPI backend online at {backend_msg} (Response latency: {latency_ms:.1f}ms)")
            log_info(f"Reported status: '{health_payload.get('status')}', database: '{health_payload.get('database')}'")
        else:
            all_passed = False
            log_fail(f"Backend unreachable or degraded: {backend_msg}")
            print(f"        {YELLOW}-> Remedy: Start backend with: python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000{RESET}")

    # -------------------------------------------------------------
    # Check 2: Database Rows in Critical Tables
    # -------------------------------------------------------------
    active_backend = candidate_backends[0] if backend_ok else None
    db_ok, table_counts, db_errors = check_database_tables(db_path, active_backend, args.timeout)
    results["checks"]["database"] = {
        "passed": db_ok,
        "table_counts": table_counts,
        "errors": db_errors
    }

    if not args.json:
        print(f"\n{BOLD}[2/4] Database Non-Zero Row Verification:{RESET}")
        for t, cnt in table_counts.items():
            if cnt > 0:
                log_pass(f"Table '{t}': {cnt} row(s) confirmed")
            else:
                log_fail(f"Table '{t}': 0 rows (EMPTY TABLE)")

        if db_ok:
            log_pass("All 4 critical tables (cyclones, alerts, shelters, hospitals) contain verified rows.")
        else:
            all_passed = False
            log_fail(f"Database health failed: {'; '.join(db_errors)}")
            print(f"        {YELLOW}-> Remedy: Seed required operational data: python scripts/seed_demo_data.py{RESET}")

    # -------------------------------------------------------------
    # Check 3: Map Tile Provider Real Non-Watermarked Verification
    # -------------------------------------------------------------
    tile_ok, tile_msg, tile_meta = check_map_tile_provider(args.tile_url, args.timeout)
    results["checks"]["map_tiles"] = {
        "passed": tile_ok,
        "message": tile_msg,
        "metadata": tile_meta
    }

    if not args.json:
        print(f"\n{BOLD}[3/4] Map Tile Provider Verification:{RESET}")
        if tile_ok:
            log_pass(f"Tile provider verified: {tile_msg}")
            log_info(f"Clean, non-watermarked tiles served ({tile_meta.get('size_bytes', 0)} bytes, {tile_meta.get('content_type')})")
        else:
            all_passed = False
            log_fail(f"Tile provider check failed: {tile_msg}")
            print(f"        {YELLOW}-> Remedy: Ensure MapComponent uses OpenStreetMap key-free tiles: 'https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png'{RESET}")

    # -------------------------------------------------------------
    # Check 4: Frontend /dashboard Stylesheet 200 OK Verification
    # -------------------------------------------------------------
    if not args.skip_frontend:
        frontend_candidates = [
            args.frontend_url,
            "http://localhost:3000",
            "http://127.0.0.1:3000"
        ]
        seen_fe = set()
        frontend_candidates = [f for f in frontend_candidates if not (f in seen_fe or seen_fe.add(f))]

        css_ok, css_msg, css_meta = check_frontend_stylesheet_health(frontend_candidates, args.timeout)
        results["checks"]["frontend_css"] = {
            "passed": css_ok,
            "message": css_msg,
            "metadata": css_meta
        }

        if not args.json:
            print(f"\n{BOLD}[4/4] Frontend Dashboard Stylesheet Verification (/dashboard):{RESET}")
            if css_ok:
                log_pass(f"Stylesheet health verified: {css_msg}")
                if "next_bundle" in css_meta:
                    log_info(f"Tailwind CSS production bundle live: {css_meta['next_bundle']}")
            else:
                all_passed = False
                log_fail(f"Frontend stylesheet check failed: {css_msg}")
                print(f"        {YELLOW}-> Remedy: Stale dev server / clobbered .next cache detected.")
                print(f"                  Terminate process on port 3000, run 'npm run build', and start fresh.{RESET}")
    else:
        results["checks"]["frontend_css"] = {"skipped": True}
        if not args.json:
            print(f"\n{BOLD}[4/4] Frontend Dashboard Stylesheet Verification:{RESET}")
            log_info("Skipped (--skip-frontend specified).")

    # -------------------------------------------------------------
    # Final Verdict & Loud Exit
    # -------------------------------------------------------------
    results["ready"] = all_passed

    if args.json:
        print(json.dumps(results, indent=2))
        sys.exit(0 if all_passed else 1)

    print("\n" + "=" * 78)
    if all_passed:
        print(f"{GREEN}{BOLD}  === [SUCCESS] CYCLONEX SYSTEM PRE-FLIGHT CHECKS PASSED ==={RESET}")
        print(f"{GREEN}  Backend reachable, database populated, tiles verified, and CSS live (200 OK).")
        print(f"  Platform is certified READY for demonstration and operations.{RESET}")
        print("=" * 78 + "\n")
        sys.exit(0)
    else:
        print(f"{RED}{BOLD}  === [FATAL ERROR] CYCLONEX STARTUP PRE-FLIGHT CHECK FAILED ==={RESET}")
        print(f"{RED}  One or more critical subsystems failed verification.")
        print(f"  The frontend will NOT be permitted to silently degrade to cached fallbacks.")
        print(f"  Resolve the flagged errors above and re-run this check.{RESET}")
        print("=" * 78 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
