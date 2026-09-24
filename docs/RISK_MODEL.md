# CycloneX Quantitative Risk Engine Specification

**Document Version**: 2.0 (Forensic Standard)  
**System Classification**: Multi-Criteria Disaster Decision-Support Index  
**Statutory Boundary**: AI Decision Support Only (Not an official IMD Warning / Not a Hydrodynamic Simulation)  

---

## 1. Conceptual Framework & Purpose

The CycloneX Risk Engine implements a quantitative disaster risk formulation derived from the **United Nations Office for Disaster Risk Reduction (UNDRR)** conceptual model:
$$\text{Disaster Risk} = \text{Hazard} \times \text{Exposure} \times \text{Vulnerability} \times \text{Uncertainty Penalty}$$

### Operational Scope & Limitations
- **Decision-Support Tool**: Designed for rapid spatial triage, prioritizing emergency relief deployment, and ranking coastal taluks/districts by estimated impact severity.
- **Not a Hydrodynamic Surge Simulation**: The engine does **not** solve 2D/3D shallow-water Navier-Stokes equations (such as SLOSH, ADCIRC, or Delft3D). Coastal storm surge is approximated via an empirical proxy coupling maximum sustained wind speed and coastal elevation.
- **Non-Statutory**: Official red alerts, mandatory evacuation mandates, and cyclone landfall bulletins are issued exclusively by the **India Meteorological Department (IMD)** and **National/State Disaster Management Authorities (NDMA/SDMA)**.

---

## 2. Mathematical Formulations & Parameter Normalization

### 2.1 Hazard Score ($H \in [0.0, 1.0]$)
Captures the physical destructive potential of the cyclone at the evaluated location:
$$H = 0.45 \cdot V_{\text{norm}} + 0.35 \cdot P_{\text{norm}} + 0.20 \cdot S_{\text{proxy}}$$

Where:
- **Wind Normalization ($V_{\text{norm}}$)**:
  $$V_{\text{norm}} = \text{clip}\left(\frac{V_{\text{wind}}}{115.0}, 0.05, 1.0\right)$$
  Calibrated to IMD Extremely Severe Cyclonic Storm baseline (115 kts).
- **Pressure Deficit Normalization ($P_{\text{norm}}$)**:
  $$P_{\text{norm}} = \text{clip}\left(\frac{1010.0 - P_{\text{central}}}{75.0}, 0.05, 1.0\right)$$
  Normalized against background tropical sea-level pressure ($1010\text{ hPa}$) and severe deficit baseline ($75\text{ hPa}$).
- **Coastal Surge Inundation Proxy ($S_{\text{proxy}}$)**:
  $$S_{\text{proxy}} = \min\left(1.0, \frac{V_{\text{wind}} / 80.0}{\max(1.0, Z_{\text{elev}} \cdot 0.75)}\right)$$
  Where $Z_{\text{elev}}$ is ground elevation above mean sea level in meters. Low-elevation coastal regions ($<5\text{m}$) experience amplified surge vulnerability.

### 2.2 Exposure Score ($E \in [0.0, 1.0]$)
Evaluates human population and physical infrastructure exposed to cyclonic winds within the sector:
$$E = \min\left(1.0, \left(0.65 \cdot \text{Pop}_{\text{norm}} + 0.35 \cdot \text{Infra}_{\text{norm}}\right) \cdot \text{Prox}_{\text{factor}}\right)$$

Where:
- **Population Density ($Pop_{\text{norm}}$)**:
  $$\text{Pop}_{\text{norm}} = \text{clip}\left(\frac{\text{Population}}{1,500,000}, 0.05, 1.0\right)$$
  Calibrated against coastal district administrative units (e.g., Kutch, Kendrapara, South 24 Parganas).
- **Critical Infrastructure Density ($\text{Infra}_{\text{norm}}$)**:
  $$\text{Infra}_{\text{norm}} = \text{clip}\left(\frac{N_{\text{facilities}}}{50}, 0.05, 1.0\right)$$
  Count of ports, bridges, electrical substations, and major transport corridors.
- **Proximity Attenuation ($\text{Prox}_{\text{factor}}$)**:
  $$\text{Prox}_{\text{factor}} = \max\left(0.35, 1.0 - \frac{D_{\text{coast}}}{350.0}\right)$$
  Reflects inland structural protection, attenuating exposure as distance from coastline ($D_{\text{coast}}$ in km) increases.

### 2.3 Vulnerability Score ($V \in [0.0, 1.0]$)
Quantifies structural and demographic resilience:
$$V = \min\left(1.0, 0.50 \cdot \text{Elev}_{\text{vuln}} + 0.50 \cdot V_{\text{social}}\right)$$

Where:
- **Topographic Vulnerability ($\text{Elev}_{\text{vuln}}$)**:
  $$\text{Elev}_{\text{vuln}} = \max\left(0.20, 1.0 - \frac{Z_{\text{elev}}}{20.0}\right)$$
- **Baseline Social Vulnerability ($V_{\text{social}}$)**:
  Fixed baseline of $0.65$ based on coastal census demographic fragility indices (proportion of kutcha housing, artisanal fishing communities).

### 2.4 Lead-Time Uncertainty Penalty ($U \in [0.0, 1.0]$)
Forecast uncertainty expands as lead time increases. To avoid false precision at longer horizons:
$$U_{\text{score}} = \text{clip}\left(\frac{T_{\text{lead}}}{72.0}, 0.0, 1.0\right)$$
$$\text{Discount} = 1.0 - 0.30 \cdot U_{\text{score}}$$

At $T_{\text{lead}} = 0\text{h}$, $\text{Discount} = 1.0$. At $T_{\text{lead}} = 72\text{h}$, $\text{Discount} = 0.70$.

### 2.5 Composite Disaster Risk Score ($R \in [0.0, 1.0]$)
$$R_{\text{raw}} = 0.40 \cdot H + 0.35 \cdot E + 0.25 \cdot V$$
$$R = \text{clip}\left(R_{\text{raw}} \cdot (0.85 + 0.15 \cdot \text{Discount}), 0.05, 1.0\right)$$

---

## 3. Operational Thresholds & Action Tiers

| Score Range | Risk Category | Visual Indicator | Operational Alert Tier | Recommended System Action |
| :--- | :--- | :--- | :--- | :--- |
| **$R \ge 0.70$** | **Extreme Risk** | Red (`#ef4444`) | **Evacuation Order Advisory** | Immediate mandatory shelter dispatch, total port closure, pre-positioning of NDRF rescue teams. |
| **$0.48 \le R < 0.70$** | **High Risk** | Orange (`#f97316`) | **Cyclone Warning Advisory** | Suspension of all fishing operations, clearing coastal roads, activating multipurpose cyclone shelters. |
| **$0.28 \le R < 0.48$** | **Moderate Risk** | Yellow (`#eab308`) | **Cyclone Alert / Watch** | Securing loose infrastructure, verifying emergency power generators and drinking water stockpiles. |
| **$R < 0.28$** | **Low Risk** | Green (`#22c55e`) | **Informational Advisory** | Continuous monitoring of IMD bulletins, standard situational awareness. |

---

## 4. Code Implementation & Test Verification

The formulation is implemented deterministically in [`geospatial/risk_engine.py`](../geospatial/risk_engine.py) and verified across multiple test suites:
- `tests/test_geospatial.py`: Verifies deterministic scores, category thresholds, and component weights.
- `tests/test_risk_robustness.py`: Tests edge cases (zero exposed population, high elevation, 0h vs 72h uncertainty discount scaling).
- `tests/test_location_intelligence.py`: Verifies dynamic variation across distinct geographical coordinates.

