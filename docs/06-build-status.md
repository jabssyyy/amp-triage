# Build Status — what actually exists

Last updated: 29 August 2026, ~02:00 Day 2.
This is the single source of truth for what is built, measured, and verified. Where an
earlier document states something different, this file wins.

---

## Summary

Phases 0 through 5 are complete and verified. The React UI is built and has been run in a
real browser against live data. What remains is the pitch, and a Streamlit fallback that
was deliberately skipped.

| Area | State |
|---|---|
| Phase 0 — repo, data, split guards | complete, 34 checks pass |
| Phase 1 — labels, class-balance gate | complete, gate passed on all six models |
| Phase 2 — embeddings, classifiers | complete, 6 models trained |
| Phase 3 — q_i and log-det selection | complete, 24 checks pass |
| Phase 4 — validation harness, API | complete, results reproduced independently |
| Phase 5 — scientist endpoints, structures | complete, all 11 endpoints exercised |
| React UI | complete, 8 screens verified in-browser |
| Phase 6 — persistence, run history | complete |
| Phase 7 — auth, labs, campaigns | complete, reviewed |
| Phase 8 — experiments, lab memory | complete |
| Phase 9 — calibration, trends | the product track, in progress |
| Pitch / slides | **not started** |
| Streamlit fallback (`src/app.py`) | **stub, deliberately skipped** |

---

## Measured results

### Labels (phase 1)

| Model | sequences | positive class |
|---|---|---|
| activity / E. coli | 995 | 59.9% active |
| activity / S. aureus | 946 | 58.9% |
| activity / P. aeruginosa | 705 | 56.7% |
| activity / K. pneumoniae | 183 | 49.2% |
| activity / A. baumannii | 105 | 67.6% |
| toxicity / human RBC | 272 | 36.0% toxic |

Class-balance gate passed everywhere — nothing near the 85/15 limit. Dual-labeled
sequences (activity **and** toxicity): **248**.

### Models (phase 2)

ESM2 `esm2_t12_35M_UR50D`, 10,065 sequences embedded to 480 dims in 75 s. XGBoost depth 4.

| Species | CV ROC-AUC | test ROC-AUC | PR baseline |
|---|---|---|---|
| E. coli | 0.817 ± 0.032 | 0.797 | 0.593 |
| P. aeruginosa | 0.818 ± 0.033 | 0.812 | 0.538 |
| S. aureus | 0.732 ± 0.028 | 0.795 | 0.542 |
| K. pneumoniae | 0.746 ± 0.053 | 0.805 | 0.464 |
| **A. baumannii** | **0.586 ± 0.112** | 0.722 | 0.600 |
| Toxicity (human RBC) | 0.849 ± 0.052 | 0.849 | 0.342 |

CV and test agree throughout, so nothing is overfit to the split. A. baumannii is barely
above chance with error bars crossing it and is labelled low-confidence in the UI.

### Selection engine (phase 3)

- Synthetic duplicate test: top-N took **5/5** near-duplicates, greedy took **3/5**.
- On 400 real peptides, mean similarity-to-nearest-selected: greedy **0.929** vs top-N **0.982**.
- Incremental Cholesky matches a direct `slogdet` to 1e-6; greedy matched the brute-force
  optimum on a small instance.
- θ sweep on 300 peptides (E. coli, k=20) — the knob is real, not decorative:

| θ | mean raw q | mean similarity | overlap with top-N |
|---|---|---|---|
| 0.2 | 0.641 | 0.872 | 5/20 |
| 1.0 | 0.818 | 0.917 | 14/20 |
| 5.0 | 0.864 | 0.961 | 19/20 |

### Validation (phase 4)

Hidden actives drawn only from the held-out test split. Clean pool: test actives + test
inactives + decoys with no label for that species. Three seeds per species.

| Species | greedy hits | top-N hits | greedy chemotypes | top-N chemotypes |
|---|---|---|---|---|
| E. coli | 13.0 [11–15] | 12.3 [11–14] | **3.7** | **1.0** |
| P. aeruginosa | 11.0 [10–12] | 9.3 [8–10] | 2.0 | 1.7 |
| S. aureus | 10.0 [9–11] | 10.0 | 1.0 | 1.0 |
| K. pneumoniae | 5.3 | 5.3 | 1.3 | 1.0 |
| A. baumannii | 2.0 | 2.0 | 1.0 | 1.0 |

**The honest reading.** Raw hit count is a wash — expected, because raw hit count is
exactly what a top-N sort optimises. The real difference is coverage: across all 15 runs
top-N reached exactly **one** chemotype every time, and greedy never lost a run. Clearest
on E. coli and P. aeruginosa; on the sparser panels there are too few scaffolds for it to
show. Cost of diversity, reported openly: greedy picks slightly more toxic candidates
(mean P(toxic) 0.076 vs 0.043).

Pitch line: *the same number of hits spread across four scaffolds instead of one.*
Not "we find more hits."

### Structures (phase 5)

- **434** sequences have a real experimental PDB entry, out of 10,065 (~4%). In the
  300-peptide demo pool that is 14.
- Experimental tier verified: magainin 2 → PDB **2MAG**, 3,560 atoms, rendered.
- Predicted tier verified: ESMFold via ESM Atlas, pLDDT rendered and colour-coded.
- RMSD verified: **7.587 Å** between 2JUE and 1BH4 via Kabsch CA alignment, and correctly
  refused when either structure is predicted.

---

## Corrections to earlier documents

**Structural coverage was overstated.** An earlier working figure of "2,578 sequences /
26% have experimental structures" was wrong. It counted every row where the DRAMP
`PDB_ID` column was non-empty — but **3,855 of those 4,310 rows literally contain the
string "Not available"**. Only 455 rows hold a real PDB code, mapping to **434** sequences
we can embed. Do not quote 26% anywhere.

**The dual-labeled ceiling is 248, not ~714.** Research findings section 11 quoted ~714
from a raw sequence overlap taken before filtering to standard amino acids, human
erythrocytes, parseable dose and parseable percentage. The usable toxicity set is ~480
sequences of which **272** carry a confident label.

**The lysis table schema was misread in the original plan.** `Activity Measure for Lysis`
holds the *effect level* ("50% Hemolysis") and `Peptide Concentration` holds the *dose that
produced it*. Each row is a dose-response point, so the toxicity label is dose-anchored,
not a percentage cut at a fixed concentration.

**Censored measurements are the negative class.** 2,533 activity rows read `>100`, `>256`
and similar, plus 1,328 ranges. Dropping them swings the class balance from ~62/38 to
~90/10. They are kept as definitive inactives where the bound is at or above the threshold.

---

## Bugs found and fixed during review

| Bug | Impact | Status |
|---|---|---|
| Fabricated PubMed citations in a hardcoded fallback bank | All six PMIDs resolved to unrelated papers (dental cement, dengue, neuroblastoma) | removed; live retrieval only |
| pLDDT read on the wrong scale | Every predicted structure labelled "low confidence" and painted red; 86/100 shown as 0.86 | normalised to 0–100 |
| Helical wheel SVG missing `y2=` | Hydrophobic moment arrow always pointed straight up | fixed |
| `select()` returned scaled q for display | UI would show q^θ, tiny numbers at high θ reading as a bug | returns both `q` and `q_scaled` |
| Wheel rendered dark navy on a light UI | Visual clash | rethemed to the M3 palette |
| 3D molecule rendered microscopically | Unreadable | sizing and framing fixed |
| Invented isoelectric point formula | `7.0 + charge * 0.8` is not a pI | replaced with a real computation |

---

## What is left

1. **The pitch.** No slides, no rehearsed narrative. Largest remaining gap and the thing
   actually being judged.
2. **Streamlit fallback.** `src/app.py` is an empty three-tab stub. Deliberately skipped —
   the React app is verified working and the hour is better spent on the pitch. If React
   fails at the venue there is no fallback; that risk was accepted knowingly.

Stretch goals never started, logged as stretch from the beginning: per-residue toxicity
attribution (Expected Gradients) and log-MIC regression for the data-rich species.


---

## Platform phases 6-8 (29 Aug 2026)

Judges reviewed the prototype and asked for a backend database and a scientist login
system. Design in `docs/07-system-design.md`.

**Phase 6 — persistence.** SQLite via SQLAlchemy, 11 tables, foreign keys enforced (off
by default in SQLite) and WAL enabled. Every shortlist is saved and reopens with the
scores frozen at selection time. An identical consecutive run replaces its predecessor
unless it has been named, because the shortlist screen re-runs on every slider move and
an unguarded save floods the history.

**Phase 7 — auth (built by the product track, reviewed here).** bcrypt, JWT HS256, 12 h expiry.
Verified under adversarial checks: `/auth/me` leaks no hash, bad password / no token /
malformed token all 401, duplicate email 400, short password 422, and a scientist
registered into a second lab sees **zero** projects from the first. All eleven original
science endpoints still answer **200 without a token** — the constraint that mattered.

**Phase 8 — institutional memory.** `/experiments`, `/lab-memory`, `/registry`, plus
`exclude_tested` and `penalise_tested` on `/shortlist`. Filtering happens on the pool
before the engine sees it, so `select.py` is untouched and its 24 checks stay valid.

Verified end to end: Elena shortlists for *E. coli* and records two failures; Marcus then
runs a shortlist on **a different pathogen** and is not offered either dead peptide. Also
verified live: record a MISS on the current rank-1 peptide, re-run the 300-peptide
shortlist, and it is gone with a new peptide at rank 1. No pre-seeded state needed.

Cross-lab memory isolation holds — a second lab inherits none of the first lab's history.

### UI corrections, 02:00 Day 2

| Issue | Fix |
|---|---|
| Legend swatches used the pre-retheme colours and no longer matched the residues | legend now generated from the same colour function |
| μH label collided with the centre hub and the arrow | offset perpendicular to the arrow |
| Connector path read as a ball of wool on long peptides | drawn first, quieter, thinner |
| Relationship graph boxes overlapped their edge labels | grid layout, haloed edge labels |
| Paper nodes were not clickable | now link out to PubMed by PMID |
| Selection lost on page refresh | `focus` persisted to localStorage |

Removed at the user's request: the "Research-support tool. Not a medical decision-maker."
sidebar line and intro sentence, and the "Where this sits against existing tools"
positioning card. The positioning argument still lives in `docs/01-context.md` for the
pitch; it is simply no longer printed in the product.
