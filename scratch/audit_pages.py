import urllib.request
import json
import re

PAGES = [
    "/dashboard",
    "/forecast",
    "/risk",
    "/evacuation",
    "/cyclones",
    "/historical",
    "/alerts"
]

print("=" * 80)
print("CYCLONEX COLD-START 7-PAGE INTEGRATION & CONTENT AUDIT")
print("=" * 80)

for page in PAGES:
    url = f"http://localhost:3000{page}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CycloneXAudit/1.0"})
        with urllib.request.urlopen(req, timeout=5) as res:
            status = res.status
            html = res.read().decode("utf-8")
            
            # Check CSS links
            css_links = re.findall(r'<link[^>]+rel=["\']stylesheet["\'][^>]*>', html, re.IGNORECASE)
            has_tailwind_bundle = any("_next/static/css" in l for l in css_links)
            
            # Check for fallback warning / cached badges
            has_offline_badge = "OFFLINE / USING CACHED DATA" in html
            has_error_message = "Error loading" in html or "Failed to fetch" in html
            
            # Extract title and headings
            title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
            title = title_match.group(1) if title_match else "N/A"
            
            h1_matches = re.findall(r'<h[1-2][^>]*>([^<]+)</h[1-2]>', html, re.IGNORECASE)
            h1_clean = [h.strip() for h in h1_matches if h.strip()][:3]
            
            print(f"\n[PAGE: {page}]")
            print(f"  HTTP Status: {status}")
            print(f"  Title: {title}")
            print(f"  Stylesheets: {len(css_links)} linked (Next.js Tailwind bundle present: {has_tailwind_bundle})")
            print(f"  Offline/Cached Badge in HTML: {has_offline_badge}")
            print(f"  Headings: {', '.join(h1_clean)}")
            print(f"  HTML Size: {len(html):,} bytes")
    except Exception as e:
        print(f"\n[PAGE: {page}] ERROR: {str(e)}")

print("\n" + "=" * 80)
print("BACKEND REAL DATA SNAPSHOT")
print("=" * 80)

API_ENDPOINTS = [
    ("/cyclones", "Cyclones List"),
    ("/alerts", "Active Alerts"),
    ("/facilities/shelters", "Shelters"),
    ("/facilities/hospitals", "Hospitals"),
    ("/historical/analogs?lat=21.65&lon=66.85&wind_speed_kts=85.0", "Historical Analogs"),
]

for ep, desc in API_ENDPOINTS:
    url = f"http://127.0.0.1:8000/api/v1{ep}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CycloneXAudit/1.0"})
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode("utf-8"))
            if isinstance(data, list):
                count = len(data)
                sample = data[0].get("name", data[0].get("title", data[0].get("id", "item"))) if count > 0 else "N/A"
                print(f"  {desc} ({ep}): {count} records | First: {sample}")
            elif isinstance(data, dict):
                items = data.get("analogs", data.get("items", []))
                print(f"  {desc} ({ep}): {len(items)} items")
    except Exception as e:
        print(f"  {desc} ({ep}): ERROR: {str(e)}")
