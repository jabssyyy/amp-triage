"""Phase 2 - human-erythrocyte XGBoost toxicity classifier.

One binary classifier over the ~272 labeled sequences from phase 1. This is a SMALL
training set and the metrics will carry wide error bars -- report the CV standard
deviation alongside the mean and say so out loud rather than quoting a single number.

Run: python src/train_toxicity.py
"""
from __future__ import annotations

import json

import pandas as pd

import config as C
from train_common import (
    baseline_rate, cross_validate, evaluate, featurize, load_embeddings,
    load_split, make_model, save_model,
)

STEM = "toxicity_human_rbc"


def main() -> None:
    index, raw, _ = load_embeddings()

    train = pd.concat([load_split(STEM, "train"), load_split(STEM, "val")])
    test = load_split(STEM, "test")

    print("\nhuman erythrocyte toxicity")
    X_tr, y_tr, _ = featurize(train, index, raw, "toxic")
    X_te, y_te, _ = featurize(test, index, raw, "toxic")
    print("      train+val=%d (%.0f%% toxic)  test=%d (%.0f%% toxic)"
          % (len(y_tr), 100 * y_tr.mean(), len(y_te), 100 * y_te.mean()))

    cv = cross_validate(X_tr, y_tr)
    print("      CV  ROC-AUC %.3f +/- %.3f   PR-AUC %.3f +/- %.3f  (%d folds)"
          % (cv["roc_auc"], cv["roc_auc_std"], cv["pr_auc"], cv["pr_auc_std"], cv["folds"]))

    model = make_model(int(y_tr.sum()), int((1 - y_tr).sum()))
    model.fit(X_tr, y_tr, verbose=False)
    held = evaluate(model, X_te, y_te)
    print("      TEST ROC-AUC %.3f   PR-AUC %.3f  (baseline PR-AUC %.3f)"
          % (held["roc_auc"], held["pr_auc"], baseline_rate(y_te)))

    save_model(model, STEM)
    results = {
        "n_train": int(len(y_tr)), "n_test": int(len(y_te)),
        "train_positive_rate": round(float(y_tr.mean()), 4),
        "cv": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in cv.items()},
        "test": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in held.items()},
        "test_pr_auc_baseline": round(baseline_rate(y_te), 4),
        "caveat": (
            "Trained on %d sequences. Small-sample metrics: quote the CV standard "
            "deviation, never the mean alone." % len(y_tr)
        ),
    }
    C.REPORTS.mkdir(parents=True, exist_ok=True)
    (C.REPORTS / "toxicity_metrics.json").write_text(json.dumps(results, indent=2))
    print("\nwrote reports/toxicity_metrics.json")
    print("TOXICITY MODEL COMPLETE")


if __name__ == "__main__":
    main()
