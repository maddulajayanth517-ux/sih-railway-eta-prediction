import pickle
from pathlib import Path

import pandas as pd

base = Path(__file__).parent / "models"
files = [
    "xgb_real_world_eta.pkl",
    "xgboost_eta_v1.pkl",
    "station_encoder.pkl",
]

print("=== Model artifact verification ===")
for name in files:
    path = base / name
    print(f"{name}: exists={path.exists()} size={path.stat().st_size if path.exists() else 0}")

model_path = base / "xgb_real_world_eta.pkl"
if not model_path.exists():
    raise SystemExit("Required model artifact is missing: xgb_real_world_eta.pkl")
try:
    with model_path.open("rb") as fh:
        model = pickle.load(fh)
    sample = pd.DataFrame({"station_encoded": [0], "distance": [0.0]})
    pred = model.predict(sample)
    print(f"xgb_real_world_eta.pkl: type={type(model).__name__} prediction={pred.tolist()}")
except Exception as exc:
    raise SystemExit(f"xgb_real_world_eta.pkl: load_error={type(exc).__name__}: {exc}")

encoder_path = base / "station_encoder.pkl"
if not encoder_path.exists():
    raise SystemExit("Required encoder artifact is missing: station_encoder.pkl")
try:
    with encoder_path.open("rb") as fh:
        enc = pickle.load(fh)
    classes = getattr(enc, "classes_", None)
    print(f"station_encoder: classes={len(classes) if classes is not None else 0}")
except Exception as exc:
    raise SystemExit(f"station_encoder: load_error={type(exc).__name__}: {exc}")
