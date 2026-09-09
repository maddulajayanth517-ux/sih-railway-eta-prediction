import os
import pickle
import pandas as pd

base = r"D:\SIH-RAILWAY-ETA\ml-engine\models"
files = [
    "xgb_real_world_eta.pkl",
    "xgboost_eta_v1.pkl",
    "station_encoder.pkl",
]

print("=== Model artifact verification ===")
for name in files:
    path = os.path.join(base, name)
    print(f"{name}: exists={os.path.exists(path)} size={os.path.getsize(path) if os.path.exists(path) else 0}")

for name in ["xgb_real_world_eta.pkl", "xgboost_eta_v1.pkl"]:
    path = os.path.join(base, name)
    if os.path.exists(path):
        try:
            with open(path, "rb") as fh:
                model = pickle.load(fh)
            print(f"{name}: type={type(model).__name__}")
            sample = pd.DataFrame({"station_encoded": [0], "distance": [0]})
            pred = model.predict(sample)
            print(f"{name}: prediction={pred.tolist()}")
        except Exception as exc:
            print(f"{name}: load_error={type(exc).__name__}: {exc}")

path = os.path.join(base, "station_encoder.pkl")
if os.path.exists(path):
    try:
        with open(path, "rb") as fh:
            enc = pickle.load(fh)
        classes = getattr(enc, "classes_", None)
        print(f"station_encoder: classes_sample={list(classes[:5]) if classes is not None and len(classes) >= 5 else classes}")
    except Exception as exc:
        print(f"station_encoder: load_error={type(exc).__name__}: {exc}")
