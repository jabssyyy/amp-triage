"""Sequence handling, measurement parsing, unit conversion, and leakage-safe splitting.

This module exists because four things in the raw tables will silently corrupt the
labels if handled naively. All four are encoded here once:

1. CENSORED MEASUREMENTS. 2,533 activity rows read ">100", ">256" etc, and 1,328 more
   are ranges like "2.5-5". A plain pd.to_numeric(...).dropna() deletes ~3,900 rows,
   almost all of them INACTIVES, and pushes the class balance from ~62/38 to ~90/10.
   parse_measurement() keeps the value and reports the censoring direction instead.

2. MIXED UNITS. Activity arrives in both ug/ml and uM. Converting needs the peptide's
   molecular weight, computed from its own sequence. See to_ugml().

3. NON-STANDARD SEQUENCES. 1,265 of 11,433 master sequences are not plain peptides --
   "(RRWQWR)2-K-(AHX)", sequences containing the greek phi, or "X" placeholders.
   ESM2 cannot embed these. is_standard_peptide() filters them.

4. ROW-LEVEL SPLITTING. The same peptide appears in many measurement rows. Splitting by
   row puts a sequence in both train and test. sequence_split() refuses to do that.
"""
from __future__ import annotations

import re
from typing import Iterable

import numpy as np
import pandas as pd

from config import MIN_PEPTIDE_LEN, PRIORITY_SPECIES, RANDOM_SEED

STANDARD_AA = frozenset("ACDEFGHIKLMNPQRSTVWY")

# Average residue masses (Da), i.e. amino acid mass minus one water.
_RESIDUE_MASS = {
    "A": 71.08, "R": 156.19, "N": 114.10, "D": 115.09, "C": 103.14,
    "E": 129.12, "Q": 128.13, "G": 57.05, "H": 137.14, "I": 113.16,
    "L": 113.16, "K": 128.17, "M": 131.19, "F": 147.18, "P": 97.12,
    "S": 87.08, "T": 101.10, "W": 186.21, "Y": 163.18, "V": 99.13,
}
_WATER = 18.02

_RANGE_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)$")


# --- sequences ---------------------------------------------------------------

def is_standard_peptide(seq, min_len: int = MIN_PEPTIDE_LEN) -> bool:
    """True if seq is a plain peptide ESM2 can embed."""
    if not isinstance(seq, str):
        return False
    s = seq.strip().upper()
    return len(s) >= min_len and set(s) <= STANDARD_AA


def molecular_weight(seq: str) -> float:
    """Molecular weight in Da from sequence. Assumes a standard peptide."""
    return sum(_RESIDUE_MASS[c] for c in seq.strip().upper()) + _WATER


# --- measurements -------------------------------------------------------------

def parse_measurement(raw) -> tuple[float, str | None]:
    """Parse a DBAASP measurement string into (value, censoring).

    Censoring is 'right' for ">100" (the true value is ABOVE 100 -- this is evidence
    of INACTIVITY), 'left' for "<2", or None for an exact reading. Ranges "2.5-5"
    return their midpoint, uncensored. Unparseable input returns (nan, None).

    Never discard right-censored rows: they carry the negative class.
    """
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return float("nan"), None
    s = str(raw).strip()
    censor = None
    if s.startswith(">="):
        censor, s = "right", s[2:]
    elif s.startswith("<="):
        censor, s = "left", s[2:]
    elif s.startswith(">"):
        censor, s = "right", s[1:]
    elif s.startswith("<"):
        censor, s = "left", s[1:]
    s = s.strip()
    m = _RANGE_RE.match(s)
    if m:
        return (float(m.group(1)) + float(m.group(2))) / 2.0, censor
    try:
        return float(s), censor
    except ValueError:
        return float("nan"), censor


def unit_kind(raw) -> str:
    """Classify a unit string as 'ugml', 'uM', or 'other'.

    Substring matching, because the CSVs are not clean UTF-8 and the micro sign
    arrives as a replacement character.
    """
    u = str(raw).strip()
    if "g/ml" in u:
        return "ugml"
    if u.endswith("M") and "mol" not in u.lower():
        return "uM"
    return "other"


def to_ugml(value: float, unit: str, seq: str) -> float:
    """Convert a concentration to ug/ml. uM needs the peptide's molecular weight."""
    kind = unit_kind(unit)
    if kind == "ugml":
        return value
    if kind == "uM":
        return value * molecular_weight(seq) / 1000.0
    return float("nan")


def normalize_species(raw) -> str | None:
    """Map a DBAASP target-species string to one of the priority species, else None.

    DBAASP records strains ("Escherichia coli ATCC 25922"); we group to species.
    """
    s = str(raw).strip()
    for species in PRIORITY_SPECIES:
        if s.startswith(species):
            return species
    return None


# --- leakage-safe splitting -----------------------------------------------------

class RowLevelSplitError(RuntimeError):
    """Raised when a caller tries to split measurement rows instead of sequences."""


def sequence_split(
    df: pd.DataFrame,
    seq_col: str = "normalized_sequence",
    fractions: tuple[float, float, float] = (0.7, 0.15, 0.15),
    seed: int = RANDOM_SEED,
) -> dict[str, pd.DataFrame]:
    """Split by unique sequence, never by row. Returns {'train','val','test'}.

    Refuses to run if the frame holds duplicate sequences without them being
    grouped -- i.e. it assigns whole sequences to splits, so a peptide can never
    appear on both sides. The returned frames are row-level subsets, but the
    membership decision was made at sequence level.
    """
    if seq_col not in df.columns:
        raise RowLevelSplitError(
            f"cannot split: no {seq_col!r} column. Splitting by row index would leak "
            "the same peptide into train and test."
        )
    if not np.isclose(sum(fractions), 1.0):
        raise ValueError(f"fractions must sum to 1.0, got {fractions}")

    seqs = np.array(sorted(df[seq_col].dropna().unique()))
    rng = np.random.default_rng(seed)
    rng.shuffle(seqs)

    n = len(seqs)
    n_train = int(round(fractions[0] * n))
    n_val = int(round(fractions[1] * n))
    buckets = {
        "train": set(seqs[:n_train]),
        "val": set(seqs[n_train:n_train + n_val]),
        "test": set(seqs[n_train + n_val:]),
    }
    out = {name: df[df[seq_col].isin(members)].copy() for name, members in buckets.items()}
    assert_no_leakage(out, seq_col)
    return out


def assert_no_leakage(splits: dict[str, pd.DataFrame], seq_col: str = "normalized_sequence") -> None:
    """Hard assertion that no sequence appears in more than one split."""
    names = list(splits)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            overlap = set(splits[a][seq_col]) & set(splits[b][seq_col])
            if overlap:
                raise RowLevelSplitError(
                    f"leakage: {len(overlap)} sequence(s) in both {a!r} and {b!r}, "
                    f"e.g. {sorted(overlap)[:3]}"
                )


def collapse_labels(df: pd.DataFrame, seq_col: str, label_col: str, rule: str = "majority") -> pd.DataFrame:
    """Collapse many measurements of one sequence into a single label.

    'majority' (default) is the honest choice: a peptide called active in most of its
    measurements is active, ties break active. 'any' is optimistic and inflates the
    positive class; it exists only for sensitivity checks.
    """
    g = df.groupby(seq_col)[label_col]
    if rule == "majority":
        collapsed = (g.mean() >= 0.5).astype(int)
    elif rule == "any":
        collapsed = g.max().astype(int)
    else:
        raise ValueError(f"unknown rule {rule!r}")
    return collapsed.rename(label_col).reset_index()
