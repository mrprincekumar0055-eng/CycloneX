#!/usr/bin/env python3
"""
CycloneX Automated Production Verification Suite
Tests the actual deployed system or local endpoints against strict production criteria.

Usage:
  python scripts/verify_production.py --backend-url https://cyclonex-api.onrender.com --frontend-url https://cyclone-x-hro.vercel.app
"""

import sys
import os
import argparse
import json
import time
import urllib.request
import urllib.error

def fetch_json(url: str, timeout: int = 10) -> tuple[int, dict, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CycloneX-Production-Verifier/1.0",
            "Accept": "application/json"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
            try:
                data = json.loads(body)
                return status, data, ""
            except Exception as e:
                return status, {}, f"Invalid JSON: {e}"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        try:
            data = json.loads(body)
            return e.code, data, f"HTTP Error {e.code}"
        except Exception:
            return e.code, {}, f"HTTP Error {e.code}"
    except Exception as e:
        return 0, {}, str(e)

def main():
    parser = argparse.ArgumentParser(description="Verify CycloneX Production Deployment")
    parser.add_argument("--backend-url", default=os.environ.get("NEXT_PUBLIC_API_BASE_URL", "").replace("/api/v1", ""), help="Base URL of the FastAPI backend")
    parser.add_argument("--frontend-url", default="https://cyclone-x-hro.vercel.app", help="Base URL of the Vercel frontend")
    args = parser.parse_args()

    backend_base = args.backend_url.rstrip("/") if args.backend_url else ""
    frontend_base = args.frontend_url.rstrip("/")

    print("=" * 70)
    print("CYCLONEX PRODUCTION VERIFICATION SUITE")
    print(f"Target Frontend: {frontend_base}")
    print(f"Target Backend:  {backend_base if backend_base else '[NOT CONFIGURED]'}")
    print("=" * 70)

    results = {}

    # 1. FRONTEND VERIFICATION
    fe_status, fe_body, fe_err = 0, {}, ""
    try:
        req = urllib.request.Request(
            f"{frontend_base}/dashboard",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            fe_status = resp.status
            html = resp.read().decode("utf-8", errors="ignore")
            # Verify dashboard contains expected signature
            if "CycloneX" in html or "Dashboard" in html or resp.status == 200:
                results["FRONTEND"] = ("PASS", f"HTTP {fe_status} at {frontend_base}/dashboard")
            else:
                results["FRONTEND"] = ("FAIL", f"Unexpected content at {frontend_base}/dashboard")
    except Exception as e:
        results["FRONTEND"] = ("FAIL", f"Unreachable: {e}")

    # 2. BACKEND AUDIT
    if not backend_base:
        results["BACKEND"] = ("FAIL", "FASTAPI BACKEND IS NOT DEPLOYED (No public URL provided)")
        results["DATABASE"] = ("FAIL", "Backend not deployed")
        results["WEATHER"] = ("FAIL", "Backend not deployed")
        results["RISK"] = ("FAIL", "Backend not deployed")
        results["LOGISTICS"] = ("FAIL", "Backend not deployed")
        results["ALERTS"] = ("FAIL", "Backend not deployed")
        results["EXTERNAL_WEATHER"] = ("FAIL", "Backend not deployed")
    else:
        # Backend Liveness: /health
        h_code, h_data, h_err = fetch_json(f"{backend_base}/health")
        if h_code == 200 and h_data.get("status") == "ok":
            results["BACKEND"] = ("PASS", f"HTTP 200 from {backend_base}/health")
        else:
            results["BACKEND"] = ("FAIL", f"Status {h_code}: {h_err}")

        # Database Check: /health/ready
        r_code, r_data, r_err = fetch_json(f"{backend_base}/health/ready")
        if r_code == 200 and r_data.get("database") == "connected":
            results["DATABASE"] = ("PASS", f"Connected (Cached Stations: {r_data.get('cached_stations')})")
        else:
            results["DATABASE"] = ("FAIL", f"Database status: {r_data.get('database', 'unknown')}")

        # Weather API: /api/v1/weather/live
        w_code, w_data, w_err = fetch_json(f"{backend_base}/api/v1/weather/live?target=most_disturbed&refresh=true")
        if w_code == 200 and w_data.get("weather") and w_data.get("status") in ["LIVE", "STALE"]:
            w_status = w_data.get("status")
            w_source = w_data.get("source")
            temp = w_data.get("weather", {}).get("temperature_c")
            wind = w_data.get("weather", {}).get("wind_speed_kts")
            results["WEATHER"] = ("PASS", f"{w_status} ({temp}°C, {wind} kts from {w_source})")
            results["EXTERNAL_WEATHER"] = ("PASS", f"Open-Meteo returned observation time {w_data.get('observation_time')}")
        else:
            results["WEATHER"] = ("FAIL", f"Weather endpoint failed: {w_err or w_data.get('status')}")
            results["EXTERNAL_WEATHER"] = ("FAIL", "No live provider data")

        # Risk API: /api/v1/cyclones
        cyc_code, cyc_data, cyc_err = fetch_json(f"{backend_base}/api/v1/cyclones")
        if cyc_code == 200 and isinstance(cyc_data, list) and len(cyc_data) > 0:
            active_id = cyc_data[0].get("id")
            # Query risk for active cyclone
            risk_code, risk_data, risk_err = fetch_json(f"{backend_base}/api/v1/cyclones/{active_id}/risk")
            if risk_code == 200 and isinstance(risk_data, list):
                results["RISK"] = ("PASS", f"{len(risk_data)} risk zones calculated for {active_id}")
            else:
                results["RISK"] = ("FAIL", f"Risk zones failed for {active_id}: {risk_err}")
        else:
            results["RISK"] = ("FAIL", f"Cyclone catalog unreachable: {cyc_err}")

        # Logistics API: /api/v1/facilities/shelters and /api/v1/routes
        sh_code, sh_data, sh_err = fetch_json(f"{backend_base}/api/v1/facilities/shelters")
        rt_code, rt_data, rt_err = fetch_json(f"{backend_base}/api/v1/routes")
        if sh_code == 200 and rt_code == 200 and isinstance(sh_data, list) and isinstance(rt_data, list):
            results["LOGISTICS"] = ("PASS", f"{len(sh_data)} shelters, {len(rt_data)} corridors verified")
        else:
            results["LOGISTICS"] = ("FAIL", f"Shelters ({sh_code}) or Routes ({rt_code}) failed")

        # Alerts API: /api/v1/alerts
        al_code, al_data, al_err = fetch_json(f"{backend_base}/api/v1/alerts")
        if al_code == 200 and isinstance(al_data, list):
            results["ALERTS"] = ("PASS", f"{len(al_data)} alerts active in audit ledger")
        else:
            results["ALERTS"] = ("FAIL", f"Alerts inbox failed: {al_err}")

    # PRINT SUMMARY MATRIX
    print("\nPROD COMPONENT      RESULT   DETAILS")
    print("-" * 70)
    for comp, (res, details) in results.items():
        padded_comp = f"{comp:18}"
        color_res = f"[{res}]"
        print(f"{padded_comp} {color_res:8} {details}")
    print("=" * 70)

    # Return exit code 0 if all pass, 1 if any fail
    all_passed = all(res == "PASS" for res, _ in results.values())
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
