# Handoff — start here

Written 21 October 2026, merging the original phase-4/5 contracts brief into one document.
This is the entry point for anyone joining the project: what PharmaMind is, how to get it
running from a fresh clone, the contracts that hold, and the rules worth knowing before you
change anything.

**`docs/06-build-status.md`** carries the measured results and current state. Where it and
this file disagree, it wins.

---

## What this is

PharmaMind ranks antimicrobial peptides against WHO-priority drug-resistant bacteria, then
selects a diverse, low-toxicity batch that fits a fixed testing budget. Built for Tech
Sangamam 2026, where it placed **4th of 78** with a special award. The hackathon is over and
the project is being kept.

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
is not "63% of optimal diversity" — exponentiating an additive bound gives an exponentially
weak multiplicative one, and the distinction is exactly what a rigorous reviewer probes.

**The genuinely reusable piece is `src/select.py`.** Diversity-aware batch selection under a
budget applies to any screening problem where testing costs money and candidates cluster.
That module does not know it is about peptides.

---

## Setting up a fresh clone

A deployed instance runs at **https://nebula.viewdns.net/pharmamind**, so you only need a
local setup to develop against.

    git clone https://github.com/jabssyyy/amp-triage.git
    cd amp-triage
    pip install -r requirements.txt
    cd frontend && npm install && cd ..

**`data/` is not in the repository**, so a fresh clone cannot score anything until you
rebuild it. `docs/08-data-setup.md` is the full procedure: download the three source files
from DBAASP and DRAMP into `data/raw/`, clean them into `data/processed/`, then

    python src/make_labels.py   # labels + the blocking class-balance gate
    python src/embed.py         # ESM2 embeddings, ~75 s, writes embeddings.npz
    python src/train_activity.py && python src/train_toxicity.py
    python src/seed.py          # your own database, lab and demo logins

`src/seed.py` creates your own SQLite database and JWT signing key. Neither is shared —
a published signing key lets anyone forge a login.

Run it, two terminals:

    cd src && python -m uvicorn api:app --port 8000
    cd frontend && npm run dev            # http://localhost:5173

Demo logins, created and printed by `python src/seed.py`: `elena.rostova@amr-unit.org` /
`ElenaDemo2026!` (lead), plus `marcus.chen@` and `priya.patel@` on the same pattern. These
are intentionally public — they are hardcoded in `src/seed.py` and wired into
`frontend/src/pages/Login.tsx` as one-click demo buttons, so the demo is reproducible by
anyone.

**That is fine for a demo and not fine for real data.** Anyone who can reach a deployment
can sign in as a lead and write to it. If a deployment ever holds real lab results, remove
the quick-login buttons, drop the seeded accounts (`experiment.source` marks seeded records)
and issue real credentials.

**Verify before and after any change — these are the contract, keep them green:**

    python src/verify_phase0.py     # 34 checks
    python src/verify_phase23.py    # 24 checks

If either fails, stop and fix that before continuing.

---

## Repository rules

- Repo: **github.com/jabssyyy/amp-triage**, public, sole author `jabssyyy`. Deployed at
  https://nebula.viewdns.net/pharmamind.
- **No AI-tool attribution anywhere** — no co-author trailers, no tool names in code,
  comments, commit messages or docs. The two original workstreams are referred to as the
  *engine track* and the *product track*.
- **`data/` is local only and not committed.** It was briefly committed while the repo was
  private (18–23 October 2026) so collaborators could get the deployment running; with that
  done and the repo public, it is out again. `docs/08-data-setup.md` rebuilds it from the
  originals, and `NOTICE.md` credits DBAASP and DRAMP — cite them, not this repository.
- **`data/.jwt_secret` and `data/pharmamind.db*` must never be committed** under any
  relaxation of the rule above. The first is a per-install JWT signing key: publishing it
  lets anyone forge a login. The second holds real accounts and bcrypt password hashes.

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

---

## The one rule that matters most

**Do not reimplement any of the science in TypeScript.** The scoring, the `q_i` formula, the
log-determinant greedy selection, the embedding normalisation — all of it is Python, all of
it is verified against brute force, and all of it stays in Python. The frontend calls an API.
It does not do math.

If you find yourself writing a determinant, a softmax, a similarity score or a probability
fusion in JavaScript, you have taken a wrong turn.

    React (frontend/)  ->  FastAPI (src/api.py)  ->  score.py / select.py / validate.py

**Verify the API against the CLI.** For the same input, `POST /score` must return exactly
what `python src/score.py --sequence ... --species ...` prints. If they disagree, the API is
wrong, not the CLI.

## Endpoint contracts

These mirror the locked Python signatures. **Do not change field names.**

    POST /score
      body     {"sequence": "GIGKFLHSAKK...", "species": "Escherichia coli"}
      returns  {"sequence", "species", "p_active", "p_toxic", "q", "cached"}
      errors   400 if the sequence has non-standard residues or is shorter than 5,
               400 if the species is not one of the five trained ones

    POST /shortlist
      body     {"sequences": [...], "species": "...", "k": 20, "theta": 1.0}
      returns  {"logdet": float, "theta": float,
                "items": [{"rank", "sequence", "q_i", "q_i_scaled", "p_active", "p_toxic",
                           "marginal_log_gain", "similarity_to_nearest_selected"}],
                "baseline_top_n": ["...sequences in plain score order..."]}

      Display `q_i`, never `q_i_scaled`. q_i is the raw P(active) * (1 - P(toxic)) and reads
      as "probability of being both active and safe". q_i_scaled is q_i ** theta, an internal
      detail of the objective -- at theta=5 it renders as a tiny number and users read that
      as a bug. Both are returned so the math stays inspectable.

    POST /validate
      body     {"species": "...", "k": 20, "n_hidden": 50}
      returns  {"greedy_recovered": int, "topn_recovered": int, "n_hidden": int, "k": int}

    GET /species
      returns  [{"name", "n_train", "cv_roc_auc", "cv_roc_auc_std", "confidence"}]
      confidence is "high" | "moderate" | "low" -- read it from reports/activity_metrics.json,
      do not hardcode.

The remaining science endpoints are `/properties`, `/wheel`, `/compare`, `/evidence`,
`/graph`, `/structure` and `/structure/compare`. All eleven **stay callable without a token**
— auth is additive and gates only the persistence endpoints. There is a verified working
demo depending on this. Use `get_current_user` as a dependency, and
`get_current_user_optional` where an endpoint behaves differently when signed in.

**Startup.** ESM2 loads lazily on the first uncached sequence and costs ~1.6 s once. It is
warmed at API startup so no user request pays it. Cached sequences score in 0.3 ms; a live
what-if sequence scores in ~37 ms once warm.

## What must appear in the UI

**Per-species confidence, visibly.** Not all five models are equally good — see the table
above. *A. baumannii* must carry a visible low-confidence marker. Hiding that is the kind of
thing a rigorous reviewer finds and punishes; showing it earns credit.

**`similarity_to_nearest_selected` per row.** This is the number the selector actually used
to decide two peptides were different. It answers "why both and not two copies of the better
one" — the single most likely question about the ranking.

**θ as a live control.** Moving it re-ranks. Measured on a 300-peptide pool against E. coli
at k=20, the knob is real, not decorative:

| θ | mean raw q of picks | mean similarity to nearest selected | overlap with top-N |
|---|---|---|---|
| 0.2 | 0.641 | 0.872 | 5/20 |
| 0.5 | 0.744 | 0.886 | 10/20 |
| 1.0 | 0.818 | 0.917 | 14/20 |
| 2.0 | 0.850 | 0.943 | 17/20 |
| 5.0 | 0.864 | 0.961 | 19/20 |

Quality rises and diversity falls monotonically, and at high θ the selection converges to
plain top-N — the correct limiting behaviour, and worth saying out loud: top-N is not a
different algorithm, it is our objective with diversity switched off.

**Structure prediction stays marked low-confidence.** ESMFold is unreliable on short peptides
and many AMPs are disordered until they contact a membrane. The experimental tier (434
sequences, ~4%) and the predicted tier are labelled distinctly, and RMSD is refused when
either structure is predicted.

---

## Data handling rules

Each of these silently corrupts the labels if you get it wrong, and the numbers will still
look plausible. Full rationale in `docs/06-build-status.md`; implementation in
`src/peptides.py`.

1. **Never drop censored measurements.** 2,533 activity rows read `>100`, `>256` and similar,
   plus 1,328 ranges. Those `>X` rows *are* the inactive class. A naive
   `to_numeric().dropna()` deletes ~3,900 rows and swings the balance from ~62/38 to ~90/10.
2. **The lysis table is (effect level, dose), not (dose, percent).** `Activity Measure for
   Lysis` holds `50% Hemolysis`; `Peptide Concentration` holds the dose that produced it. The
   toxicity label is dose-anchored, not a percentage cut.
3. **Filter to the standard twenty amino acids before embedding.** 1,265 of 11,433 master
   sequences are branched or carry non-standard residues; ESM2 cannot embed them.
4. **Split by `normalized_sequence`, never by row.** Enforced by `peptides.sequence_split`.
   Hidden actives for validation must come from the held-out **test** split
   (`data/labels/activity_<species>_test.parquet`) — drawing them from training data is
   leakage dressed up as a finding.
5. **`has_dramp_toxicity_annotation` is not a toxicity label.** It only means the DRAMP field
   is non-empty, and it often literally reads "no information found".
6. **`PDB_ID` is mostly not a PDB id.** 3,855 of 4,310 non-empty DRAMP values are the string
   "Not available". Only 434 sequences have a real experimental structure — do not quote the
   earlier 26% figure, which counted those rows.
7. **Units are mixed and the CSVs are not clean UTF-8.** Match units by substring, convert µM
   to µg/ml using molecular weight computed from the sequence.
8. **ReLU + L2 normalise embeddings before the selection kernel, never for the classifiers.**
9. **Small ESM2 only, never 3B.**

## Files that are locked

Verified, with contracts resting on their signatures. Changing them invalidates the 58
checks:

    src/select.py      the log-det greedy engine — do not change signatures
    src/score.py       P(active), P(toxic) for one sequence
    src/peptides.py    parsing, units, filtering, leakage-safe splitting
    src/embed.py  src/train_*.py
    src/db.py  src/models_db.py  src/schemas.py    the frozen 11-table schema

`frontend/src/api.ts` is append-only: add new call signatures, change nothing existing.

## Language for the pitch

Name the state of the art (CAMPR4, AI4AMP, dbAMP, AmpLyze) and position honestly as
integration plus a selectivity-first objective, validated. **Never world-first.** Report
results honestly even where the margin is modest — a small real number is worth more than a
large fake one, and a reviewer is likelier to probe a suspiciously large gap.

Calibration honesty rule, already enforced: a calibration bucket with fewer than three
results returns `observed_hit_rate: null`, not a number. Two experiments is not a hit rate.

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
      select.py        the log-det greedy engine
      validate.py      hidden-actives recovery benchmark
      audit_validation.py  independent re-check of that benchmark
      scientist.py     wheel, properties, PubMed evidence, graph, structures
      models_db.py     the frozen 11-table schema
      routes/          auth, projects, runs, experiments, analytics
      verify_phase*.py the two contract suites
    frontend/        React 19 + Vite + Tailwind; one file per screen under src/pages/
                     store.tsx holds species, pool, shortlist, tray, auth, lab memory
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

## Demo script that works

Verified end to end:

1. **Shortlist** — drag θ and watch the table re-rank. Proves the diversity term is real.
2. **Candidate** — helical wheel and 3D structure with its tier and confidence labelled.
3. **What-if Lab** — edit a residue, watch it re-score in ~40 ms and change rank.
4. **Record a result** on the current rank-1 peptide, then re-run the shortlist. It
   disappears and the panel says why. This is the institutional-memory moment and it needs no
   pre-seeded state.
5. **Model & Validation** — close on the chemotype numbers and the *A. baumannii*
   low-confidence badge. Volunteering the weak model is the strongest move available.

## Reading order

1. `docs/01-context.md` — project brief, locked decisions, how we got here
2. `docs/02-research-findings.md` — verified numbers, method maths, references
3. `docs/03-plan.md` — the phased build plan (historical)
4. `docs/05-dataset-report.md` — original schema inspection
5. **`docs/06-build-status.md`** — what exists and what it measured; this one wins
6. `docs/07-system-design.md` — the multi-user platform design (historical)
7. `docs/08-data-setup.md` — rebuilding the data from the originals
