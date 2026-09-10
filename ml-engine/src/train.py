"""Main training entrypoint for ETA prediction using hybrid ML modeling.

This script orchestrates:
1. feature preprocessing through a scikit-learn pipeline,
2. Optuna-driven XGBoost tuning,
3. an optional LSTM sequence model for temporal patterns,
4. MLflow experiment tracking,
5. SHAP-based explainability artifact logging.
"""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

import matplotlib
import mlflow
import numpy as np
import pandas as pd
import shap
import torch
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from torch import nn
from torch.utils.data import DataLoader, Dataset

from data_processor import RailwayETADataProcessor
from model_tuner import OptunaXGBTuner, XGBTuningConfig

matplotlib.use("Agg")
import matplotlib.pyplot as plt


@dataclass
class ModelTrainingConfig:
    """Runtime configuration for the ETA training pipeline."""

    data_path: str
    target_column: str = "delay_minutes"
    group_column: str = "train_id"
    timestamp_column: str = "timestamp"
    sequence_columns: Optional[List[str]] = None
    feature_columns: Optional[List[str]] = None
    test_size: float = 0.2
    random_state: int = 42
    output_dir: str = "./mlruns"
    experiment_name: str = "railway_eta_hybrid_pipeline"
    tracking_uri: str = "file:./mlruns"
    n_trials: int = 25
    cv_splits: int = 3
    sequence_window: int = 5
    lstm_hidden_dim: int = 64
    lstm_epochs: int = 20
    lstm_batch_size: int = 32
    lstm_learning_rate: float = 1e-3


class SequenceDataset(Dataset):
    """PyTorch dataset for windowed sequence data used by the LSTM model."""

    def __init__(self, sequences: np.ndarray, targets: np.ndarray) -> None:
        self.sequences = torch.tensor(sequences, dtype=torch.float32)
        self.targets = torch.tensor(targets, dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.sequences)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.sequences[idx], self.targets[idx]


class LSTMRegressor(nn.Module):
    """LSTM-based regressor for capturing temporal degradation patterns."""

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
        )
        self.head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        last_hidden = out[:, -1, :]
        return self.head(last_hidden).squeeze(-1)


def load_dataset(data_path: str) -> pd.DataFrame:
    """Load the railway dataset from disk and validate its structure."""
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"Dataset is empty: {path}")

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    return df


def infer_feature_columns(df: pd.DataFrame, target_column: str) -> List[str]:
    """Infer tabular feature columns automatically from the dataset."""
    excluded = {
        target_column,
        "id",
        "train_id",
        "station_code",
        "from_station",
        "to_station",
        "route_id",
        "timestamp",
    }
    features = [
        col for col in df.columns if col not in excluded and col != target_column
    ]
    if not features:
        raise ValueError(
            "No feature columns were inferred automatically. "
            "Please provide feature_columns explicitly."
        )
    return features


def build_sequence_windows(
    df: pd.DataFrame,
    group_column: str,
    sequence_columns: Sequence[str],
    target_column: str,
    window_size: int = 5,
) -> Tuple[np.ndarray, np.ndarray]:
    """Create windowed historical sequences grouped by train ID or similar key.

    Non-numeric sequence inputs are converted to category codes to keep the LSTM
    training pipeline robust when the temporal features include station codes or
    categorical weather identifiers.
    """
    if not sequence_columns:
        raise ValueError("sequence_columns must be provided for LSTM training.")

    required = {group_column, *sequence_columns, target_column}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing sequence columns: {missing}")

    working_df = df.copy()
    for col in sequence_columns:
        if not pd.api.types.is_numeric_dtype(working_df[col]):
            working_df[col] = pd.Categorical(working_df[col]).codes.astype(np.float32)

    sequences: List[np.ndarray] = []
    targets: List[float] = []

    if "timestamp" in working_df.columns:
        working_df = working_df.sort_values([group_column, "timestamp"], kind="mergesort")

    for _, group in working_df.groupby(group_column, sort=False):
        values = group[list(sequence_columns)].to_numpy(dtype=np.float32)
        target_values = group[target_column].to_numpy(dtype=np.float32)

        for idx in range(window_size - 1, len(group)):
            window = values[idx - window_size + 1 : idx + 1]
            sequences.append(window)
            targets.append(float(target_values[idx]))

    if not sequences:
        raise ValueError(
            "Unable to construct LSTM windows. Ensure enough rows per group and a valid sequence window."
        )

    return np.asarray(sequences, dtype=np.float32), np.asarray(targets, dtype=np.float32)


def train_lstm_model(
    X_seq: np.ndarray,
    y_seq: np.ndarray,
    config: ModelTrainingConfig,
) -> Tuple[nn.Module, List[float]]:
    """Train an LSTM regression model and return it alongside training losses."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = LSTMRegressor(
        input_dim=X_seq.shape[-1],
        hidden_dim=config.lstm_hidden_dim,
    ).to(device)

    dataset = SequenceDataset(X_seq, y_seq)
    loader = DataLoader(dataset, batch_size=config.lstm_batch_size, shuffle=True)

    optimizer = torch.optim.Adam(model.parameters(), lr=config.lstm_learning_rate)
    criterion = nn.MSELoss()
    train_losses: List[float] = []

    model.train()
    for _ in range(config.lstm_epochs):
        epoch_loss = 0.0
        for batch_x, batch_y in loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)

            optimizer.zero_grad()
            pred = model(batch_x)
            loss = criterion(pred, batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()

        train_losses.append(epoch_loss / max(1, len(loader)))

    return model.to(device), train_losses


def predict_lstm(model: nn.Module, X_seq: np.ndarray) -> np.ndarray:
    """Predict sequence outputs for the LSTM regressor."""
    device = next(model.parameters()).device
    model.eval()
    with torch.no_grad():
        tensor = torch.tensor(X_seq, dtype=torch.float32).to(device)
        predictions = model(tensor)
    return predictions.cpu().numpy()


def log_shap_summary(
    model,
    X_eval: pd.DataFrame,
    artifact_path: str = "shap",
) -> None:
    """Compute a SHAP summary plot and log it as an MLflow artifact."""
    if X_eval.empty:
        raise ValueError("Evaluation frame is empty; SHAP summary could not be generated.")

    explainer = shap.Explainer(model, X_eval)
    shap_values = explainer(X_eval.head(200))

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = Path(tmp_dir) / "shap_summary.png"
        plt.figure(figsize=(10, 6))
        shap.summary_plot(
            shap_values,
            X_eval.head(200),
            plot_type="bar",
            show=False,
        )
        plt.tight_layout()
        plt.savefig(output_path, dpi=200, bbox_inches="tight")
        plt.close()
        mlflow.log_artifact(str(output_path), artifact_path=artifact_path)


def evaluate_regression(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Compute regression metrics for ETA prediction."""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    return {
        "mae": float(mae),
        "rmse": float(rmse),
        "r2": float(r2),
    }


def train_and_evaluate() -> None:
    """Run the complete hybrid ETA training workflow."""
    parser = argparse.ArgumentParser(description="Railway ETA hybrid training pipeline")
    parser.add_argument("--data-path", type=str, required=True, help="Path to the CSV training dataset.")
    parser.add_argument("--target-column", type=str, default="delay_minutes", help="Target variable column.")
    parser.add_argument("--feature-columns", nargs="*", default=None, help="Optional list of explicit feature columns.")
    parser.add_argument("--group-column", type=str, default="train_id", help="Train or route grouping key.")
    parser.add_argument("--timestamp-column", type=str, default="timestamp", help="Timestamp column used for sequence ordering.")
    parser.add_argument("--sequence-columns", nargs="*", default=None, help="Columns used for LSTM temporal modeling.")
    parser.add_argument("--experiment-name", type=str, default="railway_eta_hybrid_pipeline", help="MLflow experiment name.")
    parser.add_argument("--tracking-uri", type=str, default="file:./mlruns", help="MLflow tracking URI.")
    parser.add_argument("--output-dir", type=str, default="./mlruns", help="Local artifact output folder.")
    parser.add_argument("--n-trials", type=int, default=25, help="Number of Optuna trials for XGBoost tuning.")
    parser.add_argument("--cv-splits", type=int, default=3, help="Cross-validation splits for tuning.")
    parser.add_argument("--seed", type=int, default=42, help="Random state for reproducibility.")
    args = parser.parse_args()

    config = ModelTrainingConfig(
        data_path=args.data_path,
        target_column=args.target_column,
        group_column=args.group_column,
        timestamp_column=args.timestamp_column,
        sequence_columns=args.sequence_columns,
        feature_columns=args.feature_columns,
        output_dir=args.output_dir,
        experiment_name=args.experiment_name,
        tracking_uri=args.tracking_uri,
        n_trials=args.n_trials,
        cv_splits=args.cv_splits,
        random_state=args.seed,
    )

    df = load_dataset(config.data_path)
    target_column = config.target_column
    if target_column not in df.columns:
        raise ValueError(
            f"Training requires a labeled '{target_column}' column. "
            f"Dataset '{config.data_path}' only contains schedule features; "
            "provide observed delay data before evaluating accuracy."
        )
    feature_columns = config.feature_columns or infer_feature_columns(df, target_column)

    feature_df = df[feature_columns].copy()
    target = df[target_column].astype(float)

    X_train, X_eval, y_train, y_eval = train_test_split(
        feature_df,
        target,
        test_size=config.test_size,
        random_state=config.random_state,
    )

    processor = RailwayETADataProcessor(
        numerical_features=[
            col for col in feature_df.columns if pd.api.types.is_numeric_dtype(feature_df[col])
        ],
        categorical_features=[
            col for col in feature_df.columns if col not in [
                c for c in feature_df.columns if pd.api.types.is_numeric_dtype(feature_df[c])
            ]
        ],
        target_column=None,
    )

    X_train_processed = processor.fit_transform(X_train)
    X_eval_processed = processor.transform(X_eval)

    X_train_processed_df = pd.DataFrame(
        X_train_processed,
        columns=processor.get_feature_names_out(),
        index=X_train.index,
    )
    X_eval_processed_df = pd.DataFrame(
        X_eval_processed,
        columns=processor.get_feature_names_out(),
        index=X_eval.index,
    )

    os.makedirs(config.output_dir, exist_ok=True)
    mlflow.set_tracking_uri(config.tracking_uri)
    mlflow.set_experiment(config.experiment_name)

    with mlflow.start_run(run_name="eta_hybrid_training") as run:
        mlflow.log_params(
            {
                "target_column": config.target_column,
                "feature_count": len(feature_columns),
                "test_size": config.test_size,
                "random_state": config.random_state,
                "cv_splits": config.cv_splits,
                "n_trials": config.n_trials,
                "sequence_window": config.sequence_window,
                "lstm_epochs": config.lstm_epochs,
            }
        )

        tuner = OptunaXGBTuner(
            X=X_train_processed_df,
            y=y_train,
            config=XGBTuningConfig(
                n_trials=config.n_trials,
                cv_splits=config.cv_splits,
                random_state=config.random_state,
            ),
        )
        tuner.tune()
        xgb_model = tuner.train_best_model()

        xgb_pred = xgb_model.predict(X_eval_processed_df)
        xgb_metrics = evaluate_regression(y_eval.to_numpy(), xgb_pred)

        lstm_model = None
        lstm_pred = None
        sequence_columns = config.sequence_columns
        if sequence_columns is None:
            sequence_columns = [
                col for col in feature_columns if col not in {config.target_column, config.group_column}
            ]

        if sequence_columns and len(sequence_columns) > 0:
            try:
                seq_X, seq_y = build_sequence_windows(
                    df=df,
                    group_column=config.group_column,
                    sequence_columns=sequence_columns,
                    target_column=config.target_column,
                    window_size=config.sequence_window,
                )
                lstm_model, _ = train_lstm_model(seq_X, seq_y, config)
                if len(seq_X) > 0:
                    lstm_pred = predict_lstm(lstm_model, seq_X[: len(seq_X)])
            except ValueError as exc:
                print(f"LSTM training skipped: {exc}")
                lstm_model = None

        if lstm_model is not None and lstm_pred is not None:
            ensemble = 0.7 * xgb_pred + 0.3 * np.asarray(lstm_pred[: len(xgb_pred)], dtype=np.float32)
        else:
            ensemble = xgb_pred

        ensemble_metrics = evaluate_regression(y_eval.to_numpy(), ensemble)

        mlflow.log_metric("xgb_mae", xgb_metrics["mae"])
        mlflow.log_metric("xgb_rmse", xgb_metrics["rmse"])
        mlflow.log_metric("xgb_r2", xgb_metrics["r2"])
        mlflow.log_metric("ensemble_mae", ensemble_metrics["mae"])
        mlflow.log_metric("ensemble_rmse", ensemble_metrics["rmse"])
        mlflow.log_metric("ensemble_r2", ensemble_metrics["r2"])

        mlflow.xgboost.log_model(xgb_model, artifact_path="xgboost_model")
        mlflow.log_params({
            "best_n_estimators": xgb_model.get_params()["n_estimators"],
            "best_max_depth": xgb_model.get_params()["max_depth"],
            "best_learning_rate": xgb_model.get_params()["learning_rate"],
            "best_subsample": xgb_model.get_params()["subsample"],
            "best_colsample_bytree": xgb_model.get_params()["colsample_bytree"],
        })

        try:
            log_shap_summary(xgb_model, X_eval_processed_df)
        except Exception as exc:  # pragma: no cover - best effort compatibility
            print(f"SHAP logging failed: {exc}")

        print("Training complete.")
        print(f"XGBoost MAE: {xgb_metrics['mae']:.4f}")
        print(f"XGBoost RMSE: {xgb_metrics['rmse']:.4f}")
        print(f"Ensemble MAE: {ensemble_metrics['mae']:.4f}")


if __name__ == "__main__":
    try:
        train_and_evaluate()
    except Exception as exc:  # pragma: no cover - top-level safety guard
        raise RuntimeError(f"ETA pipeline failed: {exc}") from exc
