"""Phase 2 - per-species XGBoost activity classifiers.

One binary classifier per WHO-priority species, features = raw mean-pooled ESM2
embedding, target = the `active` label from phase 1. 5-fold stratified CV on
train+val (sequence-aware by construction: one row per sequence), then a single
honest evaluation on the phase-1 test split.

Run: python src/train_activity.py
"""
from __future__ import annotations

import json

import pandas as pd

import config as C
from train_common import (
    baseline_rate, cross_validate, evaluate, featurize, load_embeddings,
    load_split, make_model, save_model,
)


def species_slug(species: str) -> str:
    return species.lower().replace(" ", "_").replace(".", "")


def main() -> None:
    index, raw, _ = load_embeddings()
    results: dict[str, dict] = {}

    for species in C.PRIORITY_SPECIES:
        slug = species_slug(species)
        stem = "activity_%s" % slug
        try:
            train = pd.concat([load_split(stem, "train"), load_split(stem, "val")])
            test = load_split(stem, "test")
        except FileNotFoundError:
            print("\n%s: no split files, skipping" % species)
            continue

        print("\n%s" % species)
        X_tr, y_tr, _ = featurize(train, index, raw, "active")
        X_te, y_te, _ = featurize(test, index, raw, "active")
        print("      train+val=%d (%.0f%% active)  test=%d (%.0f%% active)"
              % (len(y_tr), 100 * y_tr.mean(), len(y_te), 100 * y_te.mean()))

        cv = cross_validate(X_tr, y_tr)
        print("      CV  ROC-AUC %.3f +/- %.3f   PR-AUC %.3f +/- %.3f  (%d folds)"
              % (cv["roc_auc"], cv["roc_auc_std"], cv["pr_auc"], cv["pr_auc_std"], cv["folds"]))

        model = make_model(int(y_tr.sum()), int((1 - y_tr).sum()))
        model.fit(X_tr, y_tr, verbose=False)
        held = evaluate(model, X_te, y_te)
        print("      TEST ROC-AUC %.3f   PR-AUC %.3f  (baseline PR-AUC %.3f)"
              % (held["roc_auc"], held["pr_auc"], baseline_rate(y_te)))

        save_model(model, "activity_%s" % slug)
        results[species] = {
            "n_train": int(len(y_tr)), "n_test": int(len(y_te)),
            "train_positive_rate": round(float(y_tr.mean()), 4),
            "cv": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in cv.items()},
            "test": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in held.items()},
            "test_pr_auc_baseline": round(baseline_rate(y_te), 4),
        }

    C.REPORTS.mkdir(parents=True, exist_ok=True)
    (C.REPORTS / "activity_metrics.json").write_text(json.dumps(results, indent=2))
    print("\nwrote reports/activity_metrics.json")
    print("ACTIVITY MODELS COMPLETE (%d species)" % len(results))


if __name__ == "__main__":
    main()
