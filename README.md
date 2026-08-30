# PharmaMind — AMP Triage

**Tech Sangamam 2026.** An AI research assistant for antimicrobial drug discovery. It ranks
candidate compounds against drug-resistant pathogens, grounds every prediction in published
evidence, surfaces similar known compounds, and lets researchers explore what-if
hypotheses. A research-support tool, not a medical decision-maker.

PharmaMind mapping — **disease** = drug-resistant bacterial infection (AMR), **biological
target** = WHO-priority pathogen, **compound** = antimicrobial peptide.

The bottleneck is not prediction accuracy, it is selection under cost. A lab can generate
thousands of candidates computationally but only synthesise about twenty per round. Taking
the top scorers wastes that budget on near-duplicates and ignores that toxicity, not weak
killing, is why active AMPs fail. This tool produces a diverse, selectivity-aware shortlist
instead.

> **Starting fresh?** Read **`docs/06-build-status.md`** first. It opens with a handoff
> block covering current state, how to run it, the repository rules, and the two claims
> that must be phrased precisely. It is the source of truth where any doc disagrees.

---

## Run it

Two terminals.

    cd src && python -m uvicorn api:app --port 8000
    cd frontend && npm run dev            # http://localhost:5173

Verify the engine at any time — these are the contract, keep them green:

    python src/verify_phase0.py     # 34 checks
    python src/verify_phase23.py    # 24 checks

First-time setup:

    pip install -r requirements.txt
    cd frontend && npm install

The source databases are not redistributed here — they belong to DBAASP and DRAMP (see
`NOTICE.md`). **`docs/08-data-setup.md` explains how to fetch them and rebuild the labels,
embeddings and models.** Budget a few minutes; the embedding step takes about 75 seconds.

---

## The objective

    log det(L_A) = 2 · Σ log(q_i) + log det(S_A)

Quality plus diversity, maximised greedily under a cardinality budget k. Greedy achieves
1 − 1/e of optimal **with respect to the log-determinant objective** — not "63% of optimal
diversity". Regularised with +I so monotonicity and submodularity hold unconditionally.

- `q_i = P(active) × (1 − P(toxic))`, raised to a tunable `theta` (1.0 = neutral).
- `S_ij = ⟨e_i, e_j⟩` on ReLU'd, L2-normalised ESM2 embeddings (SubMo-GNN convention —
  skipping the normalisation silently breaks diversity).
- Both predictors are binary XGBoost classifiers over small ESM2 embeddings.

---

## Layout

    docs/            project documentation, read in order
    src/             pipeline, API, verification
    frontend/        React + Vite UI
    models/          trained classifiers
    reports/         metrics, validation output, UI screenshots
    design/template/ the design source the UI was built from
    data/            NOT in the repository — see docs/08-data-setup.md

### src

    config.py        locked thresholds and paths, each with its justification
    peptides.py      parsing, units, sequence filtering, leakage-safe splitting
    make_labels.py   phase 1 — labels + class-balance gate
    embed.py         phase 2 — ESM2 embeddings
    train_*.py       phase 2 — classifiers
    score.py         phase 2 — P(active), P(toxic) for one sequence
    select.py        phase 3 — q_i and log-det greedy selection
    validate.py      phase 4 — hidden-actives recovery vs top-N
    scientist.py     phase 5 — wheel, properties, evidence, graph, structures
    api.py           FastAPI layer the frontend calls
    audit_validation.py  independent re-check of the validation harness
    verify_phase*.py the two contract suites

---

## Documentation

Read in order:

1. `docs/01-context.md` — project brief, locked decisions, how we got here
2. `docs/02-research-findings.md` — verified numbers, method maths, references
3. `docs/03-plan.md` — the phased build plan
4. `docs/04-handoff.md` — contracts and rules for anyone extending the code
5. `docs/05-dataset-report.md` — original schema inspection
6. **`docs/06-build-status.md`** — what actually exists and what it measured. Where any
   other document disagrees with this one, this one wins.
7. `docs/07-system-design.md` — the multi-user platform design
8. `docs/08-data-setup.md` — how to obtain the source data and rebuild everything

---

## Data handling rules (violating any of these corrupts the labels)

1. **Never drop censored measurements.** 2,533 activity rows read `>100`, `>256` etc and
   1,328 more are ranges. Those `>X` rows *are* the inactive class. A naive
   `to_numeric().dropna()` deletes ~3,900 rows and swings the balance from ~62/38 to ~90/10.
2. **The lysis table is (effect level, dose), not (dose, percent).** `Activity Measure for
   Lysis` holds `50% Hemolysis`; `Peptide Concentration` holds the dose that produced it.
   The toxicity label is therefore dose-anchored, not a percentage cut.
3. **Filter to standard amino acids before embedding.** 1,265 of 11,433 master sequences are
   branched or contain non-standard residues; ESM2 cannot embed them.
4. **Split by `normalized_sequence`, never by row.** Enforced by `peptides.sequence_split`.
5. **`has_dramp_toxicity_annotation` is not a toxicity label.** It only means the DRAMP field
   is non-empty, and it often literally reads "no information found".
6. **`PDB_ID` is mostly not a PDB ID.** 3,855 of 4,310 non-empty values are the string
   "Not available". Only 434 sequences have a real experimental structure.
7. **Units are mixed and the CSVs are not clean UTF-8.** Match units by substring, convert
   µM to µg/ml using molecular weight computed from the sequence.
8. **No science in the frontend.** Every number displayed comes from an API endpoint.

---
