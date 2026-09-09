"""Advanced preprocessing utilities for railway ETA prediction.

This module provides a reusable scikit-learn preprocessing pipeline for mixed
numerical and categorical railway features such as station codes, weather IDs,
track conditions, distances, and operational metrics.
"""

from __future__ import annotations

from typing import Any, Iterable, List, Optional

import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import NotFittedError
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, RobustScaler


class RailwayETADataProcessor(BaseEstimator, TransformerMixin):
    """Preprocess railway ETA feature matrices for ML training.

    The processor automatically separates numerical and categorical columns,
    imputes missing values, robustly scales numeric features, and one-hot encodes
    categorical variables while preserving a scikit-learn compatible interface.
    """

    def __init__(
        self,
        numerical_features: Optional[List[str]] = None,
        categorical_features: Optional[List[str]] = None,
        target_column: Optional[str] = None,
    ) -> None:
        self.numerical_features = numerical_features
        self.categorical_features = categorical_features
        self.target_column = target_column
        self.numerical_features_: List[str] = []
        self.categorical_features_: List[str] = []
        self.preprocessor_: Optional[ColumnTransformer] = None

    def _validate_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """Validate and normalize the input feature matrix."""
        if X is None or X.empty:
            raise ValueError("Input feature matrix is empty or missing.")

        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X)

        if self.target_column and self.target_column in X.columns:
            X = X.drop(columns=[self.target_column])

        return X

    def _build_preprocessor(self) -> ColumnTransformer:
        """Construct a scikit-learn column transformer for mixed data."""
        numeric_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", RobustScaler()),
            ]
        )

        categorical_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                (
                    "encoder",
                    OneHotEncoder(
                        handle_unknown="ignore",
                        sparse_output=False,
                    ),
                ),
            ]
        )

        return ColumnTransformer(
            transformers=[
                ("num", numeric_transformer, self.numerical_features_),
                ("cat", categorical_transformer, self.categorical_features_),
            ],
            remainder="drop",
        )

    def fit(self, X: pd.DataFrame, y: Any = None) -> "RailwayETADataProcessor":
        """Fit the preprocessing pipeline to the provided dataset."""
        X = self._validate_features(X)

        if self.numerical_features is None:
            self.numerical_features_ = [
                col
                for col in X.columns
                if pd.api.types.is_numeric_dtype(X[col])
            ]
        else:
            missing_numerical = [
                col for col in self.numerical_features if col not in X.columns
            ]
            if missing_numerical:
                raise ValueError(
                    "Missing numerical columns: " + ", ".join(missing_numerical)
                )
            self.numerical_features_ = list(self.numerical_features)

        if self.categorical_features is None:
            self.categorical_features_ = [
                col for col in X.columns if col not in self.numerical_features_
            ]
        else:
            missing_categorical = [
                col for col in self.categorical_features if col not in X.columns
            ]
            if missing_categorical:
                raise ValueError(
                    "Missing categorical columns: " + ", ".join(missing_categorical)
                )
            self.categorical_features_ = list(self.categorical_features)

        if not self.numerical_features_ and not self.categorical_features_:
            raise ValueError(
                "No valid numerical or categorical feature columns were found."
            )

        self.preprocessor_ = self._build_preprocessor()
        self.preprocessor_.fit(X)
        return self

    def transform(self, X: pd.DataFrame) -> Any:
        """Transform the feature matrix using the fitted preprocessor."""
        if self.preprocessor_ is None:
            raise NotFittedError(
                "RailwayETADataProcessor has not been fitted yet. Call fit() first."
            )

        X = self._validate_features(X)
        return self.preprocessor_.transform(X)

    def fit_transform(self, X: pd.DataFrame, y: Any = None) -> Any:
        """Fit the model and immediately transform the input."""
        return self.fit(X, y).transform(X)

    def get_feature_names_out(self, input_features: Optional[Iterable[str]] = None) -> List[str]:
        """Return the transformed feature names after OHE and scaling."""
        if self.preprocessor_ is None:
            raise NotFittedError(
                "RailwayETADataProcessor has not been fitted yet. Call fit() first."
            )
        return list(self.preprocessor_.get_feature_names_out(input_features))


__all__ = ["RailwayETADataProcessor"]
