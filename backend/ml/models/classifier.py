"""
Cyclone Classification Engine
Maps sustained wind speeds and pressure to authoritative IMD (India Meteorological Department)
and Saffir-Simpson Hurricane Wind Scale categories.
"""
from typing import Dict, Any

class CycloneClassifier:
    """
    Standard IMD Classification for North Indian Ocean (BoB & Arabian Sea):
    - Low Pressure Area: < 17 kts
    - Depression (D): 17 - 27 kts (31 - 49 km/h)
    - Deep Depression (DD): 28 - 33 kts (50 - 61 km/h)
    - Cyclonic Storm (CS): 34 - 47 kts (62 - 88 km/h)
    - Severe Cyclonic Storm (SCS): 48 - 63 kts (89 - 117 km/h)
    - Very Severe Cyclonic Storm (VSCS): 64 - 89 kts (118 - 165 km/h)
    - Extremely Severe Cyclonic Storm (ESCS): 90 - 119 kts (166 - 220 km/h)
    - Super Cyclonic Storm (SuCS): >= 120 kts (>= 221 km/h)
    """

    @staticmethod
    def classify_imd(wind_speed_kts: float) -> Dict[str, Any]:
        if wind_speed_kts < 17:
            code = "LPA"
            label = "Low Pressure Area"
            color = "#64748b" # slate
            severity_rank = 0
        elif 17 <= wind_speed_kts <= 27:
            code = "D"
            label = "Depression"
            color = "#38bdf8" # light blue
            severity_rank = 1
        elif 28 <= wind_speed_kts <= 33:
            code = "DD"
            label = "Deep Depression"
            color = "#0284c7" # blue
            severity_rank = 2
        elif 34 <= wind_speed_kts <= 47:
            code = "CS"
            label = "Cyclonic Storm"
            color = "#22c55e" # green
            severity_rank = 3
        elif 48 <= wind_speed_kts <= 63:
            code = "SCS"
            label = "Severe Cyclonic Storm"
            color = "#eab308" # yellow
            severity_rank = 4
        elif 64 <= wind_speed_kts <= 89:
            code = "VSCS"
            label = "Very Severe Cyclonic Storm"
            color = "#f97316" # orange
            severity_rank = 5
        elif 90 <= wind_speed_kts <= 119:
            code = "ESCS"
            label = "Extremely Severe Cyclonic Storm"
            color = "#ef4444" # red
            severity_rank = 6
        else:
            code = "SuCS"
            label = "Super Cyclonic Storm"
            color = "#a855f7" # purple
            severity_rank = 7

        saffir_simpson = "Tropical Storm"
        if wind_speed_kts < 34:
            saffir_simpson = "Tropical Depression"
        elif 34 <= wind_speed_kts < 64:
            saffir_simpson = "Tropical Storm"
        elif 64 <= wind_speed_kts < 83:
            saffir_simpson = "Category 1 Hurricane"
        elif 83 <= wind_speed_kts < 96:
            saffir_simpson = "Category 2 Hurricane"
        elif 96 <= wind_speed_kts < 113:
            saffir_simpson = "Category 3 Major Hurricane"
        elif 113 <= wind_speed_kts < 137:
            saffir_simpson = "Category 4 Major Hurricane"
        else:
            saffir_simpson = "Category 5 Major Hurricane"

        return {
            "imd_code": code,
            "imd_label": label,
            "color": color,
            "severity_rank": severity_rank,
            "saffir_simpson": saffir_simpson,
            "wind_speed_kts": wind_speed_kts,
            "wind_speed_kmh": round(wind_speed_kts * 1.852, 1)
        }

