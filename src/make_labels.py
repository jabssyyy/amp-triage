"""Phase 1 - build activity and toxicity label tables, with the class-balance gate.

Blocking gate: nothing trains until the balance report is printed and passes.

Activity  : active = MIC/MBC <= 32 ug/ml against a given priority species.
Toxicity  : toxic  = >=50% hemolysis of human erythrocytes at a dose <= 100 ug/ml.
            safe   = tested at >= 100 ug/ml and never reached 50%.
            anything else is unlabeled and dropped.

Writes data/labels/{activity_<species>,toxicity_human_rbc}_{train,val,test}.parquet
plus data/labels/label_config.json recording every threshold and its justification.

Run: python src/make_labels.py
"""
from __future__ import annotations

import json
import sys

import pandas as pd

import config as C
from peptides import (
    assert_no_leakage, collapse_labels, is_standard_peptide, normalize_species,
    parse_measurement, sequence_split, to_ugml, unit_kind,
)

GATE_MAX_MAJORITY = 0.85  # a class above this share fails the balance gate

SEQ = "normalized_sequence"


def _prepare(df: pd.DataFrame, value_col: str, unit_col: str) -> pd.DataFrame:
    """Parse measurement + unit into a censoring-aware ug/ml column."""
    df = df[df[SEQ].map(is_standard_peptide)].copy()
    parsed = df[value_col].map(parse_measurement)
    df["value"] = [p[0] for p in parsed]
    df["censor"] = [p[1] for p in parsed]
    df["unit_kind"] = df[unit_col].map(unit_kind)
    df = df[df["value"].notna() & df["unit_kind"].isin(["ugml", "uM"])]
    df["ugml"] = [
        to_ugml(v, u, s) for v, u, s in zip(df["value"], df[unit_col], df[SEQ])
    ]
    return df[df["ugml"].notna()]


def build_activity() -> dict[str, pd.DataFrame]:
    raw = pd.read_csv(C.ACTIVITY_CSV, **C.CSV_READ_KWARGS)
    df = raw[raw["Activity Measure"].isin(C.ACTIVITY_MEASURES)].copy()
    df = df[df[SEQ].notna()]
    df = _prepare(df, "Activity", "Unit")
    df["species"] = df["Target Species"].map(normalize_species)
    df = df[df["species"].notna()]

    thr = C.ACTIVITY_THRESHOLD_UGML
    # A right-censored ">X" reading means the true MIC is above X.
    #   X >= thr  -> definitively INACTIVE (it did not work even at thr)
    #   X <  thr  -> ambiguous, true value could straddle thr -> drop the row
    df["active"] = ((df["ugml"] <= thr) & (df["censor"] != "right")).astype(int)
    df["ambiguous"] = (df["censor"] == "right") & (df["ugml"] < thr)
    dropped = int(df["ambiguous"].sum())
    df = df[~df["ambiguous"]]
    print("  activity: %d usable measurements (%d ambiguous right-censored rows dropped)"
          % (len(df), dropped))

    out: dict[str, pd.DataFrame] = {}
    for species, g in df.groupby("species"):
        coll = collapse_labels(g, SEQ, "active", rule="majority")
        if len(coll) < C.MIN_SEQS_PER_SPECIES:
            print("  SKIP %s: only %d sequences (< %d)"
                  % (species, len(coll), C.MIN_SEQS_PER_SPECIES))
            continue
        out[species] = coll
    return out


def build_toxicity() -> pd.DataFrame:
    raw = pd.read_csv(C.LYSIS_CSV, **C.CSV_READ_KWARGS)
    mask = raw["Target Cell"].astype(str).str.contains(C.TOXICITY_TARGET_CELL, na=False)
    df = raw[mask].copy()
    df = df[df[SEQ].notna()]

    # The effect level lives in 'Activity Measure for Lysis' ("50% Hemolysis"),
    # and the dose that produced it lives in 'Peptide Concentration'.
    pct = df["Activity Measure for Lysis"].astype(str).str.extract(r"^(\d+(?:\.\d+)?)%")[0]
    df["pct"] = pd.to_numeric(pct, errors="coerce")
    df = df[df["pct"].notna()]
    df = _prepare(df, "Peptide Concentration", "Unit")

    cut = C.TOXICITY_HEMOLYSIS_PCT
    dose = C.TOXICITY_REF_DOSE_UGML
    rows = []
    for seq, g in df.groupby(SEQ):
        low = g[g["ugml"] <= dose]
        high = g[g["ugml"] >= dose]
        if len(low) and low["pct"].max() >= cut:
            rows.append((seq, 1))          # half-lysed at or below the reference dose
        elif len(high) and high["pct"].max() < cut:
            rows.append((seq, 0))          # survived the reference dose
        # else: never tested informatively at this dose -> unlabeled
    labeled = pd.DataFrame(rows, columns=[SEQ, "toxic"])
    print("  toxicity: %d labeled sequences from %d with usable dose-response points"
          % (len(labeled), df[SEQ].nunique()))
    return labeled


def balance_gate(name: str, labels: pd.Series) -> bool:
    n = len(labels)
    pos = int(labels.sum())
    share = max(pos, n - pos) / n if n else 1.0
    ok = share <= GATE_MAX_MAJORITY and n >= C.MIN_SEQS_PER_SPECIES
    flag = "PASS" if ok else "FAIL"
    print("  %s  %-34s n=%5d  pos=%5d (%5.1f%%)  majority=%5.1f%%"
          % (flag, name, n, pos, 100 * pos / n, 100 * share))
    return ok


def main() -> None:
    C.LABELS.mkdir(parents=True, exist_ok=True)
    C.REPORTS.mkdir(parents=True, exist_ok=True)

    print("\n[1] building activity labels")
    activity = build_activity()
    print("\n[2] building toxicity labels")
    toxicity = build_toxicity()

    print("\n[3] CLASS-BALANCE GATE (blocking)")
    passed = True
    balance: dict[str, dict] = {}
    for species, tbl in sorted(activity.items()):
        passed &= balance_gate("activity / " + species, tbl["active"])
        balance["activity/" + species] = {
            "n": len(tbl), "positive": int(tbl["active"].sum()),
            "positive_pct": round(100 * tbl["active"].mean(), 2),
        }
    passed &= balance_gate("toxicity / human erythrocytes", toxicity["toxic"])
    balance["toxicity/human_rbc"] = {
        "n": len(toxicity), "positive": int(toxicity["toxic"].sum()),
        "positive_pct": round(100 * toxicity["toxic"].mean(), 2),
    }
    if not passed:
        print("\nGATE FAILED - revise thresholds before training. No splits written.")
        sys.exit(1)

    print("\n[4] writing leakage-safe splits")
    written = []
    for species, tbl in sorted(activity.items()):
        slug = species.lower().replace(" ", "_").replace(".", "")
        splits = sequence_split(tbl)
        assert_no_leakage(splits)
        for part, frame in splits.items():
            path = C.LABELS / ("activity_%s_%s.parquet" % (slug, part))
            frame.to_parquet(path, index=False)
            written.append(path.name)
        print("  activity_%s: %s" % (slug, " ".join(
            "%s=%d" % (p, len(f)) for p, f in splits.items())))
    tox_splits = sequence_split(toxicity)
    assert_no_leakage(tox_splits)
    for part, frame in tox_splits.items():
        path = C.LABELS / ("toxicity_human_rbc_%s.parquet" % part)
        frame.to_parquet(path, index=False)
        written.append(path.name)
    print("  toxicity_human_rbc: %s" % " ".join(
        "%s=%d" % (p, len(f)) for p, f in tox_splits.items()))

    # Dual-labeled set: the ceiling for anything selectivity-flavoured.
    all_activity_seqs: set = set()
    for tbl in activity.values():
        all_activity_seqs |= set(tbl[SEQ])
    dual = all_activity_seqs & set(toxicity[SEQ])
    print("\n  dual-labeled sequences (activity AND toxicity): %d" % len(dual))

    config = {
        "generated": "phase 1 - make_labels.py",
        "activity": {
            "measures": list(C.ACTIVITY_MEASURES),
            "threshold_ugml": C.ACTIVITY_THRESHOLD_UGML,
            "justification": C.ACTIVITY_THRESHOLD_JUSTIFICATION,
            "collapse_rule": "majority vote over a sequence's measurements, ties active",
            "censoring_rule": (
                "right-censored '>X' with X >= threshold is a definitive INACTIVE and is "
                "kept; with X < threshold it is ambiguous and dropped. Never discard "
                "censored rows wholesale - they carry the negative class."
            ),
        },
        "toxicity": {
            "target_cell": C.TOXICITY_TARGET_CELL,
            "hemolysis_pct": C.TOXICITY_HEMOLYSIS_PCT,
            "reference_dose_ugml": C.TOXICITY_REF_DOSE_UGML,
            "justification": C.TOXICITY_LABEL_JUSTIFICATION,
        },
        "sequence_filter": {
            "standard_amino_acids_only": True,
            "min_length": C.MIN_PEPTIDE_LEN,
        },
        "split": {"by": SEQ, "fractions": [0.7, 0.15, 0.15], "seed": C.RANDOM_SEED},
        "class_balance": balance,
        "dual_labeled_sequences": len(dual),
        "gate": {"max_majority_share": GATE_MAX_MAJORITY, "passed": True},
    }
    (C.LABELS / "label_config.json").write_text(json.dumps(config, indent=2))
    print("\n  wrote %d split files + label_config.json" % len(written))
    print("\nPHASE 1 COMPLETE - gate passed, splits written.")


if __name__ == "__main__":
    main()
