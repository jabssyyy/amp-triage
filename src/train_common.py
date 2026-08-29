"""Shared training machinery for the phase 2 classifiers.

One row per sequence (labels were collapsed in phase 1), so ordinary stratified
CV is already sequence-aware -- no group leakage is possible by construction.
The held-out test split was carved by sequence in phase 1 and is never touched
during model selection.
"""
from __future__ import annotations

import pickle

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from xgboost import XGBClassifier

import config as C

SEQ = "normalized_sequence"


def load_embeddings() -> tuple[dict[str, int], np.ndarray, np.ndarray]:
    if not C.EMBEDDING_CACHE.exists():
        raise FileNotFoundError(
            "%s missing - run `python src/embed.py` first" % C.EMBEDDING_CACHE
        )
    cache = np.load(C.EMBEDDING_CACHE, allow_pickle=True)
    seqs = [str(s) for s in cache["sequences"]]
    return {s: i for i, s in enumerate(seqs)}, cache["raw"], cache["normalized"]


def load_split(stem: str, part: str) -> pd.DataFrame:
    return pd.read_parquet(C.LABELS / ("%s_%s.parquet" % (stem, part)))


def featurize(
    df: pd.DataFrame, index: dict[str, int], matrix: np.ndarray, label_col: str
) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """Attach embeddings. Sequences with no embedding are dropped and reported."""
    present = df[df[SEQ].isin(index)].copy()
    missing = len(df) - len(present)
    if missing:
        print("      dropped %d sequence(s) with no embedding" % missing)
    rows = [index[s] for s in present[SEQ]]
    return matrix[rows], present[label_col].to_numpy(), present


def make_model(n_pos: int, n_neg: int) -> XGBClassifier:
    """Small, regularised XGBoost. Training sets here are 100-700 sequences with
    480-dim features, so depth and estimator count are kept deliberately low."""
    return XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.5,
        min_child_weight=2,
        reg_lambda=2.0,
        scale_pos_weight=(n_neg / max(n_pos, 1)),
        eval_metric="logloss",
        tree_method="hist",
        n_jobs=4,
        random_state=C.RANDOM_SEED,
    )


def cross_validate(X: np.ndarray, y: np.ndarray, folds: int = 5) -> dict[str, float]:
    """Stratified k-fold. Returns mean and std of ROC-AUC and PR-AUC."""
    folds = min(folds, int(np.bincount(y).min()))
    if folds < 2:
        return {"roc_auc": float("nan"), "roc_auc_std": float("nan"),
                "pr_auc": float("nan"), "pr_auc_std": float("nan"), "folds": 0}
    skf = StratifiedKFold(n_splits=folds, shuffle=True, random_state=C.RANDOM_SEED)
    roc, pr = [], []
    for tr, te in skf.split(X, y):
        model = make_model(int(y[tr].sum()), int((1 - y[tr]).sum()))
        model.fit(X[tr], y[tr], verbose=False)
        p = model.predict_proba(X[te])[:, 1]
        roc.append(roc_auc_score(y[te], p))
        pr.append(average_precision_score(y[te], p))
    return {
        "roc_auc": float(np.mean(roc)), "roc_auc_std": float(np.std(roc)),
        "pr_auc": float(np.mean(pr)), "pr_auc_std": float(np.std(pr)),
        "folds": folds,
    }


def evaluate(model: XGBClassifier, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
    if len(np.unique(y)) < 2:
        return {"roc_auc": float("nan"), "pr_auc": float("nan"), "n": len(y),
                "positive_rate": float(y.mean()) if len(y) else float("nan")}
    p = model.predict_proba(X)[:, 1]
    return {
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "n": len(y),
        "positive_rate": float(y.mean()),
    }


def save_model(model: XGBClassifier, name: str) -> None:
    C.MODELS.mkdir(parents=True, exist_ok=True)
    with open(C.MODELS / ("%s.pkl" % name), "wb") as fh:
        pickle.dump(model, fh)


def load_model(name: str) -> XGBClassifier:
    with open(C.MODELS / ("%s.pkl" % name), "rb") as fh:
        return pickle.load(fh)


def baseline_rate(y: np.ndarray) -> float:
    """PR-AUC baseline is the positive rate; ROC-AUC baseline is always 0.5."""
    return float(y.mean()) if len(y) else float("nan")
