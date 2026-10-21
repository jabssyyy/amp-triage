# Handoff — start here

Written 21 October 2026. This is the entry point for anyone joining the project. It covers
what PharmaMind is, how to get it running from a fresh clone, and the rules worth knowing
before you change anything.

Two other documents matter more than the rest:

- **`docs/06-build-status.md`** — measured results and current state. Where any document
  disagrees with it, it wins.
- **`docs/04-handoff.md`** — the API contracts and file-ownership boundaries. Written as a
  build brief during the hackathon, so its deadlines are historical, but the endpoint
  shapes and the "do not touch" list still hold.

---

## What this is

PharmaMind ranks antimicrobial peptides against WHO-priority drug-resistant bacteria, then
selects a diverse, low-toxicity batch that fits a fixed testing budget. Built for Tech
Sangamam 2026, where it placed **4th of 78** with a special award. The hackathon is over
and the project is being kept.

The problem is not prediction accuracy, it is **selection under cost**. A lab can generate
thousands of candidates computationally but synthesise only about twenty per round. Taking
the top twenty scorers spends that budget on near-duplicates of one chemotype, and ignores
that toxicity, not weak killing, is why active AMPs fail.

PharmaMind mapping — disease = drug-resistant bacterial infection (AMR), biological target =
WHO-priority pathogen, compound = antimicrobial peptide.

## How it works

1. **ESM2** (`esm2_t12_35M_UR50D`) embeds each peptide sequence into 480 dimensions.
2. **XGBoost** classifiers, depth 4, predict `P(active)` per species and `P(toxic)` to human
   red blood cells.
3. Each peptide gets a quality score `q_i = P(active) × (1 − P(toxic))`, raised to a tunable
   `theta` (1.0 = neutral, below 1 favours diversity, above 1 favours quality).
4. Greedy selection maximises

       log det(L_A) = 2 · Σ log(q_i) + log det(S_A)

   quality plus diversity, under a cardinality budget k. Similarity `S_ij = ⟨e_i, e_j⟩` is
   computed on ReLU'd, L2-normalised embeddings (the SubMo-GNN convention — skipping the
   normalisation silently breaks diversity). Regularised with +I so monotonicity and
   submodularity hold unconditionally.

Greedy achieves 1 − 1/e of optimal **with respect to the log-determinant objective**. That
is not "63% of optimal diversity", and the distinction is the kind of thing a rigorous
reviewer probes.

**The genuinely reusable piece is `src/select.py`.** Diversity-aware batch selection under a
budget applies to any screening problem where testing costs money and candidates cluster.
That module does not know it is about peptides.

---

## Setting up a fresh clone

    git clone https://github.com/jabssyyy/amp-triage.git
    cd amp-triage
    pip install -r requirements.txt
    cd frontend && npm install && cd ..

Then two steps that are **not** in the repository and must be run locally:

    python src/embed.py     # ESM2 embeddings, ~75 s, writes data/processed/embeddings.npz
    python src/seed.py      # your own database, lab and demo logins

`embeddings.npz` is 28 MB and regenerates, so it is not committed — but nothing scores
without it. `src/seed.py` creates your own SQLite database and JWT signing key; neither is
shared, because a published signing key lets anyone forge a login.

Run it, two terminals:

    cd src && python -m uvicorn api:app --port 8000
    cd frontend && npm run dev            # http://localhost:5173

Demo logins printed by `seed.py`: `elena.rostova@amr-unit.org` / `ElenaDemo2026!` (lead),
plus `marcus.chen@` and `priya.patel@` on the same pattern.

**Verify before and after any change — these are the contract, keep them green:**

    python src/verify_phase0.py     # 34 checks
    python src/verify_phase23.py    # 24 checks

If either fails, stop and fix that first.

---

## Repository rules

- Repo: **github.com/jabssyyy/amp-triage**, private, sole author `jabssyyy`.
- **No AI-tool attribution anywhere** — no co-author trailers, no tool names in code,
  comments, commit messages or docs. The two original workstreams are referred to as the
  *engine track* and the *product track*.
- **`data/` is committed** (changed 18 October 2026, so collaborators can run the project
  without sourcing the databases themselves). DBAASP permits redistribution with
  acknowledgement and DRAMP is CC-BY. `NOTICE.md` carries the attribution that makes this
  permitted — keep it accurate, and cite the original databases rather than this repository.
- **Never commit** `data/.jwt_secret` or `data/pharmamind.db*`. The first is a per-install
  signing key, the second holds real accounts and bcrypt password hashes. Also excluded
  because they regenerate: `embeddings.npz`, the `*_normalized.pkl` intermediates and the
  cached PDB files in `data/structures/`.

## Two claims that must stay precisely worded

**Coverage, not hit count.** Do not say the tool finds more hits than a top-N sort. Across
five species and three seeds raw hit count is a wash — expected, because raw hit count is
exactly what a top-N sort optimises. What holds up is coverage: top-N reached exactly one
chemotype in all fifteen runs, and greedy never lost a run. Say **"the same number of hits
spread across four scaffolds instead of one"** — four independent leads for the same money.
Reported openly: greedy picks slightly more toxic candidates (mean P(toxic) 0.076 vs 0.043).

**Recalibrates, does not learn.** With 20–100 wet-lab outcomes you can recalibrate and you
can exclude. You cannot retrain ESM2 or move an XGBoost classifier trained on 845 sequences.

---

## State

Phases 0–9 complete and verified: engine, validation, API, React UI, database,
authentication, campaigns, institutional memory and calibration analytics.

| | |
|---|---|
| API endpoints | 11 science + 20 platform across `src/routes/` |
| UI screens | 12 — Overview, Shortlist, Run History, Candidate, Compare, What-if Lab, Evidence, Relationships, Calibration & Trends, Model & Validation, Login, Campaigns |
| Database tables | 11, schema frozen in `src/models_db.py` |
| Verification | 58 checks across two suites, all passing |

Model performance, from `reports/activity_metrics.json`:

| Species | CV ROC-AUC | test ROC-AUC | confidence |
|---|---|---|---|
| E. coli | 0.817 ± 0.032 | 0.797 | high |
| P. aeruginosa | 0.818 ± 0.033 | 0.812 | high |
| S. aureus | 0.732 ± 0.028 | 0.795 | high |
| K. pneumoniae | 0.746 ± 0.053 | 0.805 | moderate |
| **A. baumannii** | **0.586 ± 0.112** | 0.722 | **low** |
| Toxicity (human RBC) | 0.849 ± 0.052 | 0.849 | — |

CV and test agree throughout, so nothing is overfit to the split. *A. baumannii* is barely
above chance with error bars crossing it, and carries a visible low-confidence marker in the
UI. Read `confidence` from the metrics file; never hardcode it.

`src/app.py` is a deliberate stub — a Streamlit fallback that was skipped.

## Data handling rules

Each of these silently corrupts the labels if you get it wrong, and the numbers will still
look plausible. Full rationale in `docs/06-build-status.md`.

1. **Never drop censored measurements.** 2,533 activity rows read `>100`, `>256` and similar,
   plus 1,328 ranges. Those `>X` rows *are* the inactive class. A naive
   `to_numeric().dropna()` deletes ~3,900 rows and swings the balance from ~62/38 to ~90/10.
2. **The lysis table is (effect level, dose), not (dose, percent).** `Activity Measure for
   Lysis` holds `50% Hemolysis`; `Peptide Concentration` holds the dose that produced it. The
   toxicity label is dose-anchored, not a percentage cut.
3. **Filter to the standard twenty amino acids before embedding.** 1,265 of 11,433 master
   sequences are branched or carry non-standard residues; ESM2 cannot embed them.
4. **Split by `normalized_sequence`, never by row.** Enforced by `peptides.sequence_split`.
5. **`has_dramp_toxicity_annotation` is not a toxicity label.** It only means the DRAMP field
   is non-empty, and it often literally reads "no information found".
6. **`PDB_ID` is mostly not a PDB id.** 3,855 of 4,310 non-empty DRAMP values are the string
   "Not available". Only 434 sequences have a real experimental structure (~4%) — do not
   quote the earlier 26% figure, which counted those rows.
7. **Units are mixed and the CSVs are not clean UTF-8.** Match units by substring, convert µM
   to µg/ml using molecular weight computed from the sequence.
8. **ReLU + L2 normalise embeddings before the selection kernel, never for the classifiers.**
9. **Small ESM2 only, never 3B.**
10. **No science in the frontend.** Every number displayed comes from an API endpoint. If you
    find yourself writing a determinant, a similarity score or a probability fusion in
    TypeScript, you have taken a wrong turn.

---

## Where things live

    docs/            documentation; 06-build-status.md is the source of truth
    src/             pipeline, API, verification
      config.py        locked thresholds and paths, each with its justification
      peptides.py      parsing, units, sequence filtering, leakage-safe splitting
      make_labels.py   labels + the blocking class-balance gate
      embed.py         ESM2 embeddings
      train_*.py       the six classifiers
      score.py         P(active), P(toxic) for one sequence
      select.py        the log-det greedy engine — VERIFIED, do not change signatures
      validate.py      hidden-actives recovery benchmark
      scientist.py     wheel, properties, PubMed evidence, graph, structures
      models_db.py     the frozen 11-table schema
      routes/          auth, projects, runs, experiments, analytics
      verify_phase*.py the two contract suites
    frontend/        React 19 + Vite + Tailwind; one file per screen under src/pages/
    models/          trained classifiers
    reports/         metrics, validation output, UI screenshots
    design/template/ the design source the UI was built from
    data/            source databases, labels and processed tables

## What is worth doing next

Nothing is urgent. In rough order of value:

1. **The two data-limited models.** *A. baumannii* sits at CV ROC-AUC 0.586 ± 0.112 on 90
   training sequences; toxicity rests on 231. Both are limited by labelled data, not by
   method, so more peptides would move them and more modelling would not. This is the first
   thing worth fixing for real use.
2. **Streamlit fallback.** `src/app.py` is still a stub — cheap insurance before demoing on
   an unfamiliar machine.
3. **Phase 10**, per-project recalibration from wet-lab results, is designed in
   `docs/07-system-design.md` and was never started.

Logged as stretch from the beginning and never started: per-residue toxicity attribution
(Expected Gradients) and log-MIC regression for the data-rich species.

## Reading order

1. `docs/01-context.md` — project brief, locked decisions, how we got here
2. `docs/02-research-findings.md` — verified numbers, method maths, references
3. `docs/03-plan.md` — the phased build plan (historical)
4. `docs/04-handoff.md` — API contracts and file-ownership boundaries
5. `docs/05-dataset-report.md` — original schema inspection
6. **`docs/06-build-status.md`** — what exists and what it measured; this one wins
7. `docs/07-system-design.md` — the multi-user platform design (historical)
8. `docs/08-data-setup.md` — rebuilding the data from the originals
