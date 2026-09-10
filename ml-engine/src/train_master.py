"""Train and evaluate the deployable railway ETA model.

The input CSV must contain ``station_name``, ``distance_from_origin``,
``train_no`` and an observed numeric ``delay_minutes`` target. The evaluation
metric is the percentage of held-out observations predicted within 15 minutes.
The model is not published when that accuracy is below the configured gate.
"""

from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import LabelEncoder

FEATURES = ["station_encoded", "distance"]
REQUIRED_COLUMNS = {
    "station_name",
    "distance_from_origin",
    "train_no",
    "delay_minutes",
}


def load_labeled_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"Dataset is empty: {path}")

    frame = pd.read_csv(path)
    missing = sorted(REQUIRED_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(
            "Master training requires observed delay labels. Missing columns: "
            + ", ".join(missing)
        )
    frame = frame.dropna(subset=list(REQUIRED_COLUMNS)).copy()
    frame["delay_minutes"] = pd.to_numeric(frame["delay_minutes"], errors="coerce")
    frame["distance_from_origin"] = pd.to_numeric(
        frame["distance_from_origin"], errors="coerce"
    )
    frame = frame.dropna(subset=["delay_minutes", "distance_from_origin"])
    if len(frame) < 100:
        raise ValueError("At least 100 labeled observations are required for evaluation.")
    return frame


def train_and_evaluate(
    data_path: Path,
    model_path: Path,
    encoder_path: Path,
    report_path: Path,
    seed: int = 42,
    test_size: float = 0.2,
    tolerance_minutes: float = 15.0,
    min_accuracy: float = 0.8,
) -> dict[str, float | int | str]:
    frame = load_labeled_data(data_path)
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_indices, test_indices = next(
        splitter.split(frame, groups=frame["train_no"])
    )
    train = frame.iloc[train_indices]
    test = frame.iloc[test_indices]

    encoder = LabelEncoder().fit(train["station_name"].astype(str))
    train_encoded = encoder.transform(train["station_name"].astype(str))
    test_names = test["station_name"].astype(str)
    known = set(encoder.classes_)
    test_encoded = np.array(
        [int(encoder.transform([name])[0]) if name in known else 0 for name in test_names]
    )

    X_train = pd.DataFrame(
        {"station_encoded": train_encoded, "distance": train["distance_from_origin"]}
    )
    X_test = pd.DataFrame(
        {"station_encoded": test_encoded, "distance": test["distance_from_origin"]}
    )
    y_train = train["delay_minutes"].astype(float)
    y_test = test["delay_minutes"].astype(float)

    model = xgb.XGBRegressor(
        objective="reg:squarederror",
        eval_metric="rmse",
        n_estimators=800,
        max_depth=6,
        learning_rate=0.04,
        min_child_weight=3,
        subsample=0.85,
        colsample_bytree=1.0,
        reg_alpha=0.1,
        reg_lambda=2.0,
        random_state=seed,
        n_jobs=-1,
        tree_method="hist",
    )
    model.fit(X_train[FEATURES], y_train)
    predictions = np.maximum(0.0, model.predict(X_test[FEATURES]))
    absolute_errors = np.abs(y_test.to_numpy() - predictions)
    metrics: dict[str, float | int | str] = {
        "mae_minutes": float(mean_absolute_error(y_test, predictions)),
        "rmse_minutes": float(np.sqrt(mean_squared_error(y_test, predictions))),
        "r2": float(r2_score(y_test, predictions)),
        "within_tolerance_accuracy": float(np.mean(absolute_errors <= tolerance_minutes)),
        "tolerance_minutes": tolerance_minutes,
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "model": "XGBRegressor",
    }
    if metrics["within_tolerance_accuracy"] < min_accuracy:
        raise RuntimeError(
            f"Accuracy gate failed: {metrics['within_tolerance_accuracy']:.2%} "
            f"within {tolerance_minutes:g} minutes; required {min_accuracy:.2%}."
        )

    model_path.parent.mkdir(parents=True, exist_ok=True)
    with model_path.open("wb") as handle:
        pickle.dump(model, handle, protocol=pickle.HIGHEST_PROTOCOL)
    with encoder_path.open("wb") as handle:
        pickle.dump(encoder, handle, protocol=pickle.HIGHEST_PROTOCOL)
    report_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the gated production ETA model")
    parser.add_argument("--data-path", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, default=Path("ml-engine/models/xgb_real_world_eta.pkl"))
    parser.add_argument("--encoder-path", type=Path, default=Path("ml-engine/models/station_encoder.pkl"))
    parser.add_argument("--report-path", type=Path, default=Path("ml-engine/models/evaluation.json"))
    parser.add_argument("--min-accuracy", type=float, default=0.8)
    parser.add_argument("--tolerance-minutes", type=float, default=15.0)
    args = parser.parse_args()
    metrics = train_and_evaluate(
        args.data_path,
        args.model_path,
        args.encoder_path,
        args.report_path,
        min_accuracy=args.min_accuracy,
        tolerance_minutes=args.tolerance_minutes,
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
