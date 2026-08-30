# Build Plan — Tech Sangamam 2026 (AMP / PharmaMind)

Execution guide for the engine track. Read context.md first for locked decisions; research_findings.md for numbers and math. This file is the phased what-to-build-next.

Last updated: 29 August 2026, ~00:30 Day 2.
STATUS: phases 0-9 COMPLETE and reviewed. Phase 10 is designed and did not land — full design in docs/07-system-design.md. Measured results live in docs/06-build-status.md.
This file is kept as the record of what was planned and how it changed on contact with the
data — the phase headings below carry their outcome inline.
Owner: Sir Jabin + build partner (this pair). Data pair runs parallel on labeling and QC.

---

## Schedule and target for each phase

- Round 1 — ideation + workflow. DONE.
- Round 2 (next checkpoint) — show work structure AND a basic working product. Phases 0 through 3 must be running for this.
- Round 3 (final) — full demo including scientist UX. Phases 4 and 5.

Design principle: graceful degradation. Each phase must leave the system in a demoable state. If the next phase never lands, the previous one still stands as a complete, honest demo.

---

## Phase 0 — repo skeleton and data landing — DONE (34 checks pass)

Goal: a clean repo the team can push to; cleaned CSVs sit where the code expects them.

- Create repo layout:
  - `data/raw/` (untouched source dumps), `data/processed/` (the four cleaned CSVs from the data pair), `data/labels/` (train tables written by phase 1)
  - `src/` — `embed.py`, `train_activity.py`, `train_toxicity.py`, `score.py`, `select.py`, `validate.py`, `app.py`
  - `notebooks/` — quick EDA + class-balance check
  - `models/` — saved classifier artifacts
  - `reports/` — validation outputs
- Drop the four cleaned CSVs into `data/processed/`: `peptide_master.csv`, `dbaasp_activity_experimental.csv`, `dbaasp_lysis_experimental.csv`, `dramp_toxicity_experimental.csv` (DRAMP toxicity NOT used as a label, see context Decision-1 traps).
- Environment: Python 3.10+, `torch`, `fair-esm`, `xgboost` (or `lightgbm`), `scikit-learn`, `pandas`, `numpy`, `streamlit`, `faiss-cpu`, `biopython` (for helical-wheel math later).
- README stub: one-paragraph pitch, mapping to PharmaMind (disease = AMR, target = WHO pathogen, compound = AMP), and the framing sentence from context.md.

Exit criteria: `python -c "import torch, esm, xgboost, sklearn, pandas"` runs; CSVs are readable; sequence-level split function stub exists and refuses to split by row.

---

## Phase 1 — labels and class-balance gate — DONE (gate passed, 6 label sets)

Blocking gate before any model trains. Do this even if the data pair is doing it in parallel; verify.

- Activity labels: filter DBAASP activity to `Activity Measure in {MIC, MBC}`; harmonize units (µg/ml → µM via molecular weight computed from sequence); drop 111 sequence-less rows; collapse (sequence, species) duplicates by median log-MIC. Apply threshold (candidate: MIC ≤ 32 µg/ml equivalent) to make a binary `active` per (sequence, species). Restrict initial modeling to WHO-priority species with at least ~50 measurements after collapse (candidates: E. coli, S. aureus, P. aeruginosa; check counts, drop any that starve).
- Toxicity labels: from DBAASP lysis only, target cell = human erythrocytes, keep hemolysis-% measurements at a chosen reference concentration band (e.g. 25–100 µM window; document exact choice). Threshold hemolysis-% to a binary `toxic` label.
- CLASS-BALANCE HISTOGRAM (mandatory before locking thresholds): plot the resulting active/inactive and toxic/safe proportions per species. If any label is >85/15 lopsided, revise the threshold or use a binned label instead of a single cut. Record the final threshold and cite the source (breakpoint reference or dataset convention).
- Anti-leakage: split by `normalized_sequence`, not by row. Write `train.parquet`, `val.parquet`, `test.parquet` for each of activity (per species) and toxicity.

Exit criteria: label distributions are printed and sane; all splits pass a leakage assertion (no sequence appears in more than one split); threshold values are written to `data/labels/label_config.json` with their justification.

---

## Phase 2 — embeddings + classifiers — DONE (10,065 embedded, 6 models)

- ESM2 embeddings: use `esm2_t12_35M_UR50D` (small, CPU-friendly) or `esm2_t30_150M_UR50D` if time and hardware permit. Batch-embed every unique sequence in `peptide_master.csv`, mean-pool over residues to a single vector per sequence, cache to `data/processed/embeddings.npy` keyed by normalized_sequence. NOT ESM2-3B (see research_findings section 4).
- Post-embedding normalization for the SELECTION engine only (phase 3): ReLU then L2 unit-normalize (SubMo-GNN convention, research_findings section 1). Keep two copies: raw for classifiers, normalized for the selection kernel.
- Activity classifier: one XGBoost binary classifier per priority species; features = raw ESM2 embedding; target = `active` label. 5-fold sequence-aware CV; report ROC-AUC and PR-AUC per species.
- Toxicity classifier: one XGBoost binary classifier on the ~717-sequence dual set; same features; target = `toxic`. Same CV protocol.
- Save models as `models/activity_<species>.pkl` and `models/toxicity_human_rbc.pkl`.

Exit criteria: `score.py --sequence X --species Y` returns `{P_active, P_toxic}` in under a second. Cross-val metrics recorded in `reports/model_metrics.md`.

---

## Phase 3 — q_i and selection engine — DONE (24 checks pass, matched brute force)

- Compute q_i = P(active) × (1 - P(toxic)) per candidate for a chosen target species. Apply the θ knob: `q_i_scaled = q_i ** theta`, default `theta = 1.0`, exposed as a CLI/UI knob.
- Similarity kernel S: `S_ij = <e_i, e_j>` on the L2-normalized ReLU'd embeddings.
- Log-det greedy selection under cardinality budget k (default k=20):
  - Marginal-gain greedy on `log det(L_A + I)` where `L_ij = q_i * S_ij * q_j`.
  - Use rank-1 Cholesky update per pick (do not recompute the full det each step; O(n·k²) not O(n·k⁴)).
  - Reference impl to mirror: SubMo-GNN's DPP-greedy loop, research_findings section 6.
- Deterministic tie-break by q_i descending.

Exit criteria: `select.py --pool candidates.csv --species E_coli --k 20 --theta 1.0` outputs a ranked shortlist CSV. The five most-similar duplicates in a synthetic pool must NOT all appear in the top-k (proves diversity is on).

---

## Phase 4 — validation harness + API — DONE (Streamlit replaced by React, see UI plan below)

Round 2 target: this phase makes the demo real.

- Validation: hide N known actives inside the candidate pool, run selection, measure recovery-within-budget vs plain top-N. Report as one plot and one number (e.g. "greedy recovers 14/20 hidden actives at k=20 vs 9/20 for top-N"). Honest even if the number is modest.
- Streamlit app (`app.py`), 3 tabs is enough for Round 2:
  1. Score — paste a sequence, pick a species, see P(active), P(toxic), q_i.
  2. Shortlist — upload a pool CSV, set k and θ, get the ranked table with the columns q_i, P(active), P(toxic), similarity-to-nearest-selected.
  3. Validation — one button that runs the recovery-within-budget test and shows the comparison.

Exit criteria for Round 2: someone can walk up, use all three tabs on your machine, and see honest numbers. This is what you show at the "basic working product" checkpoint.

---

## Phase 5 — scientist UX and evidence layer — DONE (all endpoints live)

- Helical wheel per peptide: compute deterministically from sequence with a lightweight SVG generator; show hydrophobic vs cationic faces. Fast, safe, judge-legible (research_findings section 10). Primary structural visual.
- Side-by-side compare: two peptides, both wheels, property panel (charge, hydrophobic fraction, length), and the embedding distance number the selector actually used.
- What-if: edit a residue or type a hypothetical sequence, re-embed, re-score, re-place on the shortlist live. This is PharmaMind requirement #4.
- Evidence layer (RAG over PubMed): retrieve top-3 abstracts per shortlisted peptide (or per pathogen if peptide-specific hits are sparse), summarize with a small LLM, attach as an "evidence" pane per shortlist row. Explicitly a research-support surface, not a decision-maker.
- KG-style relationship view (cheap add): render compound - pathogen - resistance mechanism - source paper as a small graph from the RAG results. Explainability, not the engine.
- AVOID confident 3D structure prediction (AlphaFold on short peptides is unreliable, research_findings section 10). Only include as a low-confidence illustration if there is time and space.

Exit criteria for Round 3: end-to-end demo where a researcher scores, ranks, compares, edits, and reads grounded evidence — all in one app.

---

## Role split (this pair)

- **Person A — core engine.** Phase 0 setup, phase 1 labels/gate, phase 2 embeddings + classifiers, phase 3 q_i + selection, phase 4 validation harness.
- **Person B — product surface.** Streamlit app scaffold from phase 0, phase 4 UI wire-up as A finishes each piece, phase 5 helical wheel + compare + what-if + evidence layer.
- Sync points: end of phase 1 (labels frozen), end of phase 2 (score.py contract locked), end of phase 3 (select.py contract locked).

Decide who is A and who is B before the engine track starts.

---

## Non-negotiables (carry into every phase)

- Split by normalized_sequence, never by row.
- Do NOT use `has_dramp_toxicity_annotation` as a toxic label.
- Use small ESM2, never 3B.
- The 1 - 1/e guarantee is on the log-determinant objective, NOT on raw diversity. Pitch it precisely.
- Selectivity-first is via q_i = P(active) × (1 - P(toxic)), no hard toxicity filter (Decision 2, pure fold).
- All threshold choices need a cited justification and a class-balance check.
- Do not overclaim; name the SOTA (CAMPR4, AI4AMP, AmpLyze) and position honestly as integration + selectivity-first ranking.

---

## Immediate next actions (do these first in the engine track)

1. Assign A and B.
2. Person A: Phase 0 repo skeleton + verify the four CSVs load.
3. Person B: Streamlit app skeleton with the three empty tabs.
4. Both: read context.md decisions 1, 2, 3 and confirm before writing model code.

---

# UI BUILD PLAN (added 28 Aug 2026, ~9:15 PM Day 1)

Owner: the engine track (not the product track). Template: `stitch_pharmamind_research_interface/`,
a Stitch export — 8 static Tailwind pages plus `clinical_precision/DESIGN.md`, which is the
Material-3 design token source, not a page.

## Stack decision

**Vite + React + Tailwind**, porting the template's tokens verbatim.

Not vanilla JS on the static pages, despite that being faster. The app's whole value is
state that flows between screens: pick a species, build a shortlist, click into a
candidate, send two candidates to compare, edit one in the what-if lab and watch it
re-rank. Across 8 separate HTML files that means URL params and localStorage glue, which
breaks exactly when a judge starts clicking around. One SPA with shared state is the
lower-risk build even though the first hour costs more.

## Endpoint map — every page is backed by real data

| Template page | Endpoints | Status |
|---|---|---|
| experimental_shortlist | `POST /shortlist` | live |
| candidate_detail_amp_041 | `POST /score`, `/properties`, `/wheel`, `/structure`, `/evidence` | live |
| compare_candidates | `POST /compare`, `GET /structure/compare` | live |
| what_if_lab | `POST /score` (uncached embeds in ~37 ms) | live |
| scientific_evidence | `GET /evidence` | live |
| relationship_graph | `GET /graph` | live |
| model_validation | `POST /validate`, `GET /species` | live |
| research_overview | `GET /species` + derived aggregates | partial — hero counts derived, no separate source |

Nothing is faked. Any tile without a real source renders as an explicit placeholder,
never as an invented number.

## Build order

Priority is demo value, so the strongest screens exist first and the build degrades
gracefully if time runs out.

1. **Shell** — Vite scaffold, Tailwind config with the exact M3 tokens from DESIGN.md,
   API client, sidebar + top bar layout, routing, global state (species, pool, shortlist,
   compare tray).
2. **Shortlist** — the core screen. Species picker, k and theta controls, ranked table
   with q_i / P(active) / P(toxic) / similarity-to-nearest-selected. Theta must re-rank live.
3. **Candidate detail** — score panel, properties, helical wheel SVG, structure viewer
   with tier badge, evidence list.
4. **Model & validation** — the recovery and chemotype numbers, per-species confidence
   badges. A. baumannii must render its low-confidence marker.
5. **Compare** — two candidates side by side, both wheels, embedding distance, RMSD only
   when both are experimental tier.
6. **What-if lab** — edit a residue, re-score live, see it re-placed.
7. **Evidence** and **Relationship graph**.
8. **Overview** — last, because it is the least load-bearing screen.

## Non-negotiables carried into the UI

- No science in the frontend. Every number comes from an endpoint.
- Display `q_i`, never `q_i_scaled`.
- Per-species confidence badges read from `/species`; A. baumannii shows **low**.
- `similarity_to_nearest_selected` is visible on the shortlist — it is the answer to
  "why both and not two copies of the better one".
- Structure tier badge always visible: experimental / predicted / unavailable. Predicted
  structures show pLDDT confidence. RMSD is hidden unless both are experimental.
- Evidence rows always show PMID + link. If `status` is `empty` or `unavailable`, render
  that state honestly. Never render a citation the API did not return.

## Exit criteria

`npm run dev` serves the app against a running `uvicorn src.api:app`; a person can pick a
species, generate a shortlist, open a candidate, compare two, edit one in the what-if lab,
and read grounded evidence — with every number traceable to an endpoint.


---

## How the plan changed on contact with the data

Recorded honestly, because the deltas are more useful than the original guesses.

**Phase 1 was wrong about the toxicity data.** The plan said to "keep hemolysis-%
measurements at a chosen reference concentration band and threshold the hemolysis %". The
lysis table does not hold that. It holds (effect level, dose that produced it), so the label
had to be dose-anchored instead. See research findings section 15.

**Phase 1 missed the censoring trap.** Nothing in the plan mentioned that 2,533 activity
rows are right-censored strings like `>100`, and that those rows are the entire inactive
class. Handling them correctly is the difference between a 62/38 split and a 90/10 one.

**Phase 1 missed non-standard sequences.** 1,265 of 11,433 master sequences are branched or
contain non-standard residues that ESM2 cannot embed.

**Species count went from three to five.** K. pneumoniae and A. baumannii both cleared the
50-sequence bar and are both WHO critical-priority, so they were trained and then labelled
by confidence rather than dropped.

**Phase 4's headline claim did not survive measurement.** "More real hits within budget"
is not what the data shows. Chemotype coverage is. The pitch was rebuilt around the claim
the evidence actually supports.

**Phase 4/5 UI switched from Streamlit to React** on request, with a FastAPI layer added
between the science and the frontend. The Streamlit fallback was then skipped deliberately.

**Structure work was added** beyond the original plan — a three-tier system (experimental
PDB / ESMFold prediction with pLDDT / unavailable) with RMSD gated to experimental pairs
only. The plan had flagged confident 3D as a trap; showing structures *with* their
confidence turned out to be the safe and stronger version of that idea.


---

# PHASES 6-10 — from tool to platform

Added 29 August 2026, ~00:30 Day 2, after judges reviewed the prototype and asked for a
backend database and a scientist login system.

**Full design, schema and rationale: `docs/07-system-design.md`. Read that first.** This is
the execution summary only.

## Why this is not just plumbing

The tool currently forgets everything the moment you close the tab. A lab is several
scientists running parallel campaigns against different pathogens over months, and the DMTA
cycle (design, make, test, analyse) only compounds if results accumulate somewhere shared.

The feature that makes it worth building: **the diversity objective currently avoids
redundancy inside one batch of twenty. With shared history it avoids redundancy across
everything the lab has ever tested.** Scientist 2 stops being handed peptides from a
scaffold scientist 1 already proved dead. Same submodular argument, extended along time.
The pitch line becomes "we never spend your money learning the same thing twice."

## Phases

| Phase | Scope | Exit criterion |
|---|---|---|
| 6 | Persistence, no auth. SQLite + SQLAlchemy, runs saved and reloadable, History screen. | Run a shortlist, restart the API, reopen it, identical numbers. |
| 7 | Labs, scientists, projects. bcrypt + JWT, project scoping, login UI. | Three seeded scientists log in; runs attributed correctly. |
| 8 | **Results + institutional memory.** Experiment capture, peptide registry, `exclude_tested` / `penalise_tested` on shortlist. | Scientist 1 records failures; scientist 2 visibly does not receive those peptides. |
| 9 | Trends and calibration. Hit rate per round, predicted-vs-observed calibration, cumulative chemotype coverage. | Calibration curve renders on seeded history. |
| 10 | Feedback into the model — Platt recalibration per project. Stretch. | Not expected tonight; present as designed. |

Phase 8 is the differentiator. Do not sacrifice it to reach phase 9.

## Non-negotiables for this stretch

- **Do not break the working product.** It is the asset. Auth is additive; the existing
  eleven endpoints stay callable unauthenticated until phase 8 is stable.
- **Do not touch `select.py`, `score.py` or `peptides.py`.** Exclusion logic lives in the API
  layer. Both verification suites stay green at every step.
- New code goes in new files: `src/db.py`, `src/models_db.py`, `src/auth.py`, `src/crud.py`.
  `api.py` gains routes and imports, nothing else.
- Seeded demo results are labelled `source='seeded_public'` and shown as such in the UI.
  Public DBAASP records must never be presented as this lab's own wet-lab work.
- Do not claim the model "learns" from twenty results. It recalibrates and it excludes.
  Both are real; the stronger claim is not.

## Stop rule

If phase 8 is not working by 07:00, stop and demo phase 7. Login plus saved history is a
good story. A half-wired memory feature that errors on stage is not.


---

## Parallel execution split (decided 29 Aug 2026, ~01:00 Day 2)

the engine track takes phases 6 and 8; the product track take phase 7; both run at the same
time. Phase 9 goes to whoever is free first.

### The dependency that has to be broken first

Phase 7 (auth, scientists, projects) needs database models and a session that phase 6
creates. Run naively, the product track sit blocked until phase 6 lands and the "parallel" plan is
just a sequential one with extra waiting.

**Fix: phase 6a is a shared foundation, written once, first, by the engine track, and frozen.**
It defines the COMPLETE schema — every table in the design, including the ones only phases 7
and 8 will use. Once it is committed and pushed, both tracks build against a fixed contract
and never touch each other's files.

    PHASE 6a  (the engine track, ~20 min, blocking)
      src/db.py          engine, SessionLocal, get_db dependency, init_db()
      src/models_db.py   ALL tables: lab, scientist, project, project_member, pool,
                         pool_sequence, run, run_item, assignment, experiment,
                         peptide_registry
      src/schemas.py     shared pydantic request/response models
      alembic init + first migration
      -> committed and pushed. Neither track edits these afterwards without saying so.

    then, in parallel:

    PHASE 6b  the engine track   run persistence, history endpoints, History UI screen
    PHASE 7   the product track        auth, labs, scientists, projects, login UI
    PHASE 8   the engine track   experiments, peptide registry, institutional memory
    PHASE 9   whoever is free   calibration and trend analytics

### No-collision rule

`api.py` is the one file both tracks would otherwise fight over. It becomes a thin
composition root and nothing else — imports routers, includes them, keeps the existing
eleven science endpoints. All new endpoints live in separate router modules:

    src/routes/runs.py        the engine track   phase 6b
    src/routes/auth.py        the product track        phase 7
    src/routes/projects.py    the product track        phase 7
    src/routes/experiments.py the engine track   phase 8
    src/routes/analytics.py   phase 9

Frontend splits the same way — the product track own `src/pages/Login.tsx`, `Projects.tsx` and the auth
bits of `store.tsx`; the engine track owns `History.tsx`, `LabMemory` and `Experiments`. Anything
touching `store.tsx` gets announced before editing, because it is the one shared frontend
file.

### Git discipline while running in parallel

- Branch per track: `feat/phase-6-persistence`, `feat/phase-7-auth`, `feat/phase-8-memory`.
- Both branch off `main` only after 6a is pushed.
- Pull `main` before each push; never force-push.
- Both verification suites must pass before any merge to `main`.

### Ordering note on phase 8

Phase 8 needs experiment records, which need projects, which come from phase 7. the engine track
can build all of phase 8 against the frozen schema and seed data without waiting — the only
genuine join point is at merge, where experiments start being attributed to real logged-in
scientists rather than seeded ones. Build it that way, merge phase 7 first, then phase 8.
