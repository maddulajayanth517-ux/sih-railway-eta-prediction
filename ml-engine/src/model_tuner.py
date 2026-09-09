"""Hyperparameter tuning and XGBoost model training for ETA prediction.

This module encapsulates Optuna-based search over XGBoost hyperparameters and
prepares the best-performing regressor for deployment into the training pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np
import optuna
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import KFold, cross_val_score


@dataclass
class XGBTuningConfig:
    """Configuration for XGBoost hyperparameter optimization."""

    n_trials: int = 40
    cv_splits: int = 3
    random_state: int = 42
    scoring: str = "neg_root_mean_squared_error"
    study_name: str = "eta_xgb_tuning"
    direction: str = "maximize"


class OptunaXGBTuner:
    """Search for the best XGBoost regressor using Optuna and cross-validation."""

    def __init__(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        config: Optional[XGBTuningConfig] = None,
    ) -> None:
        self.X = X
        self.y = y
        self.config = config or XGBTuningConfig()
        self.study_: Optional[optuna.study.Study] = None
        self.best_model_: Optional[xgb.XGBRegressor] = None

    def _build_model(self, params: Dict[str, Any]) -> xgb.XGBRegressor:
        """Create an XGBoost regressor with tuned parameters."""
        model_params = {
            "objective": "reg:squarederror",
            "eval_metric": "rmse",
            "n_estimators": int(params.get("n_estimators", 400)),
            "max_depth": int(params.get("max_depth", 6)),
            "learning_rate": float(params.get("learning_rate", 0.05)),
            "subsample": float(params.get("subsample", 0.8)),
            "colsample_bytree": float(params.get("colsample_bytree", 0.8)),
            "gamma": float(params.get("gamma", 0.0)),
            "reg_alpha": float(params.get("reg_alpha", 0.0)),
            "reg_lambda": float(params.get("reg_lambda", 1.0)),
            "min_child_weight": int(params.get("min_child_weight", 1)),
            "random_state": self.config.random_state,
            "n_jobs": -1,
            "verbosity": 0,
            "tree_method": "hist",
        }
        return xgb.XGBRegressor(**model_params)

    def objective(self, trial: optuna.trial.Trial) -> float:
        """Objective function used by Optuna for tuning."""
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 200, 1000, step=50),
            "max_depth": trial.suggest_int("max_depth", 3, 12),
            "learning_rate": trial.suggest_float(
                "learning_rate", 0.01, 0.2, log=True
            ),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "gamma": trial.suggest_float("gamma", 0.0, 5.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 5.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.0, 10.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
        }

        model = self._build_model(params)
        cv = KFold(
            n_splits=self.config.cv_splits,
            shuffle=True,
            random_state=self.config.random_state,
        )

        scores = cross_val_score(
            model,
            self.X,
            self.y,
            cv=cv,
            scoring=self.config.scoring,
            n_jobs=1,
        )
        return float(np.mean(scores))

    def tune(self) -> optuna.study.Study:
        """Run the Optuna hyperparameter search and persist the best study."""
        sampler = optuna.samplers.TPESampler(seed=self.config.random_state)
        pruner = optuna.pruners.MedianPruner(
            n_startup_trials=5,
            n_warmup_steps=10,
        )

        study = optuna.create_study(
            direction=self.config.direction,
            sampler=sampler,
            pruner=pruner,
            study_name=self.config.study_name,
        )
        study.optimize(self.objective, n_trials=self.config.n_trials, show_progress_bar=False)
        self.study_ = study
        return study

    def train_best_model(self) -> xgb.XGBRegressor:
        """Train the final XGBoost regressor using the best Optuna trial."""
        if self.study_ is None:
            raise ValueError("The study has not been tuned yet. Call tune() first.")

        best_params = self.study_.best_params
        model = self._build_model(best_params)
        model.fit(self.X, self.y)
        self.best_model_ = model
        return model


def tune_and_train_xgboost(
    X: pd.DataFrame,
    y: pd.Series,
    n_trials: int = 40,
    cv_splits: int = 3,
    random_state: int = 42,
) -> Tuple[xgb.XGBRegressor, optuna.study.Study]:
    """Convenience wrapper to run Optuna tuning and return the trained model."""
    tuner = OptunaXGBTuner(
        X=X,
        y=y,
        config=XGBTuningConfig(
            n_trials=n_trials,
            cv_splits=cv_splits,
            random_state=random_state,
        ),
    )
    study = tuner.tune()
    model = tuner.train_best_model()
    return model, study


__all__ = ["OptunaXGBTuner", "XGBTuningConfig", "tune_and_train_xgboost"]
