# CycloneX Machine Learning Reproducibility & Forensic Audit Report

**Audit Date**: September 2026  
**Evaluation Standard**: Strict Leave-One-Storm-Out (LOSO) Cross-Validation without Spatial or Temporal Leakage  
**Data Provenance**: NOAA NCEI IBTrACS v04r00 North Indian Ocean (NI) 6-Hourly Synoptic Best-Track Archive  

---

## 1. Experimental Setup & Reproducibility Matrix

All models and evaluations are completely reproducible from clean code using random seed `42` and the verified 6-hourly best-track observations in `data/processed/ibtracs_ni_synoptic_6h.csv`.

| Dimension | Specification |
| :--- | :--- |
| **Dataset Source** | NOAA NCEI IBTrACS v04r00 (`ibtracs.NI.list.v04r00.csv`) |
| **Basin** | North Indian Ocean (`NI`: Bay of Bengal & Arabian Sea) |
| **Historical Storms** | **11 Named Cyclones**: `AMPHAN`, `BIPARJOY`, `FANI`, `HUDHUD`, `MICHAUNG`, `MOCHA`, `NISARGA`, `PHAILIN`, `REMAL`, `TAUKTAE`, `YAAS` |
| **Temporal Resolution** | Strictly 6-hourly synoptic observations (`00:00`, `06:00`, `12:00`, `18:00` UTC) |
| **Total Observations** | **258 sequential synoptic observations** |
| **Valid Transitions** | **+6h**: 247 samples (11 storms)<br>**+12h**: 236 samples (11 storms)<br>**+24h**: 214 samples (11 storms)<br>**+48h**: 170 samples (10 storms)<br>**+72h**: 133 samples (9 storms) |
| **Evaluation Method** | **Leave-One-Storm-Out (LOSO) Cross-Validation** (11 folds; each storm held out in exactly one test fold) |
| **Random Seed** | `random_state = 42` across all classifiers and regressors |
| **Feature Space (Classification & Intensity)** | `[lat, lon, wind_kts, pressure_hpa, pressure_deficit, d_lat_prev, d_lon_prev, d_wind_prev, trans_speed_kmh]` (9 features) |
| **Feature Space (Track Displacement)** | `[lat, lon, wind_kts, pressure_deficit, d_lat_prev, d_lon_prev, trans_speed_kmh]` (7 features) |
| **Evaluation Artifacts** | `ml/artifacts/evaluation_metrics.json`<br>`artifacts/track_evaluation_predictions.csv` (1,000 auditable prediction rows) |

---

## 2. Forensic Data-Leakage Audit

A comprehensive audit was performed across six potential vectors of data leakage:

### A. Storm-Level Leakage (Passed)
- **Rule**: A cyclone must never appear in both training and test sets.
- **Verification**: In all 11 LOSO folds, `train_storms` contains exactly 10 storms and `test_storm` contains exactly 1 storm. The intersection between training and test storms is strictly empty (`set(train_storms) ∩ {test_storm} == ∅`). Tested automatically via `tests/test_ml_baselines.py::test_loso_strict_no_storm_overlap`.

### B. Temporal / Lookahead Leakage (Passed)
- **Rule**: Features at time $T$ must not contain information from future timesteps ($T+6\text{h}, T+12\text{h}$, etc.).
- **Verification**: Input features only evaluate current state ($T$) and previous 6-hour displacement step ($T - 6\text{h}$). All future targets ($T+H$) are computed solely as prediction targets and are never fed into feature matrices.

### C. Target Leakage (Passed)
- **Rule**: The target variable or a deterministic equivalent must not exist in the input vector.
- **Verification**: In IMD category classification, the target is the storm stage at $T+6\text{h}$. The input vector does not contain $V(T+6\text{h})$ or future pressure. The model must learn the transition dynamics between current physical state and future stage.

### D. Duplicate Leakage (Passed)
- **Rule**: No duplicate observations or synthetic twins.
- **Verification**: The dataset enforces `drop_duplicates(subset=["storm_name", "iso_time"])`. All synthetic Gaussian duplicate augmentation from legacy scripts has been eradicated.

### E. Normalization / Preprocessing Leakage (Passed)
- **Rule**: Scalers or transformers must not be fit across the entire dataset before splitting.
- **Verification**: Tree-based ensembles (`RandomForestClassifier`, `GradientBoostingRegressor`) operate on raw numerical feature values without global standard scalers. Any scaling logic is localized strictly within each training fold.

### F. Artifact Leakage (Passed)
- **Rule**: Serialized evaluation metrics must reflect out-of-fold predictions, not training fit.
- **Verification**: All metrics reported in `ml/artifacts/evaluation_metrics.json` are aggregated from out-of-fold test evaluations during LOSO cross-validation. The deployable serialized models (`classifier_baseline.joblib`, `intensity_baseline.joblib`, `track_*_baseline.joblib`) are trained on the full catalog as deployment artifacts, distinct from validation evaluation.

---

## 3. Detailed Leave-One-Storm-Out (LOSO) Folds

Every storm belongs to exactly one test fold:

```text
Fold 01: Train = 222 obs (10 storms) | Test = 25 obs | Held-out: AMPHAN
Fold 02: Train = 206 obs (10 storms) | Test = 41 obs | Held-out: BIPARJOY
Fold 03: Train = 212 obs (10 storms) | Test = 35 obs | Held-out: FANI
Fold 04: Train = 215 obs (10 storms) | Test = 32 obs | Held-out: HUDHUD
Fold 05: Train = 239 obs (10 storms) | Test =  8 obs | Held-out: MICHAUNG
Fold 06: Train = 232 obs (10 storms) | Test = 15 obs | Held-out: MOCHA
Fold 07: Train = 233 obs (10 storms) | Test = 14 obs | Held-out: NISARGA
Fold 08: Train = 220 obs (10 storms) | Test = 27 obs | Held-out: PHAILIN
Fold 09: Train = 240 obs (10 storms) | Test =  7 obs | Held-out: REMAL
Fold 10: Train = 223 obs (10 storms) | Test = 24 obs | Held-out: TAUKTAE
Fold 11: Train = 228 obs (10 storms) | Test = 19 obs | Held-out: YAAS
```

Total Held-out Evaluation Points: **247 transitions** across all 11 storms.

---

## 4. Classification Verification & Baselines

- **Prediction Objective**: IMD Cyclone Category at $T+6\text{h}$
- **Classes**: Depression (D), Cyclonic Storm (CS), Severe Cyclonic Storm (SCS), Very Severe Cyclonic Storm (VSCS), Extremely Severe Cyclonic Storm (ESCS), Super Cyclonic Storm (SuCS)
- **Class Distribution**: VSCS: 53, SCS: 46, D: 44, CS: 41, ESCS: 39, SuCS: 24

### Comparative Evaluation (247 Out-of-Fold Samples)

| Model / Baseline | Accuracy | Weighted F1 | Macro F1 | Balanced Accuracy | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CycloneX Random Forest** | **67.21%** | **0.6706** | **0.6807** | **68.80%** | 100 Trees, max_depth=5, LOSO evaluated |
| **Persistence Baseline** | **70.04%** | **0.7003** | 0.6920 | 69.40% | Assumes IMD stage at $T$ persists at $T+6\text{h}$ |
| **Majority Class Baseline** | **21.46%** | 0.0758 | 0.0589 | 16.67% | Always predicts `Very Severe Cyclonic Storm` |
| **Uniform Random Guessing** | **16.67%** | 0.1667 | 0.1667 | 16.67% | $1/6$ probability across 6 classes |

### Confusion Matrix
```text
Rows = Ground Truth at T+6h, Columns = CycloneX Prediction
Classes: ['Cyclonic Storm', 'Depression', 'Extremely Severe', 'Severe Cyclonic', 'Super Cyclonic', 'Very Severe']

              CS    D  ESCS   SCS  SuCS  VSCS
CS         [  29,   2,    0,   10,    0,    0 ]
D          [   5,  38,    0,    1,    0,    0 ]
ESCS       [   0,   0,   28,    0,    7,    4 ]
SCS        [   5,   0,    2,   31,    0,    8 ]
SuCS       [   0,   0,    5,    0,   18,    1 ]
VSCS       [   1,   0,   20,   10,    0,   22 ]
```

**Scientific Commentary**:  
At a short lead time of 6 hours, atmospheric inertia causes tropical cyclones to maintain their operational stage in ~70% of 6-hour windows. The CycloneX model achieves 67.21% accuracy predicting future transitions from continuous physical state vectors. Because tropical cyclone stages are discrete bands of a continuous wind spectrum, category persistence is a recognized strong short-term baseline. CycloneX substantially outperforms both majority-class (21.46%) and random guessing (16.67%).

---

## 5. Intensity Forecast Verification vs Persistence

Evaluated on identical sample subsets across 11 storms.

| Horizon | Samples | Storms | CycloneX MAE (kts) | CycloneX RMSE (kts) | CycloneX Bias (kts) | Persistence MAE (kts) | Persistence RMSE (kts) | Persistence Bias (kts) | Skill vs Persistence (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **+6h** | 247 | 11 | **6.32** | 8.69 | +0.40 | 7.40 | 10.64 | -0.21 | **+14.6%** |
| **+12h** | 236 | 11 | **10.21** | 13.83 | -0.48 | 14.11 | 19.17 | -0.78 | **+27.7%** |
| **+24h** | 214 | 11 | **18.40** | 23.78 | -1.80 | 26.63 | 33.78 | -2.70 | **+30.9%** |
| **+48h** | 170 | 10 | **29.96** | 35.67 | -2.15 | 44.06 | 52.39 | -10.44 | **+32.0%** |
| **+72h** | 133 | 9 | **40.70** | 46.39 | -3.38 | 49.18 | 58.82 | -19.68 | **+17.2%** |

*Skill Formula*: $\text{Skill} = \left(1 - \frac{\text{MAE}_{\text{CycloneX}}}{\text{MAE}_{\text{Persistence}}}\right) \times 100\%$  
CycloneX exhibits positive skill over persistence across all five operational horizons.

---

## 6. Track Forecast Forensic Verification

Evaluated on identical sample subsets across 11 storms using Great-Circle Haversine position error.

| Horizon | Samples | Storms | CycloneX Mean Error (km) | CycloneX Median Error (km) | CycloneX Std Dev (km) | Persistence Mean Error (km) | Persistence Median Error (km) | Persistence Std Dev (km) | Skill vs Persistence (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **+6h** | 247 | 11 | **41.3** | 34.5 | 30.6 | 37.3 | 31.5 | 28.2 | -10.7% |
| **+12h** | 236 | 11 | **75.2** | 67.1 | 47.3 | 71.0 | 61.5 | 43.6 | -5.8% |
| **+24h** | 214 | 11 | **141.9** | 131.5 | 76.9 | 141.2 | 130.6 | 75.4 | -0.5% |
| **+48h** | 170 | 10 | **284.6** | 272.4 | 158.8 | 302.1 | 275.4 | 168.8 | **+5.8%** |
| **+72h** | 133 | 9 | **388.8** | 359.3 | 251.2 | 473.5 | 421.5 | 284.7 | **+17.9%** |

### Resolution of the Phase 3 Anomaly
In Phase 3, the track errors were reported as 161 km (+6h), 342 km (+12h), and 318 km (+24h). Forensic inspection revealed that because the legacy catalog only had 47 sparse milestone points, only 4 observations reached step +4 (+24h). These 4 points came from a single straight-moving storm track, distorting the sample.  
With the genuine 6-hourly dataset of 258 observations, error increases monotonically with lead time:
$$41.3\text{ km} \longrightarrow 75.2\text{ km} \longrightarrow 141.9\text{ km} \longrightarrow 284.6\text{ km} \longrightarrow 388.8\text{ km}$$
At short horizons (+6h, +12h), kinematic persistence (extrapolating recent 6h motion) is competitive, within ~4 km. At longer horizons (+48h, +72h), kinematic extrapolation diverges severely, and CycloneX achieves **+5.8%** and **+17.9%** skill over persistence.

Auditable predictions CSV: [`artifacts/track_evaluation_predictions.csv`](../artifacts/track_evaluation_predictions.csv) (1,000 rows).

