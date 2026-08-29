"""Phase 0 exit criteria. Run: python src/verify_phase0.py"""
from __future__ import annotations

import sys
import numpy as np
import pandas as pd

import config as C
from peptides import (
    RowLevelSplitError, assert_no_leakage, collapse_labels, is_standard_peptide,
    molecular_weight, normalize_species, parse_measurement, sequence_split,
    to_ugml, unit_kind,
)

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{'  -- ' + detail if detail and not cond else ''}")
    if not cond:
        failures.append(name)


print("\n[1] dependencies")
for mod in ("torch", "xgboost", "sklearn", "pandas", "numpy", "streamlit", "esm"):
    try:
        __import__(mod)
        check(f"import {mod}", True)
    except Exception as exc:
        check(f"import {mod}", False, repr(exc)[:70])

print("\n[2] data files readable")
for path in (C.ACTIVITY_CSV, C.LYSIS_CSV, C.MASTER_CSV, C.DRAMP_CSV):
    try:
        df = pd.read_csv(path, nrows=50, **C.CSV_READ_KWARGS)
        check(f"{path.name}", "normalized_sequence" in df.columns, "no normalized_sequence column")
    except Exception as exc:
        check(f"{path.name}", False, repr(exc)[:70])
for d in (C.LABELS, C.MODELS, C.REPORTS, C.RAW):
    check(f"dir {d.relative_to(C.ROOT)}", d.is_dir())

print("\n[3] censored-measurement parsing (the class-balance trap)")
check("'>100' is right-censored", parse_measurement(">100") == (100.0, "right"))
check("'<2' is left-censored", parse_measurement("<2") == (2.0, "left"))
check("'2.5-5' midpoints to 3.75", parse_measurement("2.5-5") == (3.75, None))
check("'3.125' is exact", parse_measurement("3.125") == (3.125, None))
check("junk -> nan", np.isnan(parse_measurement("n.d.")[0]))

print("\n[4] units and molecular weight")
check("plain 'g/ml' substring detected", unit_kind("\ufffdg/ml") == "ugml")
check("mojibaked micromolar detected", unit_kind("\ufffdM") == "uM")
check("nmol/g is not a supported unit", unit_kind("nmol/g") == "other")
gly = molecular_weight("GGGGG")
check("MW(GGGGG) ~= 303.3", abs(gly - (5 * 57.05 + 18.02)) < 1e-6, f"got {gly}")
check("uM -> ug/ml uses MW", abs(to_ugml(1000.0, "\ufffdM", "GGGGG") - gly) < 1e-6)

print("\n[5] sequence filtering")
check("plain peptide accepted", is_standard_peptide("KWKLFKKIGAVLKVL"))
check("branched notation rejected", not is_standard_peptide("(RRWQWR)2-K-(AHX)"))
check("non-standard residue rejected", not is_standard_peptide("AAAAARRRR\u03a6FKX"))
check("1-mer rejected", not is_standard_peptide("K"))

print("\n[6] leakage-safe splitting")
rows = pd.DataFrame({
    "normalized_sequence": [s for s in ("AAAAA", "CCCCC", "DDDDD", "EEEEE", "FFFFF", "GGGGG") for _ in range(4)],
    "active": [0, 1, 1, 1] * 6,
})
splits = sequence_split(rows)
check("all rows preserved", sum(len(v) for v in splits.values()) == len(rows))
try:
    assert_no_leakage(splits)
    check("no sequence in two splits", True)
except RowLevelSplitError as exc:
    check("no sequence in two splits", False, str(exc)[:70])
try:
    sequence_split(rows.drop(columns=["normalized_sequence"]))
    check("refuses to split without a sequence column", False, "it did not refuse")
except RowLevelSplitError:
    check("refuses to split without a sequence column", True)
bad = {"train": rows.iloc[:12], "test": rows.iloc[8:]}
try:
    assert_no_leakage(bad)
    check("detects a deliberately leaked split", False, "leak went undetected")
except RowLevelSplitError:
    check("detects a deliberately leaked split", True)

print("\n[7] label collapsing")
coll = collapse_labels(rows, "normalized_sequence", "active", rule="majority")
check("majority collapses 0,1,1,1 -> 1", int(coll["active"].unique()[0]) == 1)
check("one row per sequence", len(coll) == 6)

print("\n[8] species grouping")
check("strain -> species", normalize_species("Escherichia coli ATCC 25922") == "Escherichia coli")
check("off-panel species -> None", normalize_species("Bacillus subtilis 168") is None)
check("five priority species configured", len(C.PRIORITY_SPECIES) == 5)

print("\n" + "=" * 62)
if failures:
    print(f"PHASE 0 INCOMPLETE - {len(failures)} check(s) failed:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("PHASE 0 COMPLETE - all checks passed.")
