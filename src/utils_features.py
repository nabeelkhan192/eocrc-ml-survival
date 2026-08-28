"""
Shared helpers: leak-free design-matrix construction, cohort loading,
group/split slicing, and figure watermarking for synthetic-mode outputs.

FeatureBuilder is the single place where data-dependent preprocessing
happens. It is fitted ONLY on training-window data, frozen, persisted, and
reused for every downstream transform (test window, transported EO test,
SHAP, recalibration). This is what prevents test-window or cross-group
information from leaking into any model input.
"""
import json

import numpy as np
import pandas as pd

from config import (
    COHORT_FILE, MODELS, DATA_MODE, NUMERIC_FEATURES, INDICATOR_FEATURES,
    CATEGORICAL_FEATURES, STAGE_ONLY_FEATURES,
)


def load_cohort() -> pd.DataFrame:
    return pd.read_parquet(COHORT_FILE)


def slice_group(df: pd.DataFrame, group: str, split: str) -> pd.DataFrame:
    return df[(df.eo_group == group) & (df.split == split)].reset_index(drop=True)


class FeatureBuilder:
    """Design-matrix builder fitted on training-window data only.

    fit() learns: numeric imputation medians, the dummy-column vocabulary,
    and which columns are constant in the training window (dropped to avoid
    singular designs). transform() applies the frozen state to any data.
    """

    def __init__(self, stage_only: bool = False):
        self.stage_only = stage_only
        self.medians_: dict = {}
        self.columns_: list | None = None

    # -- internals ---------------------------------------------------------
    def _raw(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.stage_only:
            return df[STAGE_ONLY_FEATURES].copy()
        return df[NUMERIC_FEATURES + INDICATOR_FEATURES
                  + CATEGORICAL_FEATURES].copy()

    def _encode(self, raw: pd.DataFrame) -> pd.DataFrame:
        cats = STAGE_ONLY_FEATURES if self.stage_only else CATEGORICAL_FEATURES
        return pd.get_dummies(raw, columns=cats, drop_first=True).astype(float)

    # -- API ---------------------------------------------------------------
    def fit(self, train_df: pd.DataFrame) -> "FeatureBuilder":
        raw = self._raw(train_df)
        if not self.stage_only:
            for col in NUMERIC_FEATURES:
                self.medians_[col] = float(np.nanmedian(raw[col].values))
            raw = raw.fillna(self.medians_)
        X = self._encode(raw)
        # Drop columns constant in the TRAINING window (train-only rule,
        # so no test leakage). Dropped columns are printed for audit.
        keep = [c for c in X.columns if X[c].nunique() > 1]
        dropped = sorted(set(X.columns) - set(keep))
        if dropped:
            print(f"    FeatureBuilder(stage_only={self.stage_only}): "
                  f"dropped train-constant columns {dropped}")
        self.columns_ = keep
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.columns_ is None:
            raise RuntimeError("FeatureBuilder.transform called before fit")
        raw = self._raw(df)
        if not self.stage_only:
            raw = raw.fillna(self.medians_)
        X = self._encode(raw)
        # Unseen test-only categories are dropped; missing train dummies -> 0
        return X.reindex(columns=self.columns_, fill_value=0.0)

    # -- persistence -------------------------------------------------------
    def save(self, name: str) -> None:
        payload = dict(stage_only=self.stage_only, medians=self.medians_,
                       columns=self.columns_)
        (MODELS / f"{name}_features.json").write_text(json.dumps(payload))

    @classmethod
    def load(cls, name: str) -> "FeatureBuilder":
        payload = json.loads((MODELS / f"{name}_features.json").read_text())
        fb = cls(stage_only=payload["stage_only"])
        fb.medians_ = payload["medians"]
        fb.columns_ = payload["columns"]
        return fb


def watermark(fig) -> None:
    """Stamp synthetic-mode figures so they can never pass as results."""
    if DATA_MODE == "synthetic":
        fig.text(0.5, 0.5, "SYNTHETIC-DATA\nPIPELINE TEST", fontsize=28,
                 color="red", alpha=0.18, ha="center", va="center",
                 rotation=30, zorder=1000)
