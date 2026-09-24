#!/usr/bin/env python3
"""
CycloneX Automated Production Verification Suite
Tests the actual deployed system against strict production criteria.

Usage:
  python scripts/verify_production.py --backend-url https://<your-backend>.onrender.com --frontend-url https://cyclone-x-hro.vercel.app
"""

import sys
import os
import argparse
import json
import re
import urllib.request
import urllib.error

def fetch_json(url: str, timeout: int = 15, headers: dict = None) -> tuple[int, dict, str, dict]:
    default_headers = {
        "User-Agent": "CycloneX-Production-Verifier/1.0",
        "Accept": "application/json"
    }
    if headers:
        default_headers.update(headers)
    req = urllib.request.Request(url, headers=default_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            resp_headers = dict(resp.headers)
            body = resp.read().decode("utf-8")
            try:
                data = json.loads(body)
                return status, data, "", resp_headers
            except Exception as e:
                return status, {}, f"Invalid JSON: {e}", resp_headers
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        resp_headers = dict(e.headers) if hasattr(e, "headers") else {}
        try:
            data = json.loads(body)
            return e.code, data, f"HTTP Error {e.code}", resp_headers
        except Exception:
            return e.code, {}, f"HTTP Error {e.code}", resp_headers
    except Exception as e:
        return 0, {}, str(e), {}

def check_no_localhost_references(repo_dir: str) -> bool:
    """Scans frontend src directory to ensure no production code calls localhost or 127.0.0.1 directly."""
    src_dir = os.path.join(repo_dir, "frontend", "src")
    if not os.path.exists(src_dir):
        return True
    
    # Allowed in api.ts as fallback during dev/isLocalhost checks only
    for root, _, files in os.walk(src_dir):
        for f in files:
            if f.endswith((".ts", ".tsx", ".js", ".jsx")) and f != "api.ts":
                fpath = os.path.join(root, f)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as file:
                    content = file.read()
                    if "http://localhost:8000" in content or "http://127.0.0.1:8000" in content:
                        return False
    return True

def main():
    parser = argparse.ArgumentParser(description="Verify CycloneX Production Deployment")
    parser.add_argument("--backend-url", default=os.environ.get("NEXT_PUBLIC_API_BASE_URL", "").replace("/api/v1", ""), help="Base URL of the FastAPI backend")
    parser.add_argument("--frontend-url", default="https://cyclone-x-hro.vercel.app", help="Base URL of the Vercel frontend")
    args = parser.parse_args()

    backend_base = args.backend_url.rstrip("/") if args.backend_url else ""
    frontend_base = args.frontend_url.rstrip("/")
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    print("=" * 70)
    print("CYCLONEX COMPREHENSIVE PRODUCTION VERIFICATION SUITE")
    print(f"Target Frontend: {frontend_base}")
    print(f"Target Backend:  {backend_base if backend_base else '[NOT CONFIGURED]'}")
    print("=" * 70)

    results = {}

    # 1. FRONTEND AVAILABILITY
    try:
        req = urllib.request.Request(
            f"{frontend_base}/dashboard",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            if resp.status == 200:
                results["FRONTEND"] = "PASS"
            else:
                results["FRONTEND"] = "FAIL"
    except Exception:
        results["FRONTEND"] = "FAIL"

    # 2. LOCALHOST REFERENCES
    no_lh = check_no_localhost_references(repo_root)
    results["LOCALHOST REFERENCES"] = "PASS" if no_lh else "FAIL"

    # BACKEND TESTS
    if not backend_base:
        results["BACKEND"] = "FAIL"
        results["DATABASE"] = "FAIL"
        results["WEATHER"] = "OFFLINE"
        results["CYCLONE API"] = "FAIL"
        results["ML FORECAST"] = "FAIL"
        results["RISK"] = "FAIL"
        results["EXPOSURE"] = "FAIL"
        results["SHELTERS"] = "FAIL"
        results["HOSPITALS"] = "FAIL"
        results["ROUTES"] = "FAIL"
        results["ALERTS"] = "FAIL"
        results["CORS"] = "FAIL"
    else:
        # Backend Liveness: /health
        h_code, h_data, _, _ = fetch_json(f"{backend_base}/health")
        results["BACKEND"] = "PASS" if (h_code == 200 and h_data.get("status") == "ok") else "FAIL"

        # Database Check: /health/ready
        r_code, r_data, _, _ = fetch_json(f"{backend_base}/health/ready")
        results["DATABASE"] = "PASS" if (r_code == 200 and r_data.get("database") == "connected") else "FAIL"

        # Weather: /api/v1/weather/live
        w_code, w_data, _, _ = fetch_json(f"{backend_base}/api/v1/weather/live?lat=19.076&lon=72.877&refresh=true")
        if w_code == 200 and w_data.get("status") in ["LIVE", "STALE"]:
            results["WEATHER"] = w_data.get("status")
        else:
            results["WEATHER"] = "OFFLINE"

        # Cyclone API: /api/v1/cyclones
        c_code, c_data, _, _ = fetch_json(f"{backend_base}/api/v1/cyclones")
        active_id = "demo-biparjoy-2023"
        if c_code == 200 and isinstance(c_data, list) and len(c_data) > 0:
            results["CYCLONE API"] = "PASS"
            active_id = c_data[0].get("id", active_id)
        else:
            results["CYCLONE API"] = "FAIL"

        # ML Forecast & Track: /api/v1/cyclones/{id}/forecast
        f_code, f_data, _, _ = fetch_json(f"{backend_base}/api/v1/cyclones/{active_id}/forecast")
        results["ML FORECAST"] = "PASS" if (f_code == 200 and isinstance(f_data, list)) else "FAIL"

        # Risk: /api/v1/cyclones/{id}/risk
        rk_code, rk_data, _, _ = fetch_json(f"{backend_base}/api/v1/cyclones/{active_id}/risk")
        results["RISK"] = "PASS" if (rk_code == 200 and isinstance(rk_data, list)) else "FAIL"

        # Exposure: /api/v1/cyclones/{id}/exposure
        ex_code, ex_data, _, _ = fetch_json(f"{backend_base}/api/v1/cyclones/{active_id}/exposure")
        results["EXPOSURE"] = "PASS" if (ex_code == 200 and isinstance(ex_data, dict)) else "FAIL"

        # Shelters: /api/v1/facilities/shelters
        sh_code, sh_data, _, _ = fetch_json(f"{backend_base}/api/v1/facilities/shelters")
        results["SHELTERS"] = "PASS" if (sh_code == 200 and isinstance(sh_data, list)) else "FAIL"

        # Hospitals: /api/v1/facilities/hospitals
        hp_code, hp_data, _, _ = fetch_json(f"{backend_base}/api/v1/facilities/hospitals")
        results["HOSPITALS"] = "PASS" if (hp_code == 200 and isinstance(hp_data, list)) else "FAIL"

        # Routes: /api/v1/routes
        rt_code, rt_data, _, _ = fetch_json(f"{backend_base}/api/v1/routes")
        results["ROUTES"] = "PASS" if (rt_code == 200 and isinstance(rt_data, list)) else "FAIL"

        # Alerts: /api/v1/alerts
        al_code, al_data, _, _ = fetch_json(f"{backend_base}/api/v1/alerts")
        results["ALERTS"] = "PASS" if (al_code == 200 and isinstance(al_data, list)) else "FAIL"

        # CORS: Check OPTIONS preflight with Origin header
        _, _, _, cors_headers = fetch_json(
            f"{backend_base}/health",
            headers={"Origin": "https://cyclone-x-hro.vercel.app"}
        )
        allowed_origin = cors_headers.get("access-control-allow-origin", "")
        results["CORS"] = "PASS" if ("cyclone-x-hro.vercel.app" in allowed_origin or allowed_origin == "*") else "FAIL"

    # PRINT STANDARDIZED OUTPUT
    print("\nFINAL PRODUCTION AUDIT REPORT:")
    print("-" * 40)
    for test in [
        "FRONTEND", "BACKEND", "DATABASE", "WEATHER", "CYCLONE API",
        "ML FORECAST", "RISK", "EXPOSURE", "SHELTERS", "HOSPITALS",
        "ROUTES", "ALERTS", "CORS", "LOCALHOST REFERENCES"
    ]:
        print(f"{test:<22}: {results.get(test, 'N/A')}")
    print("=" * 70)

if __name__ == "__main__":
    main()
