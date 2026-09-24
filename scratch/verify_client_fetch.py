import urllib.request
import json

base = "http://127.0.0.1:8000/api/v1"

def check(name, url):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
            count = len(data) if isinstance(data, list) else (len(data.get("analogs", [])) if "analogs" in data else 1)
            print(f"[OK] {name}: {count} items returned (HTTP {r.status})")
            return True
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        return False

print("Auditing API calls made by the 7 frontend pages:")
check("/dashboard & /cyclones -> /cyclones", f"{base}/cyclones")
check("/dashboard -> /cyclones/demo-biparjoy-2023", f"{base}/cyclones/demo-biparjoy-2023")
check("/dashboard & /forecast -> /forecast", f"{base}/cyclones/demo-biparjoy-2023/forecast")
check("/dashboard & /risk -> /risk", f"{base}/cyclones/demo-biparjoy-2023/risk")
check("/dashboard & /evacuation -> /shelters", f"{base}/facilities/shelters")
check("/dashboard & /evacuation -> /hospitals", f"{base}/facilities/hospitals")
check("/dashboard & /alerts -> /alerts", f"{base}/alerts")
check("/historical -> /historical/analogs", f"{base}/historical/analogs?lat=21.65&lon=66.85&wind_speed_kts=85.0")
