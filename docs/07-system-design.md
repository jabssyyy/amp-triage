# System Design — from tool to platform (phases 6–10)

Written 29 August 2026, ~00:30 Day 2, after judge feedback on the prototype asking for a
backend database and a scientist login system.

---

## 1. What a lab actually does, and where we sit in it

Worth getting this right before designing, because the schema falls straight out of it.

Antimicrobial discovery runs on the **Design–Make–Test–Analyse (DMTA) cycle**:

1. **Design** — generate or gather candidate peptides, predict which are worth trying.
2. **Make** — synthesise the chosen batch. Roughly 20 per round, because that is what the
   budget allows.
3. **Test** — wet-lab assays. MIC against the target pathogen, hemolysis against human red
   blood cells. About 28 days end to end.
4. **Analyse** — see which actually worked, and let that shape the next round.

Then it loops. A real campaign is many turns of this wheel against one pathogen.

**Today our product does step 1 only.** You run it, you get a shortlist, and the moment you
close the tab it has forgotten everything. Every run starts from nothing. That is what the
judges spotted, and they are right — it makes the tool a calculator rather than a system.

A lab is not one scientist doing one run. It is several people running parallel campaigns
against different pathogens over months, and the value compounds only if the results
accumulate somewhere shared.

## 2. The one feature that makes this worth building

Adding a database could easily be plumbing — logins, tables, a history page, nothing that
changes the science. There is a much stronger version available, and it comes free from the
maths we already have.

**Right now the diversity objective avoids redundancy inside a single batch of twenty.
With shared history it can avoid redundancy across everything the lab has ever tested.**

Concretely: scientist 1 runs a campaign against *E. coli*, tests twenty peptides, and
fourteen fail. Three weeks later scientist 2 starts a campaign against *K. pneumoniae*.
Without shared memory, the selector happily hands them peptides from the same scaffold that
already failed — because it has no idea that happened. With shared memory, those are
excluded or penalised, and the budget goes somewhere new.

This is the same submodular argument we already make, extended along the time axis instead
of within a batch. It turns "we pick a diverse batch" into **"we never spend your money
learning the same thing twice"**, which is a substantially better pitch and is the honest
description of what the system would do.

It also answers the segregation question directly. The point of separating scientists is not
tidiness — it is that separated work needs a shared memory or the lab duplicates effort.

## 3. Entities

    Lab
     └── Scientist            (login, role, belongs to a lab)
     └── Project              (a campaign: one target pathogen, several members)
          ├── Pool            (an uploaded set of candidate sequences)
          ├── Run             (one selection: pool + species + k + theta -> shortlist)
          │    └── RunItem    (one selected peptide, with its scores AT SELECTION TIME)
          │         └── Assignment   (which scientist owns testing this candidate)
          └── Experiment      (a wet-lab result for a peptide: MIC or hemolysis)

    PeptideRegistry           (lab-wide memory: every peptide ever selected or tested,
                               with its accumulated outcomes)

Two things deserve emphasis.

**RunItem stores the scores as they were at selection time.** Models get retrained; a
shortlist is a historical record of a decision and must not silently change underneath the
scientist who acted on it. This is also what makes calibration analysis possible later.

**PeptideRegistry is the institutional memory.** It is denormalised on purpose — one row per
sequence per lab, carrying how many times it has been selected, how many times tested, and
the best observed outcome. The selector reads this table, so the lookup must be one indexed
query and not a join across every run in history.

### Schema sketch

    lab(id, name, created_at)

    scientist(id, lab_id, email UNIQUE, full_name, password_hash, role, created_at)
      role in {'lead', 'scientist', 'viewer'}

    project(id, lab_id, name, target_species, status, created_by, created_at)
      status in {'active', 'paused', 'closed'}

    project_member(project_id, scientist_id, role)

    pool(id, project_id, name, n_sequences, uploaded_by, created_at)
    pool_sequence(pool_id, sequence)          -- indexed on sequence

    run(id, project_id, pool_id, scientist_id, species, k, theta,
        logdet, excluded_tested BOOL, n_excluded, created_at)

    run_item(id, run_id, rank, sequence, q_i, p_active, p_toxic,
             similarity_to_nearest, marginal_log_gain)

    assignment(id, run_item_id, assigned_to, status, updated_at)
      status in {'proposed', 'assigned', 'synthesised', 'tested', 'dropped'}

    experiment(id, project_id, sequence, scientist_id, assay,
               measured_value, unit, outcome, tested_at, notes, source)
      assay in {'MIC', 'hemolysis'}
      outcome in {'hit', 'miss', 'toxic', 'inconclusive'}
      source in {'wet_lab', 'seeded_public'}      -- never blur these two

    peptide_registry(lab_id, sequence, times_selected, times_tested,
                     best_outcome, last_tested_at)
      PRIMARY KEY (lab_id, sequence)

`experiment.source` matters. Seeded demonstration data drawn from public DBAASP records must
never be presentable as this lab's own wet-lab work. The column enforces the distinction and
the UI must show it.

## 4. Phases

Each phase leaves the system demoable on its own — the graceful-degradation rule that has
governed this build from the start. If phase 8 never lands, phase 7 still stands up.

### Phase 6 — persistence (no auth yet)

Every run gets saved and can be reopened. No accounts, single implicit lab.

- SQLAlchemy models, SQLite at `data/pharmamind.db`, alembic for migrations.
- Save on every `/shortlist` call: run + run_items.
- New endpoints: `GET /runs`, `GET /runs/{id}`, `DELETE /runs/{id}`.
- UI: a **History** screen listing past runs; clicking one restores that exact shortlist.

*Exit:* run a shortlist, restart the API, reopen the run, see identical numbers.

### Phase 7 — scientists, labs, projects

- Password hashing with bcrypt via passlib. JWT access tokens, ~12 h expiry.
- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`.
- Project CRUD; every run belongs to a project; every project targets one pathogen.
- Existing science endpoints stay callable so the verified demo path cannot break — auth is
  **additive**, gating only the new persistence endpoints at first.
- UI: login screen, project picker in the header beside the species selector, "my runs"
  versus "lab runs" filter.

*Exit:* three seeded scientists log in, each sees their own projects plus their lab's, and
runs are attributed correctly.

### Phase 8 — results and institutional memory (the differentiator)

This is the phase that justifies the whole exercise. Do not let it be cut for phase 9.

- `POST /experiments` records a wet-lab outcome for a peptide; assignment status advances.
- `peptide_registry` updates on every selection and every result.
- `POST /shortlist` gains two optional flags:
  - `exclude_tested` — drop anything the lab has already tested,
  - `penalise_tested` — multiply q_i by a decay factor instead of dropping outright.
  Implemented **in the API layer, not in `select.py`** — the verified core keeps its
  signatures and its 24 passing checks.
- The response reports `n_excluded` so the UI can say *"12 candidates skipped: already
  tested by this lab"*. That sentence is the demo moment.
- UI: a **Lab Memory** panel on the shortlist showing what was skipped and why, plus a
  results-entry form on the candidate screen.

*Exit:* scientist 1 records failures; scientist 2 runs a shortlist on a different pathogen
and visibly does not receive those peptides.

### Phase 9 — trends and calibration

- `GET /analytics/{project_id}` returning: hit rate per round, **calibration** (predicted
  P(active) bucketed against observed hit rate), property distributions of hits versus
  misses, and cumulative chemotype coverage across rounds.
- UI: an **Analytics** screen. Calibration is the headline chart — it is the honest answer
  to "is your model actually right?", and it gets more convincing as data accumulates rather
  than less.

*Exit:* with seeded history, the calibration curve renders and the hit-rate trend is real.

### Phase 10 — feedback into the model (stretch, claim carefully)

- Recalibrate probabilities per project using observed outcomes (Platt scaling on the
  existing classifier output). Cheap, statistically sound at small n.
- Surface calibration drift: "your predictions run 12% optimistic on this pathogen."
- Optionally fold confirmed results into training data and retrain on demand — flagged
  clearly as a manual action, never automatic.

*Do not claim the model "learns" from twenty results.* Twenty to a hundred outcomes cannot
retrain ESM2 and will not meaningfully move an XGBoost classifier trained on 845 sequences.
What they genuinely support is **recalibration** and **exclusion**. Say that. It is a real
capability and it survives scrutiny; "our model learns from every experiment" does not.

## 5. Technology

**SQLite via SQLAlchemy 2.0**, file at `data/pharmamind.db`. Postgres is the right answer for
a real deployment and the wrong answer tonight — a database that needs a running service is
a live failure mode at a venue. SQLAlchemy means the swap is a connection-string change, and
saying that in the pitch shows the choice was deliberate rather than naive.

**JWT with bcrypt.** No email verification, no password reset, no OAuth. Seeded accounts with
known passwords for the demo.

**Alembic** for migrations, so the schema is versioned rather than hand-patched.

Everything needed is already installed. No new dependencies, therefore no install risk.

## 6. Seed data

The system is unconvincing when empty, and there is no time to generate genuine wet-lab
results. Seed one lab, three scientists, three projects, and a history of runs whose
"results" are drawn from **real DBAASP measurements held out of training**.

This is legitimate because the measurements are real. It is only legitimate **if labelled**:
`experiment.source = 'seeded_public'`, and the UI says so on screen. Presenting public data
as this lab's own experiments would be the same class of mistake as the fabricated citations
we tore out earlier, and it would be caught the same way.

## 7. What we are deliberately not building

Role permissions beyond lead/scientist/viewer. Email or password reset. Real-time
collaboration. Audit logging. Multi-tenancy past a single lab per deployment. File storage
for assay attachments. Any of these is defensible to skip; none is missed in a demo.

## 8. Honest risk assessment

There are roughly eight hours to the final checkpoint and a working, verified product
already exists. That product is the asset — **the highest risk in this plan is breaking it.**

Mitigations, in order of importance:

1. Auth is additive. The existing eleven endpoints keep working unauthenticated until
   phase 8 is stable. The demo path must never depend on a login working.
2. `select.py`, `score.py` and `peptides.py` are not touched. Exclusion logic lives in the
   API layer. Both verification suites must stay green at every step.
3. Database work goes in new files (`src/db.py`, `src/models_db.py`, `src/auth.py`,
   `src/crud.py`). `api.py` gains routes and imports, nothing else.
4. If phase 8 is incomplete at 07:00, stop and demo phase 7. A working login plus saved
   history is a perfectly good story; a half-wired memory feature that errors on stage is
   not.

The realistic target is **phases 6, 7 and 8 complete, phase 9 partial**. Phase 10 will not
land tonight and should be presented as the designed next step, which is a legitimate thing
to show a judge as long as it is described as designed rather than done.
