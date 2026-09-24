"""
CycloneX Scientifically Defensible Storm-Based Machine Learning Validation (Phase 4)
Guarantees zero data leakage:
- NO row duplication or synthetic twin augmentation.
- Strict Storm-Level Group Cross-Validation (Leave-One-Storm-Out / LOSO across 11 historical storms).
- Strict temporal causality: Features at time T predict strictly into future (T+6h, T+12h, T+24h, T+48h, T+72h).
- Side-by-side comparison against Persistence baselines with identical samples.
- Predictions export to CSV for complete scientific auditability.
"""
import os
import sys
import json
import math
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    balanced_accuracy_score, confusion_matrix, mean_absolute_error, mean_squared_error
)
import joblib

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
ROOT_ARTIFACTS_DIR = os.path.join(REPO_ROOT, "artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)
os.makedirs(ROOT_ARTIFACTS_DIR, exist_ok=True)

CSV_PATH = os.path.join(REPO_ROOT, "data", "processed", "ibtracs_ni_synoptic_6h.csv")

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0)**2
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

def imd_category(wind: float) -> str:
    if wind < 34.0:
        return "Depression"
    elif wind < 48.0:
        return "Cyclonic Storm"
    elif wind < 64.0:
        return "Severe Cyclonic Storm"
    elif wind < 90.0:
        return "Very Severe Cyclonic Storm"
    elif wind < 120.0:
        return "Extremely Severe Cyclonic Storm"
    else:
        return "Super Cyclonic Storm"

def load_or_build_dataset() -> pd.DataFrame:
    """
    Loads verified 6-hourly synoptic observations and structures sequential transitions.
    """
    if not os.path.exists(CSV_PATH):
        print(f"[Data Preparation] Downloading verified 6-hourly dataset to {CSV_PATH}...")
        import subprocess
        script_path = os.path.join(REPO_ROOT, "scripts", "prepare_ibtracs_dataset.py")
        subprocess.run([sys.executable, script_path], check=True)

    df_raw = pd.read_csv(CSV_PATH)
    records = []
    
    for storm_name, grp in df_raw.groupby("storm_name"):
        grp = grp.sort_values("iso_time").reset_index(drop=True)
        n = len(grp)
        for i in range(n):
            curr = grp.iloc[i]
            prev = grp.iloc[i-1] if i > 0 else curr
            
            d_lat_prev = curr["lat"] - prev["lat"]
            d_lon_prev = curr["lon"] - prev["lon"]
            d_wind_prev = curr["wind_kts"] - prev["wind_kts"]
            dist_prev_km = haversine_km(prev["lat"], prev["lon"], curr["lat"], curr["lon"])
            trans_speed_kmh = dist_prev_km / 6.0 if i > 0 else 12.0
            press_deficit = max(0.0, 1010.0 - curr["pressure_hpa"])
            
            row_dict = {
                "storm_id": curr["sid"],
                "storm_name": storm_name,
                "iso_time": curr["iso_time"],
                "lat": curr["lat"],
                "lon": curr["lon"],
                "wind_kts": curr["wind_kts"],
                "pressure_hpa": curr["pressure_hpa"],
                "pressure_deficit": press_deficit,
                "d_lat_prev": d_lat_prev,
                "d_lon_prev": d_lon_prev,
                "d_wind_prev": d_wind_prev,
                "trans_speed_kmh": trans_speed_kmh,
                "category_T": imd_category(curr["wind_kts"])
            }
            
            # Future horizons: 6h (step 1), 12h (step 2), 24h (step 4), 48h (step 8), 72h (step 12)
            for h, step in [(6, 1), (12, 2), (24, 4), (48, 8), (72, 12)]:
                if i + step < n:
                    fut = grp.iloc[i + step]
                    row_dict[f"target_time_{h}h"] = fut["iso_time"]
                    row_dict[f"target_lat_{h}h"] = fut["lat"]
                    row_dict[f"target_lon_{h}h"] = fut["lon"]
                    row_dict[f"target_wind_{h}h"] = fut["wind_kts"]
                    row_dict[f"target_pressure_{h}h"] = fut["pressure_hpa"]
                    row_dict[f"target_cat_{h}h"] = imd_category(fut["wind_kts"])
                else:
                    row_dict[f"target_time_{h}h"] = None
                    row_dict[f"target_lat_{h}h"] = None
                    row_dict[f"target_lon_{h}h"] = None
                    row_dict[f"target_wind_{h}h"] = None
                    row_dict[f"target_pressure_{h}h"] = None
                    row_dict[f"target_cat_{h}h"] = None
                    
            records.append(row_dict)

    df = pd.DataFrame(records)
    return df

def evaluate_and_serialize() -> Dict[str, Any]:
    print("[CycloneX Validation] Loading verified 6-hourly IBTrACS dataset...")
    df = load_or_build_dataset()
    unique_storms = sorted(df["storm_name"].unique())
    num_storms = len(unique_storms)
    num_observations = len(df)
    print(f"[CycloneX Validation] Loaded {num_observations} 6-hourly observations across {num_storms} storms.")

    # ----------------------------------------------------
    # 1. Leave-One-Storm-Out (LOSO) Classification Evaluation
    # ----------------------------------------------------
    print("[CycloneX Validation] Running LOSO for IMD Stage Classification (T+6h)...")
    clf_features = ["lat", "lon", "wind_kts", "pressure_hpa", "pressure_deficit", "d_lat_prev", "d_lon_prev", "d_wind_prev", "trans_speed_kmh"]
    valid_clf = df[df["target_cat_6h"].notnull()].copy()

    y_true_clf = []
    y_pred_clf = []
    y_persist_clf = []
    loso_folds_log = []

    fold_idx = 1
    for test_storm in unique_storms:
        tr_mask = valid_clf["storm_name"] != test_storm
        te_mask = valid_clf["storm_name"] == test_storm
        if te_mask.sum() == 0:
            continue

        train_storms = sorted(valid_clf.loc[tr_mask, "storm_name"].unique().tolist())
        loso_folds_log.append({
            "fold": fold_idx,
            "test_storm": test_storm,
            "train_storms_count": len(train_storms),
            "train_samples": int(tr_mask.sum()),
            "test_samples": int(te_mask.sum())
        })

        X_tr = valid_clf.loc[tr_mask, clf_features]
        y_tr = valid_clf.loc[tr_mask, "target_cat_6h"]
        X_te = valid_clf.loc[te_mask, clf_features]
        y_te = valid_clf.loc[te_mask, "target_cat_6h"]
        persist_te = valid_clf.loc[te_mask, "category_T"]

        clf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        clf.fit(X_tr, y_tr)
        pred = clf.predict(X_te)

        y_true_clf.extend(y_te.tolist())
        y_pred_clf.extend(pred.tolist())
        y_persist_clf.extend(persist_te.tolist())
        fold_idx += 1

    classes = sorted(list(set(y_true_clf)))
    cat_acc = float(accuracy_score(y_true_clf, y_pred_clf))
    cat_f1_weighted = float(f1_score(y_true_clf, y_pred_clf, average="weighted", zero_division=0))
    cat_f1_macro = float(f1_score(y_true_clf, y_pred_clf, average="macro", zero_division=0))
    cat_bal_acc = float(balanced_accuracy_score(y_true_clf, y_pred_clf))
    cat_prec_weighted = float(precision_score(y_true_clf, y_pred_clf, average="weighted", zero_division=0))
    cat_rec_weighted = float(recall_score(y_true_clf, y_pred_clf, average="weighted", zero_division=0))
    cm = confusion_matrix(y_true_clf, y_pred_clf, labels=classes).tolist()
    class_dist = pd.Series(y_true_clf).value_counts().to_dict()

    # Baseline classification metrics
    acc_persist = float(accuracy_score(y_true_clf, y_persist_clf))
    f1_persist = float(f1_score(y_true_clf, y_persist_clf, average="weighted", zero_division=0))
    maj_class = str(pd.Series(y_true_clf).mode()[0])
    acc_maj = float(accuracy_score(y_true_clf, [maj_class] * len(y_true_clf)))
    acc_random = round(1.0 / len(classes), 4)

    # ----------------------------------------------------
    # 2. Leave-One-Storm-Out (LOSO) Intensity Forecasting
    # ----------------------------------------------------
    print("[CycloneX Validation] Running LOSO for Multi-Horizon Intensity Forecasting...")
    intensity_results = {}
    int_features = ["lat", "lon", "wind_kts", "pressure_hpa", "pressure_deficit", "d_lat_prev", "d_lon_prev", "d_wind_prev", "trans_speed_kmh"]

    for h, target_col in [(6, "target_wind_6h"), (12, "target_wind_12h"), (24, "target_wind_24h"), (48, "target_wind_48h"), (72, "target_wind_72h")]:
        valid_int = df[df[target_col].notnull()].copy()
        y_true = []
        y_pred = []
        y_persist = []

        for test_storm in unique_storms:
            tr_mask = valid_int["storm_name"] != test_storm
            te_mask = valid_int["storm_name"] == test_storm
            if te_mask.sum() == 0:
                continue

            X_tr = valid_int.loc[tr_mask, int_features]
            y_tr = valid_int.loc[tr_mask, target_col]
            X_te = valid_int.loc[te_mask, int_features]
            y_te = valid_int.loc[te_mask, target_col]

            reg = GradientBoostingRegressor(n_estimators=80, max_depth=3, learning_rate=0.05, random_state=42)
            reg.fit(X_tr, y_tr)
            pred = reg.predict(X_te)

            y_true.extend(y_te.tolist())
            y_pred.extend(pred.tolist())
            y_persist.extend(X_te["wind_kts"].tolist())

        y_true_arr = np.array(y_true)
        y_pred_arr = np.array(y_pred)
        y_per_arr = np.array(y_persist)

        mae_m = float(mean_absolute_error(y_true_arr, y_pred_arr))
        rmse_m = float(math.sqrt(mean_squared_error(y_true_arr, y_pred_arr)))
        bias_m = float(np.mean(y_pred_arr - y_true_arr))

        mae_p = float(mean_absolute_error(y_true_arr, y_per_arr))
        rmse_p = float(math.sqrt(mean_squared_error(y_true_arr, y_per_arr)))
        bias_p = float(np.mean(y_per_arr - y_true_arr))

        skill_pct = round((1.0 - (mae_m / mae_p)) * 100.0, 1)

        intensity_results[f"{h}h"] = {
            "samples": len(y_true),
            "storms_count": int(valid_int["storm_name"].nunique()),
            "cyclonex_model": {
                "mae_kts": round(mae_m, 2),
                "rmse_kts": round(rmse_m, 2),
                "bias_kts": round(bias_m, 2)
            },
            "persistence_baseline": {
                "mae_kts": round(mae_p, 2),
                "rmse_kts": round(rmse_p, 2),
                "bias_kts": round(bias_p, 2)
            },
            "skill_improvement_pct": skill_pct
        }

    # ----------------------------------------------------
    # 3. Leave-One-Storm-Out (LOSO) Track Forecasting
    # ----------------------------------------------------
    print("[CycloneX Validation] Running LOSO for Multi-Horizon Track Forecasting...")
    track_results = {}
    track_features = ["lat", "lon", "wind_kts", "pressure_deficit", "d_lat_prev", "d_lon_prev", "trans_speed_kmh"]
    track_predictions_rows = []

    for h, step, lat_col, lon_col in [
        (6, 1, "target_lat_6h", "target_lon_6h"),
        (12, 2, "target_lat_12h", "target_lon_12h"),
        (24, 4, "target_lat_24h", "target_lon_24h"),
        (48, 8, "target_lat_48h", "target_lon_48h"),
        (72, 12, "target_lat_72h", "target_lon_72h")
    ]:
        valid_track = df[df[lat_col].notnull() & df[lon_col].notnull()].copy()
        errors_m = []
        errors_p = []

        for test_storm in unique_storms:
            tr_mask = valid_track["storm_name"] != test_storm
            te_mask = valid_track["storm_name"] == test_storm
            if te_mask.sum() == 0:
                continue

            X_tr = valid_track.loc[tr_mask, track_features]
            y_dlat_tr = valid_track.loc[tr_mask, lat_col] - valid_track.loc[tr_mask, "lat"]
            y_dlon_tr = valid_track.loc[tr_mask, lon_col] - valid_track.loc[tr_mask, "lon"]

            X_te = valid_track.loc[te_mask, track_features]
            te_df = valid_track.loc[te_mask]

            reg_lat = GradientBoostingRegressor(n_estimators=50, max_depth=3, learning_rate=0.05, random_state=42)
            reg_lon = GradientBoostingRegressor(n_estimators=50, max_depth=3, learning_rate=0.05, random_state=42)
            reg_lat.fit(X_tr, y_dlat_tr)
            reg_lon.fit(X_tr, y_dlon_tr)

            d_lat_pred = reg_lat.predict(X_te)
            d_lon_pred = reg_lon.predict(X_te)

            pred_lats = X_te["lat"].values + d_lat_pred
            pred_lons = X_te["lon"].values + d_lon_pred

            persist_lats = X_te["lat"].values + (X_te["d_lat_prev"].values * step)
            persist_lons = X_te["lon"].values + (X_te["d_lon_prev"].values * step)

            act_lats = te_df[lat_col].values
            act_lons = te_df[lon_col].values

            for idx in range(len(te_df)):
                row = te_df.iloc[idx]
                a_lat, a_lon = act_lats[idx], act_lons[idx]
                p_lat, p_lon = pred_lats[idx], pred_lons[idx]
                per_lat, per_lon = persist_lats[idx], persist_lons[idx]

                err_m = haversine_km(a_lat, a_lon, p_lat, p_lon)
                err_p = haversine_km(a_lat, a_lon, per_lat, per_lon)

                errors_m.append(err_m)
                errors_p.append(err_p)

                track_predictions_rows.append({
                    "storm_id": row["storm_id"],
                    "storm_name": row["storm_name"],
                    "initial_timestamp": row["iso_time"],
                    "forecast_timestamp": row[f"target_time_{h}h"],
                    "horizon_hours": h,
                    "actual_lat": round(a_lat, 4),
                    "actual_lon": round(a_lon, 4),
                    "predicted_lat": round(p_lat, 4),
                    "predicted_lon": round(p_lon, 4),
                    "persistence_lat": round(per_lat, 4),
                    "persistence_lon": round(per_lon, 4),
                    "cyclonex_error_km": round(err_m, 2),
                    "persistence_error_km": round(err_p, 2)
                })

        err_m_arr = np.array(errors_m)
        err_p_arr = np.array(errors_p)

        mean_m = float(np.mean(err_m_arr))
        med_m = float(np.median(err_m_arr))
        std_m = float(np.std(err_m_arr))

        mean_p = float(np.mean(err_p_arr))
        med_p = float(np.median(err_p_arr))
        std_p = float(np.std(err_p_arr))

        skill_pct = round((1.0 - (mean_m / mean_p)) * 100.0, 1)

        track_results[f"{h}h"] = {
            "samples": len(errors_m),
            "storms_count": int(valid_track["storm_name"].nunique()),
            "cyclonex_model": {
                "mean_error_km": round(mean_m, 1),
                "median_error_km": round(med_m, 1),
                "std_error_km": round(std_m, 1)
            },
            "persistence_baseline": {
                "mean_error_km": round(mean_p, 1),
                "median_error_km": round(med_p, 1),
                "std_error_km": round(std_p, 1)
            },
            "skill_improvement_pct": skill_pct
        }

    # Save track prediction rows to CSV
    track_csv_root = os.path.join(ROOT_ARTIFACTS_DIR, "track_evaluation_predictions.csv")
    track_csv_ml = os.path.join(ARTIFACTS_DIR, "track_evaluation_predictions.csv")
    df_track_preds = pd.DataFrame(track_predictions_rows)
    df_track_preds.to_csv(track_csv_root, index=False)
    df_track_preds.to_csv(track_csv_ml, index=False)
    print(f"[CycloneX Validation] Saved {len(df_track_preds)} track predictions to {track_csv_root}")

    # ----------------------------------------------------
    # 4. Train Deployable Production Models (Full Catalog)
    # ----------------------------------------------------
    print("[CycloneX Validation] Training deployable baseline artifacts on full dataset...")
    final_clf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    final_clf.fit(valid_clf[clf_features], valid_clf["target_cat_6h"])

    final_intensity = GradientBoostingRegressor(n_estimators=80, max_depth=3, learning_rate=0.05, random_state=42)
    final_intensity.fit(df[df["target_wind_6h"].notnull()][int_features], df[df["target_wind_6h"].notnull()]["target_wind_6h"])

    final_track_lat = GradientBoostingRegressor(n_estimators=50, max_depth=3, learning_rate=0.05, random_state=42)
    final_track_lon = GradientBoostingRegressor(n_estimators=50, max_depth=3, learning_rate=0.05, random_state=42)
    t_valid = df[df["target_lat_6h"].notnull()]
    final_track_lat.fit(t_valid[track_features], t_valid["target_lat_6h"] - t_valid["lat"])
    final_track_lon.fit(t_valid[track_features], t_valid["target_lon_6h"] - t_valid["lon"])

    joblib.dump(final_clf, os.path.join(ARTIFACTS_DIR, "classifier_baseline.joblib"))
    joblib.dump(final_intensity, os.path.join(ARTIFACTS_DIR, "intensity_baseline.joblib"))
    joblib.dump(final_track_lat, os.path.join(ARTIFACTS_DIR, "track_dlat_baseline.joblib"))
    joblib.dump(final_track_lon, os.path.join(ARTIFACTS_DIR, "track_dlon_baseline.joblib"))

    # Construct complete evaluation JSON
    results = {
        "scientific_validation_methodology": "Leave-One-Storm-Out (LOSO) Cross-Validation without temporal or storm-level data leakage",
        "dataset_summary": {
            "source": "NOAA NCEI IBTrACS v04r00 North Indian Ocean (NI) 6-Hourly Synoptic Best Track",
            "num_storms": num_storms,
            "storms_included": unique_storms,
            "num_observations": num_observations,
            "temporal_resolution": "6-hourly synoptic (00Z, 06Z, 12Z, 18Z)"
        },
        "loso_folds": loso_folds_log,
        "classification_validation": {
            "prediction_target": "IMD Stage Category at T+6h (No Target Leakage)",
            "model_type": "RandomForestClassifier (Storm-Grouped LOSO)",
            "accuracy": round(cat_acc, 4),
            "weighted_f1": round(cat_f1_weighted, 4),
            "macro_f1": round(cat_f1_macro, 4),
            "balanced_accuracy": round(cat_bal_acc, 4),
            "precision_weighted": round(cat_prec_weighted, 4),
            "recall_weighted": round(cat_rec_weighted, 4),
            "classes": classes,
            "confusion_matrix": cm,
            "class_distribution": class_dist,
            "baseline_comparisons": {
                "persistence_baseline": {
                    "description": "Category at time T assumed to persist at T+6h",
                    "accuracy": round(acc_persist, 4),
                    "weighted_f1": round(f1_persist, 4)
                },
                "majority_class_baseline": {
                    "description": f"Always predict majority class ({maj_class})",
                    "accuracy": round(acc_maj, 4)
                },
                "random_guessing_baseline": {
                    "description": f"Uniform random selection among {len(classes)} classes",
                    "accuracy": acc_random
                }
            }
        },
        "intensity_validation": {
            "methodology": "Storm-Grouped LOSO Regression evaluated against Persistence on identical sample subsets",
            "horizons": intensity_results
        },
        "track_validation": {
            "methodology": "Great-Circle Position Error (km) evaluated via Storm-Grouped LOSO against Persistence on identical sample subsets",
            "horizons": track_results
        },
        "evaluation_timestamp": pd.Timestamp.now(tz="UTC").isoformat()
    }

    metrics_path = os.path.join(ARTIFACTS_DIR, "evaluation_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"[CycloneX Validation] Evaluation complete! Genuine metrics saved to {metrics_path}")
    return results

if __name__ == "__main__":
    res = evaluate_and_serialize()
    print(f"\n[Summary] Classification Accuracy: {res['classification_validation']['accuracy']*100:.2f}% | F1: {res['classification_validation']['weighted_f1']}")
    print(f"[Summary] Intensity 6h MAE: {res['intensity_validation']['horizons']['6h']['cyclonex_model']['mae_kts']} kts ({res['intensity_validation']['horizons']['6h']['skill_improvement_pct']}% skill)")
    print(f"[Summary] Track 6h Error: {res['track_validation']['horizons']['6h']['cyclonex_model']['mean_error_km']} km")
