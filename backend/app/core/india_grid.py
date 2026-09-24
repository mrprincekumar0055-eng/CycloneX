"""
CycloneX India Meteorological Grid & Disturbance Index
Defines 44 representative synoptic observation stations across India's
cyclone-exposed coastline (Arabian Sea & Bay of Bengal), island territories,
and strategic interior nodes.
"""
from typing import Dict, Any, List, Optional

# 44 Representative Grid Coordinates spanning India
INDIA_GRID_POINTS: List[Dict[str, Any]] = [
    # -------------------------------------------------------------
    # 1. GUJARAT & NORTH ARABIAN SEA (High Cyclone Impact Belt)
    # -------------------------------------------------------------
    {"id": "in-jak", "name": "Jakhau Port", "district": "Kutch", "state": "Gujarat", "region": "Northwest Coast", "lat": 23.24, "lon": 68.62, "coastal": True},
    {"id": "in-man", "name": "Mandvi Coastal Sector", "district": "Kutch", "state": "Gujarat", "region": "Northwest Coast", "lat": 22.83, "lon": 69.36, "coastal": True},
    {"id": "in-dwa", "name": "Dwarka", "district": "Devbhumi Dwarka", "state": "Gujarat", "region": "Saurashtra Coast", "lat": 22.24, "lon": 68.97, "coastal": True},
    {"id": "in-por", "name": "Porbandar Port", "district": "Porbandar", "state": "Gujarat", "region": "Saurashtra Coast", "lat": 21.64, "lon": 69.60, "coastal": True},
    {"id": "in-ver", "name": "Veraval / Somnath", "district": "Gir Somnath", "state": "Gujarat", "region": "Saurashtra Coast", "lat": 20.90, "lon": 70.37, "coastal": True},
    {"id": "in-bip", "name": "Biparjoy Anchor Point (Offshore)", "district": "Arabian Sea", "state": "Offshore", "region": "Northeast Arabian Sea", "lat": 21.65, "lon": 66.85, "coastal": True},
    {"id": "in-sur", "name": "Hazira / Surat Port", "district": "Surat", "state": "Gujarat", "region": "Gulf of Khambhat", "lat": 21.17, "lon": 72.83, "coastal": True},

    # -------------------------------------------------------------
    # 2. MAHARASHTRA & GOA (Konkan Coast)
    # -------------------------------------------------------------
    {"id": "in-mum", "name": "Mumbai Harbour", "district": "Mumbai", "state": "Maharashtra", "region": "Konkan Coast", "lat": 18.92, "lon": 72.83, "coastal": True},
    {"id": "in-ali", "name": "Alibag Coastal Sector", "district": "Raigad", "state": "Maharashtra", "region": "Konkan Coast", "lat": 18.64, "lon": 72.87, "coastal": True},
    {"id": "in-rat", "name": "Ratnagiri Port", "district": "Ratnagiri", "state": "Maharashtra", "region": "Konkan Coast", "lat": 16.99, "lon": 73.30, "coastal": True},
    {"id": "in-mor", "name": "Mormugao / Panaji", "district": "South Goa", "state": "Goa", "region": "Konkan Coast", "lat": 15.40, "lon": 73.80, "coastal": True},

    # -------------------------------------------------------------
    # 3. KARNATAKA & KERALA (Malabar Coast)
    # -------------------------------------------------------------
    {"id": "in-kar", "name": "Karwar Naval Base", "district": "Uttara Kannada", "state": "Karnataka", "region": "Canara Coast", "lat": 14.80, "lon": 74.13, "coastal": True},
    {"id": "in-man-k", "name": "Mangaluru Major Port", "district": "Dakshina Kannada", "state": "Karnataka", "region": "Canara Coast", "lat": 12.91, "lon": 74.85, "coastal": True},
    {"id": "in-koz", "name": "Kozhikode Malabar", "district": "Kozhikode", "state": "Kerala", "region": "Malabar Coast", "lat": 11.25, "lon": 75.78, "coastal": True},
    {"id": "in-koc", "name": "Kochi Major Port", "district": "Ernakulam", "state": "Kerala", "region": "Malabar Coast", "lat": 9.93, "lon": 76.26, "coastal": True},
    {"id": "in-tvm", "name": "Thiruvananthapuram / Vizhinjam", "district": "Thiruvananthapuram", "state": "Kerala", "region": "Malabar Coast", "lat": 8.52, "lon": 76.93, "coastal": True},
    {"id": "in-kan", "name": "Kanyakumari / Cape Comorin", "district": "Kanyakumari", "state": "Tamil Nadu", "region": "Southern Cape", "lat": 8.08, "lon": 77.55, "coastal": True},

    # -------------------------------------------------------------
    # 4. TAMIL NADU & PUDUCHERRY (Coromandel Coast)
    # -------------------------------------------------------------
    {"id": "in-ram", "name": "Rameswaram / Pamban Island", "district": "Ramanathapuram", "state": "Tamil Nadu", "region": "Gulf of Mannar", "lat": 9.28, "lon": 79.31, "coastal": True},
    {"id": "in-nag", "name": "Nagapattinam Coast", "district": "Nagapattinam", "state": "Tamil Nadu", "region": "Coromandel Coast", "lat": 10.76, "lon": 79.84, "coastal": True},
    {"id": "in-pud", "name": "Puducherry Coast", "district": "Puducherry", "state": "Puducherry", "region": "Coromandel Coast", "lat": 11.94, "lon": 79.83, "coastal": True},
    {"id": "in-che", "name": "Chennai Port", "district": "Chennai", "state": "Tamil Nadu", "region": "Coromandel Coast", "lat": 13.08, "lon": 80.27, "coastal": True},

    # -------------------------------------------------------------
    # 5. ANDHRA PRADESH (Cyclone Vulnerability Hotspot)
    # -------------------------------------------------------------
    {"id": "in-nel", "name": "Krishnapatnam Port", "district": "Nellore", "state": "Andhra Pradesh", "region": "Andhra Coast", "lat": 14.25, "lon": 80.12, "coastal": True},
    {"id": "in-mac", "name": "Machilipatnam / Krishna Delta", "district": "Krishna", "state": "Andhra Pradesh", "region": "Andhra Coast", "lat": 16.18, "lon": 81.13, "coastal": True},
    {"id": "in-kak", "name": "Kakinada Deepwater Port", "district": "Kakinada", "state": "Andhra Pradesh", "region": "Godavari Delta", "lat": 16.98, "lon": 82.24, "coastal": True},
    {"id": "in-viz", "name": "Visakhapatnam Port", "district": "Visakhapatnam", "state": "Andhra Pradesh", "region": "Andhra Coast", "lat": 17.68, "lon": 83.21, "coastal": True},

    # -------------------------------------------------------------
    # 6. ODISHA (High Frequency Cyclone Ingress Corridor)
    # -------------------------------------------------------------
    {"id": "in-gop", "name": "Gopalpur Port", "district": "Ganjam", "state": "Odisha", "region": "Odisha Coast", "lat": 19.26, "lon": 84.91, "coastal": True},
    {"id": "in-pur", "name": "Puri Coastline", "district": "Puri", "state": "Odisha", "region": "Odisha Coast", "lat": 19.81, "lon": 85.83, "coastal": True},
    {"id": "in-par", "name": "Paradip Major Port", "district": "Jagatsinghpur", "state": "Odisha", "region": "Odisha Coast", "lat": 20.31, "lon": 86.61, "coastal": True},
    {"id": "in-dha", "name": "Dhamra Port / Bhitarkanika", "district": "Bhadrak", "state": "Odisha", "region": "Odisha Coast", "lat": 20.78, "lon": 86.74, "coastal": True},
    {"id": "in-bal", "name": "Balasore / Chandipur", "district": "Balasore", "state": "Odisha", "region": "North Odisha Coast", "lat": 21.49, "lon": 86.93, "coastal": True},

    # -------------------------------------------------------------
    # 7. WEST BENGAL & SUNDARBANS
    # -------------------------------------------------------------
    {"id": "in-dig", "name": "Digha Coastal Sector", "district": "Purba Medinipur", "state": "West Bengal", "region": "Bengal Coast", "lat": 21.62, "lon": 87.51, "coastal": True},
    {"id": "in-sag", "name": "Sagar Island / Sundarbans", "district": "South 24 Parganas", "state": "West Bengal", "region": "Ganges Delta", "lat": 21.65, "lon": 88.08, "coastal": True},
    {"id": "in-hal", "name": "Haldia Industrial Port", "district": "Purba Medinipur", "state": "West Bengal", "region": "Hooghly Estuary", "lat": 22.06, "lon": 88.06, "coastal": True},
    {"id": "in-kol", "name": "Kolkata Metropolitan", "district": "Kolkata", "state": "West Bengal", "region": "Lower Bengal Basin", "lat": 22.57, "lon": 88.36, "coastal": False},

    # -------------------------------------------------------------
    # 8. ISLAND TERRITORIES (Early Maritime Warning Nodes)
    # -------------------------------------------------------------
    {"id": "in-pbl", "name": "Port Blair", "district": "South Andaman", "state": "Andaman & Nicobar", "region": "Bay of Bengal Offshore", "lat": 11.62, "lon": 92.72, "coastal": True},
    {"id": "in-kav", "name": "Kavaratti", "district": "Lakshadweep", "state": "Lakshadweep", "region": "Arabian Sea Offshore", "lat": 10.57, "lon": 72.64, "coastal": True},

    # -------------------------------------------------------------
    # 9. INLAND & REGIONAL REFERENCE ANCHORS
    # -------------------------------------------------------------
    {"id": "in-del", "name": "New Delhi / NCR", "district": "New Delhi", "state": "Delhi", "region": "Northern Plains", "lat": 28.61, "lon": 77.20, "coastal": False},
    {"id": "in-ahm", "name": "Ahmedabad", "district": "Ahmedabad", "state": "Gujarat", "region": "Western Interior", "lat": 23.02, "lon": 72.57, "coastal": False},
    {"id": "in-hyd", "name": "Hyderabad", "district": "Hyderabad", "state": "Telangana", "region": "Deccan Plateau", "lat": 17.38, "lon": 78.48, "coastal": False},
    {"id": "in-blr", "name": "Bengaluru", "district": "Bengaluru Urban", "state": "Karnataka", "region": "Southern Interior", "lat": 12.97, "lon": 77.59, "coastal": False},
    {"id": "in-nag-p", "name": "Nagpur / Vidarbha", "district": "Nagpur", "state": "Maharashtra", "region": "Central India", "lat": 21.14, "lon": 79.08, "coastal": False},
    {"id": "in-pat", "name": "Patna", "district": "Patna", "state": "Bihar", "region": "Gangetic Basin", "lat": 25.59, "lon": 85.13, "coastal": False},
    {"id": "in-guw", "name": "Guwahati", "district": "Kamrup", "state": "Assam", "region": "Northeast Corridor", "lat": 26.14, "lon": 91.73, "coastal": False},
    {"id": "in-sri", "name": "Srinagar", "district": "Srinagar", "state": "Jammu & Kashmir", "region": "Himalayan North", "lat": 34.08, "lon": 74.79, "coastal": False}
]

def calculate_disturbance_score(
    wind_kts: Optional[float],
    gust_kts: Optional[float],
    pressure_hpa: Optional[float],
    precip_mm: Optional[float]
) -> Dict[str, Any]:
    """
    Computes a heuristic Meteorological Disturbance Index (MDI in [0, 100])
    combining:
      1. Normalized Wind & Gust Factor (45% weight)
         - 0.6 * sustained + 0.4 * gust normalized against 65 kts (Severe Cyclonic threshold).
      2. Inverse Normalized Sea-Level Pressure Deficit (35% weight)
         - Deficit relative to standard 1013.25 hPa normalized against 40 hPa drop.
      3. Precipitation Intensity Factor (20% weight)
         - Hourly rainfall normalized against 25 mm/h (Heavy Rainfall threshold).

    Formula:
      Score = 100 * (0.45 * W_norm + 0.35 * P_norm + 0.20 * R_norm)

    Returns:
      dict with:
        - score: float in [0.0, 100.0]
        - category: human-readable disturbance severity tier
        - components: breakdown of wind, pressure, and precipitation contributions
        - disclaimer: explicit label stating this is an empirical heuristic index
    """
    v_wind = float(wind_kts) if wind_kts is not None else 0.0
    v_gust = float(gust_kts) if gust_kts is not None else v_wind
    v_eff = 0.6 * v_wind + 0.4 * v_gust
    w_norm = min(1.0, max(0.0, v_eff / 65.0))

    slp = float(pressure_hpa) if pressure_hpa is not None else 1013.25
    deficit = max(0.0, 1013.25 - slp)
    p_norm = min(1.0, deficit / 40.0)

    rain = float(precip_mm) if precip_mm is not None else 0.0
    r_norm = min(1.0, max(0.0, rain / 25.0))

    raw_score = 100.0 * (0.45 * w_norm + 0.35 * p_norm + 0.20 * r_norm)
    score = round(min(100.0, max(0.0, raw_score)), 1)

    if score >= 75.0:
        category = "EXTREME DISTURBANCE"
        color = "red"
    elif score >= 55.0:
        category = "HIGH CYCLONIC DISTURBANCE"
        color = "amber"
    elif score >= 35.0:
        category = "MODERATE CONVECTIVE ACTIVITY"
        color = "yellow"
    elif score >= 20.0:
        category = "ELEVATED MONSOON / SQUALL"
        color = "blue"
    else:
        category = "QUIET / AMBIENT"
        color = "emerald"

    return {
        "disturbance_score": score,
        "category": category,
        "indicator_color": color,
        "components": {
            "wind_factor": round(w_norm, 3),
            "pressure_deficit_factor": round(p_norm, 3),
            "precipitation_factor": round(r_norm, 3)
        },
        "formula": "100 * (0.45 * W_norm + 0.35 * P_norm + 0.20 * R_norm)",
        "disclaimer": "Heuristic composite index combining live wind, pressure deficit, and rain. Decision-support guidance only; follow official IMD/SDMA bulletins."
    }

# Bounding box covering mainland India, Andaman & Nicobar, Lakshadweep, and immediate maritime EEZ
INDIA_LAT_MIN = 6.0
INDIA_LAT_MAX = 38.0
INDIA_LON_MIN = 68.0
INDIA_LON_MAX = 98.0

import math

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometers using the Haversine formula."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2.0)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(r * c, 1)

def is_valid_coordinate(lat: Any, lon: Any) -> bool:
    """Validates that latitude is in [-90, 90] and longitude in [-180, 180]."""
    try:
        f_lat = float(lat)
        f_lon = float(lon)
        return (-90.0 <= f_lat <= 90.0) and (-180.0 <= f_lon <= 180.0)
    except (ValueError, TypeError):
        return False

def is_in_india_region(lat: Any, lon: Any) -> bool:
    """Validates whether coordinates fall within India's monitoring and maritime domain."""
    try:
        f_lat = float(lat)
        f_lon = float(lon)
        return (INDIA_LAT_MIN <= f_lat <= INDIA_LAT_MAX) and (INDIA_LON_MIN <= f_lon <= INDIA_LON_MAX)
    except (ValueError, TypeError):
        return False

def find_nearest_station(lat: float, lon: float) -> Dict[str, Any]:
    """Finds the nearest cataloged synoptic station from INDIA_GRID_POINTS."""
    closest = None
    min_dist = float("inf")
    for pt in INDIA_GRID_POINTS:
        d = haversine_km(lat, lon, pt["lat"], pt["lon"])
        if d < min_dist:
            min_dist = d
            closest = dict(pt)
    if closest is not None:
        closest["distance_km"] = min_dist
        return closest
    return {"name": "Indian Observation Sector", "state": "India", "distance_km": 0.0}

