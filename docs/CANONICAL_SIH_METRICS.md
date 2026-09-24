# CycloneX Canonical SIH Grand Finale Performance Metrics

**Document Authority**: Single Source of Truth for all UI, Documentation, and Jury Presentations  
**Evaluation Run Timestamp**: `2026-09-16T14:04:13.163968+00:00`  
**Registry Version**: `3.0 (Forensically Verified)`  
**Authoritative Artifact**: [`ml/artifacts/evaluation_metrics.json`](../ml/artifacts/evaluation_metrics.json)  
**Track Prediction Audit Trail**: [`artifacts/track_evaluation_predictions.csv`](../artifacts/track_evaluation_predictions.csv) (1,000 Out-of-Fold Predictions)  

---

## 1. Dataset & Validation Methodology

- **Source Archive**: NOAA NCEI International Best Track Archive for Climate Stewardship (IBTrACS) v04r00 (`ibtracs.NI.list.v04r00.csv`).
- **Basin Scope**: North Indian Ocean (`NI`: Bay of Bengal & Arabian Sea).
- **Storm Population**: **11 Historical Named Cyclones**:
  1. `AMPHAN` (2020)
  2. `BIPARJOY` (2023)
  3. `FANI` (2019)
  4. `HUDHUD` (2014)
  5. `MICHAUNG` (2023)
  6. `MOCHA` (2023)
  7. `NISARGA` (2020)
  8. `PHAILIN` (2013)
  9. `REMAL` (2024)
  10. `TAUKTAE` (2021)
  11. `YAAS` (2021)
- **Temporal Cadence**: Strictly 6-hourly synoptic observations (`00:00`, `06:00`, `12:00`, `18:00` UTC).
- **Total Genuine Observations**: **258 sequential synoptic records** (zero synthetic duplicates, zero data augmentation twins).
- **Validation Standard**: **Leave-One-Storm-Out (LOSO) Cross-Validation** (11 folds; in each fold, 10 storms form the training partition and 1 held-out storm forms the test partition).
- **Data Leakage Guarantee**: Zero storm overlap (`set(train) ∩ set(test) == ∅`), zero target lookahead leakage, zero pre-split global normalization.

---

## 2. Classification Performance (IMD Stage at T+6h)

- **Target Variable**: Discrete IMD category 6 hours into the future ($T+6\text{h}$) without target wind leakage.
- **Model Architecture**: `RandomForestClassifier` (100 estimators, max_depth=5, random_state=42).
- **Evaluated Samples**: 247 valid sequential out-of-fold transitions.

### Benchmark Comparison

| Evaluation Metric | CycloneX Model | Naive Persistence Baseline | Majority Class Baseline | Uniform Random Guessing |
| :--- | :--- | :--- | :--- | :--- |
| **Accuracy** | **67.21%** | **70.04%** | 21.46% | 16.67% |
| **Weighted F1** | **0.6706** | **0.7003** | 0.0758 | 0.1667 |
| **Macro F1** | **0.6807** | 0.6920 | 0.0589 | 0.1667 |
| **Balanced Accuracy** | **68.80%** | 69.40% | 16.67% | 16.67% |
| **Weighted Precision** | **0.6858** | 0.7012 | 0.0461 | 0.1667 |
| **Weighted Recall** | **0.6721** | 0.7004 | 0.2146 | 0.1667 |

### Authoritative Mandated Scientific Finding
> **"CycloneX does not outperform naive persistence for +6h classification in this evaluation."**

*Scientific Rationale*: Tropical cyclones exhibit strong temporal autocorrelation over short intervals ($\Delta t = 6\text{h}$). In ~70% of 6-hour synoptic windows, a storm remains in the same discrete operational stage. Naive stage persistence is therefore an exceptionally stringent baseline. CycloneX demonstrates valid transition learning without leakage, significantly outperforming majority-class (21.46%) and random guessing (16.67%).

### Authoritative Confusion Matrix (247 Samples)
```text
Rows = Ground Truth Category at T+6h | Columns = Predicted Category
Classes: [CS: Cyclonic Storm, D: Depression, ESCS: Extremely Severe, SCS: Severe, SuCS: Super Cyclonic, VSCS: Very Severe]

            CS    D  ESCS   SCS  SuCS  VSCS   Total
CS         [29,   2,    0,   10,    0,    0]     41
D          [ 5,  38,    0,    1,    0,    0]     44
ESCS       [ 0,   0,   28,    0,    7,    4]     39
SCS        [ 5,   0,    2,   31,    0,    8]     46
SuCS       [ 0,   0,    5,    0,   18,    1]     24
VSCS       [ 1,   0,   20,   10,    0,   22]     53
---------------------------------------------------
Total      [40,  40,   55,   52,   25,   35]    247
```

---

## 3. Intensity Forecast Performance (Max Sustained Wind MAE)

- **Target Variable**: Maximum sustained 10-minute surface wind speed (kts) at horizons $+6\text{h}, +12\text{h}, +24\text{h}, +48\text{h}, +72\text{h}$.
- **Model Architecture**: `GradientBoostingRegressor` (80 estimators, max_depth=3, learning_rate=0.05, random_state=42).
- **Skill Calculation**: $\text{Skill Improvement (\%)} = \left(1 - \frac{\text{MAE}_{\text{CycloneX}}}{\text{MAE}_{\text{Persistence}}}\right) \times 100\%$

### Canonical Multi-Horizon Intensity Table

| Horizon | Valid Transitions | Storms | CycloneX MAE (kts) | CycloneX RMSE (kts) | CycloneX Bias (kts) | Persistence MAE (kts) | Persistence RMSE (kts) | Persistence Bias (kts) | Skill vs Persistence (%) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **+6h** | 247 | 11 | **6.32** | 8.69 | +0.40 | **7.40** | 10.64 | -0.21 | **+14.6%** |
| **+12h** | 236 | 11 | **10.21** | 13.83 | -0.48 | **14.11** | 19.17 | -0.78 | **+27.7%** |
| **+24h** | 214 | 11 | **18.40** | 23.78 | -1.80 | **26.63** | 33.78 | -2.70 | **+30.9%** |
| **+48h** | 170 | 10 | **29.96** | 35.67 | -2.15 | **44.06** | 52.39 | -10.44 | **+32.0%** |
| **+72h** | 133 | 9 | **40.70** | 46.39 | -3.38 | **49.18** | 58.82 | -19.68 | **+17.2%** |

*Scientific Finding*: CycloneX exhibits consistent, verified positive skill over persistence across all five operational horizons, cutting 24-hour intensity error from 26.63 kts to 18.40 kts (+30.9% skill).

---

## 4. Track Trajectory Performance (Great-Circle Haversine Error)

- **Target Variable**: Great-Circle displacement error (km) computed via spherical Haversine formula against actual future eye coordinates.
- **Model Architecture**: Dual `GradientBoostingRegressor` predicting orthogonal displacement components ($\Delta\text{lat}, \Delta\text{lon}$).
- **Kinematic Persistence**: Extrapolates previous 6-hour vector displacement ($x_T + v_{\text{prev}} \times \Delta t$).

### Canonical Multi-Horizon Track Table

| Horizon | Valid Transitions | Storms | CycloneX Mean (km) | CycloneX Median (km) | CycloneX Std (km) | Persistence Mean (km) | Persistence Median (km) | Persistence Std (km) | Skill vs Persistence (%) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **+6h** | 247 | 11 | **41.3** | 34.5 | 30.6 | **37.3** | 31.5 | 28.2 | -10.7% (Persistence competitive) |
| **+12h** | 236 | 11 | **75.2** | 67.1 | 47.3 | **71.0** | 61.5 | 43.6 | -5.8% (Persistence competitive) |
| **+24h** | 214 | 11 | **141.9** | 131.5 | 76.9 | **141.2** | 130.6 | 75.4 | -0.5% (Near-parity / comparable) |
| **+48h** | 170 | 10 | **284.6** | 272.4 | 158.8 | **302.1** | 275.4 | 168.8 | **+5.8%** (Demonstrated skill) |
| **+72h** | 133 | 9 | **388.8** | 359.3 | 251.2 | **473.5** | 421.5 | 284.7 | **+17.9%** (Demonstrated skill) |

### Scientifically Accurate Track Interpretation
1. **Short Horizons (+6h, +12h)**: Kinematic persistence is highly competitive. CycloneX does *not* claim superiority over persistence at 6h or 12h (differences are within 4 km).
2. **Intermediate Horizon (+24h)**: CycloneX and persistence perform comparably (141.9 km vs 141.2 km).
3. **Extended Horizons (+48h, +72h)**: CycloneX demonstrates significant positive skill (+5.8% at 48h, +17.9% at 72h), reducing 72-hour position displacement error from 473.5 km down to 388.8 km (an 84.7 km improvement).

---

## 5. Scientific Boundaries & Stated Limitations

1. **Satellite Vision Deep Learning Status**:
   - **Current Active Pipeline**: Analytical spectral-gradient vorticity baseline (`ml/satellite_detector.py`).
   - **Deep Network Status**: `NOT TRAINED — DATASET REQUIRED`.
   - **Explicit Rule**: CycloneX never displays unverified CNN accuracy or claims deep-learning satellite detection.
2. **Risk Engine Formulation**:
   - The risk model is strictly an **empirical multi-criteria decision-support index combining hazard, exposure, vulnerability and uncertainty** under the United Nations UNDRR framework.
   - It is **NOT** an ADCIRC, SLOSH, or hydrodynamic numerical surge simulation, and does **NOT** solve 2D shallow-water Navier-Stokes equations.
3. **Operational Decision Support**:
   - CycloneX is an auxiliary emergency decision-support copilot designed for District Magistrates, First Responders, and Port Authorities.
   - It does **not** replace statutory meteorological bulletins from the India Meteorological Department (IMD) or official evacuation mandates from the National Disaster Management Authority (NDMA).

