"""
Satellite Dataset Pipeline for CycloneX
Establishes storm-partitioned satellite dataset directories and manifests.
Enforces storm-aware train / validation / test splits so images from the same cyclone
never appear in multiple splits.
"""
import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

DATA_DIR = os.path.dirname(__file__)
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
LABELS_DIR = os.path.join(DATA_DIR, "labels")
SPLITS_DIR = os.path.join(DATA_DIR, "splits")

for d in [RAW_DIR, PROCESSED_DIR, LABELS_DIR, SPLITS_DIR]:
    os.makedirs(d, exist_ok=True)

# Documented Metadata Schema:
# {
#   "image_id": str,
#   "source": str,
#   "timestamp": str,
#   "latitude": float,
#   "longitude": float,
#   "storm_id": str,
#   "label": int (1 = Tropical Cyclone, 0 = Disturbance/Non-cyclone)
# }

def initialize_satellite_dataset_manifest() -> Dict[str, Any]:
    """
    Creates documented storm-aware train/val/test split manifests.
    """
    # Sample storm partition assignments (Storm-Aware Partitioning)
    train_storms = ["BIPARJOY", "AMPHAN", "FANI", "HUDHUD", "PHAILIN", "YAAS", "NISARGA"]
    val_storms = ["MICHAUNG", "TAUKTAE"]
    test_storms = ["MOCHA", "REMAL"]

    def create_sample_entries(storm_names: List[str], label_mode: int = 1) -> List[Dict[str, Any]]:
        entries = []
        for s in storm_names:
            entries.append({
                "image_id": f"img-{s.lower()}-2023-01",
                "source": "NASA GIBS / MODIS Terra Corrected Reflectance",
                "timestamp": "2023-06-14T06:00:00Z",
                "latitude": 21.65,
                "longitude": 66.85,
                "storm_id": s,
                "label": label_mode,
                "channels": ["Visible_Red", "Visible_Green", "Visible_Blue"],
                "resolution_meters": 250
            })
        return entries

    train_meta = create_sample_entries(train_storms)
    val_meta = create_sample_entries(val_storms)
    test_meta = create_sample_entries(test_storms)

    # Save split manifests
    with open(os.path.join(SPLITS_DIR, "train_metadata.json"), "w") as f:
        json.dump(train_meta, f, indent=2)

    with open(os.path.join(SPLITS_DIR, "val_metadata.json"), "w") as f:
        json.dump(val_meta, f, indent=2)

    with open(os.path.join(SPLITS_DIR, "test_metadata.json"), "w") as f:
        json.dump(test_meta, f, indent=2)

    summary = {
        "pipeline_status": "STORM_AWARE_SPLIT_INITIALIZED",
        "dataset_directories": {
            "raw": RAW_DIR,
            "processed": PROCESSED_DIR,
            "labels": LABELS_DIR,
            "splits": SPLITS_DIR
        },
        "storm_partitions": {
            "train_storms": train_storms,
            "val_storms": val_storms,
            "test_storms": test_storms
        },
        "leakage_safety_guarantee": "No satellite image from the same storm ID can cross between train, validation, or test partitions."
    }

    with open(os.path.join(DATA_DIR, "satellite_dataset_manifest.json"), "w") as f:
        json.dump(summary, f, indent=2)

    return summary

if __name__ == "__main__":
    s = initialize_satellite_dataset_manifest()
    print(json.dumps(s, indent=2))

