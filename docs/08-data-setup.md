# Data setup

The source databases are not in this repository. They belong to DBAASP and DRAMP (see
`NOTICE.md`), they are large, and mirroring someone else's dataset is not part of what this
project built. Everything below rebuilds from the originals in a few minutes.

A fresh clone has no `data/` directory and cannot score anything until you work through all
three steps.

## 1. Download the sources

Place these under `data/raw/`:

| File | Source |
|---|---|
| `activity-against-target-species.csv` | DBAASP export — https://dbaasp.org (or the REST API at `dbaasp.org/api/v1`) |
| `hemolytic-and-cytotoxic-activities.csv` | DBAASP export, haemolysis and cytotoxicity |
| `general_amps.xlsx` | DRAMP 4.0 — http://dramp.cpu-bioinfor.org (one-click download, CC-BY) |

DRAMP is a direct download. DBAASP needs either a site export or the API; the activity
table is the one holding MIC and MBC by target species.

## 2. Clean into the processed tables

The cleaning step produces one row per measurement, preserving the experimental detail the
labelling rules depend on:

    data/processed/peptide_master.csv                 one row per unique sequence
    data/processed/dbaasp_activity_experimental.csv   MIC/MBC by target species
    data/processed/dbaasp_lysis_experimental.csv      haemolysis dose-response points
    data/processed/dramp_toxicity_experimental.csv    DRAMP annotations
    data/processed/sequence_pdb_map.json              sequence to experimental PDB id
    data/processed/sequence_name_map.json             sequence to peptide name

Each needs a `normalized_sequence` column: the sequence trimmed and upper-cased.

## 3. Build labels, embeddings and models

    python src/make_labels.py     # labels + the blocking class-balance gate
    python src/embed.py           # ESM2 embeddings, ~75 s, writes embeddings.npz
    python src/train_activity.py  # five per-species activity classifiers
    python src/train_toxicity.py  # human-erythrocyte toxicity classifier
    python src/seed.py            # your own database, lab and demo logins

The trained classifiers in `models/` **are** committed, so steps 3c and 3d only matter if
you change the labelling rules or the training data. `embeddings.npz` is not committed and
nothing scores without it, so `embed.py` is never optional.

Then confirm the engine is intact:

    python src/verify_phase0.py    # 34 checks
    python src/verify_phase23.py   # 24 checks

## Four rules the rebuild must respect

These are not stylistic. Getting any of them wrong silently corrupts the labels, and the
numbers will still look plausible.

1. **Never drop censored measurements.** 2,533 activity rows read `>100`, `>256` and
   similar; 1,328 more are ranges. Those `>X` rows *are* the inactive class. A naive
   `to_numeric().dropna()` deletes about 3,900 rows and swings the balance from ~62/38 to
   ~90/10.
2. **The lysis table is (effect level, dose), not (dose, percent).** `Activity Measure for
   Lysis` holds `50% Hemolysis`; `Peptide Concentration` holds the dose that produced it.
   The toxicity label is therefore dose-anchored.
3. **Filter to the standard twenty amino acids before embedding.** 1,265 of 11,433 master
   sequences are branched or carry non-standard residues; ESM2 cannot embed them.
4. **`PDB_ID` is mostly not a PDB id.** 3,855 of 4,310 non-empty values in DRAMP are the
   literal string "Not available". Only 434 sequences have a real experimental structure.

Full rationale, with the measured numbers, is in `docs/06-build-status.md`.
