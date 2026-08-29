# Handoff — contracts and rules

STATUS (29 Aug 2026): phases 4 and 5 are COMPLETE, and the React UI is built. This file is
now the reference for anyone extending the code — the contracts, the endpoint shapes and the
rules below all still hold. Measured results are in `docs/06-build-status.md`.

Originally written as a brief for the product track building phases 4 and 5.

Verify the core still passes before and after your changes:

    python src/verify_phase0.py    # 34 checks
    python src/verify_phase23.py   # 24 checks

If either script fails, stop and fix that before continuing. They are the contract.

---

## The one rule that matters most

**Do not reimplement any of the science in TypeScript.** The scoring, the q_i formula,
the log-determinant greedy selection, the embedding normalisation — all of it is Python,
all of it is verified against brute force, and all of it stays in Python. The frontend
calls an API. It does not do math.

If you find yourself writing a determinant, a softmax, a similarity score, or a
probability fusion in JavaScript, you have taken a wrong turn.

---

## Architecture for a React frontend

The decision is React, not Streamlit, for a professional UI. That requires an API layer
that does not exist yet:

    React (frontend/)  ->  FastAPI (src/api.py)  ->  score.py / select.py / validate.py

**The UI is built LAST, from a template Sir Jabin will provide.** Do not design one.
Everything else — validation, API, helical-wheel geometry, evidence retrieval — is built
and testable through the API before any frontend exists. When the template arrives, the
work is wiring it to endpoints that already return real data.

**Build the API early and verify it against the CLI.** For the same input, `POST /score`
must return exactly what `python src/score.py --sequence ... --species ...` prints. If
they disagree, the API is wrong, not the CLI.

`src/app.py` is a Streamlit stub with three empty tabs. Keep it as a thin fallback that
calls the same API — if React is not finished by Round 3, a working Streamlit demo beats
a broken React one. That is the graceful-degradation rule from plan.md.

### Endpoint contracts

These mirror the locked Python signatures. Do not change field names.

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

      Display `q_i`, never `q_i_scaled`. q_i is the raw P(active) * (1 - P(toxic)) and
      reads as "probability of being both active and safe". q_i_scaled is q_i ** theta,
      an internal detail of the objective -- at theta=5 it renders as a tiny number and
      users read that as a bug. Both are returned so the math stays inspectable.

    POST /validate
      body     {"species": "...", "k": 20, "n_hidden": 50}
      returns  {"greedy_recovered": int, "topn_recovered": int, "n_hidden": int, "k": int}

    GET /species
      returns  [{"name", "n_train", "cv_roc_auc", "cv_roc_auc_std", "confidence"}]
      confidence is "high" | "moderate" | "low" — read it from reports/activity_metrics.json,
      do not hardcode.

### Startup

ESM2 loads lazily on the first uncached sequence and costs ~1.6s once. Warm it at API
startup so no user request pays it. Cached sequences score in 0.3 ms; a live what-if
sequence scores in ~37 ms once warm.

---

## What must appear in the UI

**Per-species confidence, visibly.** Not all five models are equally good. From
`reports/model_metrics.md`:

| Species | CV ROC-AUC | Show as |
|---|---|---|
| Escherichia coli | 0.817 +/- 0.032 | high |
| Pseudomonas aeruginosa | 0.818 +/- 0.033 | high |
| Staphylococcus aureus | 0.732 +/- 0.028 | high |
| Klebsiella pneumoniae | 0.746 +/- 0.053 | moderate |
| Acinetobacter baumannii | 0.586 +/- 0.112 | **low** |

A. baumannii is barely above chance and its error bars cross it. It must carry a visible
low-confidence marker. Hiding that is the kind of thing a rigorous judge finds and
punishes; showing it is the kind of thing that earns credit.

**`similarity_to_nearest_selected` per row.** This is the number the selector actually
used to decide two peptides were different. It answers "why both and not two copies of
the better one" — the single most likely judge question about the ranking.

**θ as a live control.** Moving it re-ranks. θ<1 favours diversity, θ>1 favours quality.
Let the judge move it and watch the shortlist change; that demonstrates the objective is
real and not a score sort with extra steps.

Measured on a 300-peptide pool against E. coli at k=20 — the knob is not decorative, and
this table is worth showing:

| θ | mean raw q of picks | mean similarity to nearest selected | overlap with top-N |
|---|---|---|---|
| 0.2 | 0.641 | 0.872 | 5/20 |
| 0.5 | 0.744 | 0.886 | 10/20 |
| 1.0 | 0.818 | 0.917 | 14/20 |
| 2.0 | 0.850 | 0.943 | 17/20 |
| 5.0 | 0.864 | 0.961 | 19/20 |

Quality rises and diversity falls monotonically, and at high θ the selection converges
to plain top-N — which is the correct limiting behaviour and a good thing to say out
loud: top-N is not a different algorithm, it is our objective with diversity switched
off.

---

## Phase 4 — validation harness (build this before any UI polish)

`src/validate.py` is still a stub. It is the most important thing you will build, because
the pitch rests on it.

Hide N known actives inside a candidate pool, run selection, and measure how many the
shortlist recovers within budget k versus plain top-N.

**The hidden actives must come from the phase-1 held-out TEST split.** If you draw them
from training data, the models have already seen them and the result is leakage dressed
up as a finding. `data/labels/activity_<species>_test.parquet` is the correct source.

Report one plot and one number. Report it honestly even if the margin is modest — a
small real number is worth more than a large fake one, and the judge is likelier to
probe a suspiciously large gap.

Note the ceiling before you start: on 400 real peptides the greedy shortlist averaged
0.929 similarity-to-nearest versus 0.982 for top-N. Real AMP embedding space is tight,
so expect a modest improvement, not a dramatic one.

## Phase 5 — scientist UX, built as API capability first

Every item below is computable server-side and must be exposed as an endpoint returning
real data BEFORE the UI template arrives. Build and test them headlessly.

1. **Helical wheel** — `GET /wheel?sequence=...` returning SVG. Deterministic geometry
   from the sequence: residues placed at 100° increments, coloured by hydrophobic vs
   cationic. This is pure math and belongs in Python, not the frontend. It shows the
   amphipathic split that explains activity AND toxicity in one picture, and it is the
   primary structural visual.
2. **Properties** — `GET /properties?sequence=...` returning net charge at pH 7,
   hydrophobic fraction, length, and residue composition.
3. **Compare** — `POST /compare` with two sequences, returning both property sets plus
   the embedding cosine distance the selector actually used. That number answers "why
   both and not two copies of the better one".
4. **What-if** — already supported by `POST /score`; an uncached sequence embeds live in
   ~37 ms. This is PharmaMind requirement #4 and is non-negotiable. No new backend work,
   just confirm it round-trips.
5. **Evidence layer** — `GET /evidence?sequence=...&species=...`, PubMed retrieval,
   top-3 abstracts per shortlisted peptide (or per pathogen where peptide-specific hits
   are sparse), summarised. Frame it as research-support, never a decision-maker.
6. **Relationship graph** — `GET /graph?...` returning nodes and edges for
   compound / pathogen / resistance mechanism / source paper, derived from the evidence
   results. Return data, not a rendered picture. Explainability surface, not the engine.

**Do not build confident 3D structure prediction.** AlphaFold is unreliable on short
peptides and many AMPs are disordered until they contact a membrane. If it appears at
all, it is a marked low-confidence illustration and the last thing you do.

---

## Things that will silently corrupt results if you touch them

1. Never drop censored measurements (`>100`, `>256`). Those rows are the inactive class.
2. The lysis table is (effect level, dose), not (dose, percent).
3. Filter to standard amino acids before embedding; ESM2 cannot handle the rest.
4. Split by `normalized_sequence`, never by row.
5. `has_dramp_toxicity_annotation` is not a toxicity label.
6. ReLU + L2 normalise embeddings before the selection kernel, never for the classifiers.
7. Small ESM2 only. Never 3B.

Full explanations are in `README.md` and `src/peptides.py`.

---

## Language for the pitch

The 1 − 1/e guarantee is **on the log-determinant objective**, not on raw diversity.
Say "near-optimal with respect to the log-determinant objective". Do not say "63% of
optimal diversity" — exponentiating an additive bound gives an exponentially weak
multiplicative one, and that is exactly the kind of imprecision a rigorous judge probes.

Name the state of the art (CAMPR4, AI4AMP, dbAMP, AmpLyze) and position honestly as
integration plus a selectivity-first objective, validated. Never world-first.

---

# ADDENDUM — Phase 7: authentication, scientists, projects

Added 29 August 2026, ~01:00 Day 2. This is the product track' next assignment. the engine track is
building phases 6 and 8 at the same time, so the boundaries below are not style preferences —
crossing them causes merge conflicts in a live build.

Read `docs/07-system-design.md` section 3 for the schema and section 4 for why phase 7 exists.

## Wait for phase 6a

Do not start until `src/db.py`, `src/models_db.py` and `src/schemas.py` are on `main`. They
define the COMPLETE schema including every table you need. **Do not add, rename or alter a
column in those files.** If something is genuinely missing, say so and stop — a schema change
mid-flight breaks the other track silently.

Then branch: `git checkout -b feat/phase-7-auth` off `main`.

## Your scope

    src/auth.py               password hashing, JWT encode/decode, current-user dependency
    src/routes/auth.py        POST /auth/register, POST /auth/login, GET /auth/me
    src/routes/projects.py    project CRUD, membership, GET /projects/mine
    src/seed.py               one lab, three scientists, three projects
    frontend/src/pages/Login.tsx
    frontend/src/pages/Projects.tsx

You may add `app.include_router(...)` lines to `api.py`. Nothing else in that file.

## Files you must NOT touch

    src/select.py  src/score.py  src/peptides.py  src/embed.py  src/train_*.py
    src/db.py  src/models_db.py  src/schemas.py
    src/routes/runs.py  src/routes/experiments.py        (the engine track owns these)
    frontend/src/pages/{Shortlist,Candidate,Compare,WhatIf,Evidence,Graph,Validation}.tsx
    frontend/src/api.ts    (append-only: add new call signatures, change nothing existing)

`frontend/src/store.tsx` is shared. You own the auth slice — current user, token, active
project. Announce before editing and keep your changes additive.

## Requirements

**Passwords.** bcrypt via passlib. Never store or log a plaintext password. Never return a
password hash from any endpoint, including `/auth/me`.

**Tokens.** JWT, HS256, ~12 hour expiry. Read the secret from an env var with a development
default; do not hardcode a production secret. Return `{access_token, token_type}`.

**Auth is additive, and this is the important one.** The existing eleven science endpoints
(`/score`, `/shortlist`, `/validate`, `/species`, `/properties`, `/wheel`, `/compare`,
`/evidence`, `/graph`, `/structure`, `/structure/compare`) **stay callable without a token**
in phase 7. There is a verified working demo depending on them and it must not break. Gate
only the new persistence endpoints. Provide `get_current_user` as a dependency and a separate
`get_current_user_optional` for endpoints that behave differently when signed in.

**Projects.** A project has exactly one `target_species`, drawn from the five trained ones.
Membership is many-to-many via `project_member`. Roles are `lead`, `scientist`, `viewer` —
implement the column and check it for destructive actions only. Do not build a permissions
framework.

**Seed data.** One lab ("Sample AMR Research Unit"), three scientists with known demo
passwords, three projects on different pathogens. Print the credentials on seed so the demo
is reproducible. Seeded records must be identifiable as seeded.

**Frontend.** Login screen matching the existing Material 3 tokens in `tailwind.config.js` —
do not introduce new colours or a component library. Token in memory plus `localStorage`.
Project selector sits in the header next to the existing species selector. When a project is
active, the species selector follows the project's target and shows why.

## Do not build

Email verification, password reset, OAuth or social login, refresh-token rotation, rate
limiting, audit logging, or an admin panel. Any of these is defensible to skip and none is
missed in a demo. If you find yourself building a permissions matrix, stop.

## Definition of done

1. `python src/verify_phase0.py` and `python src/verify_phase23.py` both pass.
2. `npx tsc --noEmit` clean; `npm run build` succeeds.
3. All eleven original endpoints still answer **without** a token — prove it with curl.
4. Three seeded scientists can log in; each sees their own projects and their lab's.
5. `/auth/me` never returns a hash.
6. Pull `main`, resolve, push `feat/phase-7-auth`. Do not merge to `main` yourself.

Report: the curl transcript for register / login / me / projects, the two suite outputs, and
the seeded credentials.
