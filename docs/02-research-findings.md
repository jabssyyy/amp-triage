# Research Findings — Tech Sangamam 2026 (AMP / AMR Triage)

Living knowledge base. Companion to context.md. Everything here has been verified against sources; where a claim is soft or an argument rather than a measured fact, it is marked.

Last updated: 29 August 2026, ~00:20 Day 2.
Changelog: v5 — build complete. Added section 15 with measured results and three corrections
to numbers in this file. docs/06-build-status.md supersedes this file where they disagree.
Changelog: v4 — no new verified numbers; noted the corrected checkpoint schedule for cross-reference with plan.md.
Changelog: v3 — build phase: cleaned-data pipeline real numbers (section 11), Decision 1 rationale (section 12), class-balance gate and split-by-sequence rule.
Changelog: v2 — added dataset download links, competitive landscape, and visualization/structure notes. v1 — initial capture (verified method knowledge, real numbers, data sources, selectivity direction, references).

---

## 1. The verified objective-function knowledge (the core of the build)

These were pulled from the sources, cross-checked, and hand-verified. This is the mathematical spine of the selection engine.

- **Submodularity = diminishing returns.** A set function f is submodular if adding an item to a smaller set helps at least as much as adding it to a larger set. Diversity is naturally submodular: the tenth near-copy adds almost nothing.
- **Greedy algorithm + guarantee.** Start empty, repeatedly add the item with the largest marginal gain, stop at budget k. For a monotone submodular function under a cardinality constraint, greedy reaches at least 1 - 1/e approximately 63.2% of the optimal value (usually >90% in practice). Proved by Nemhauser, Wolsey, Fisher (1978). The base problem is NP-hard, which is why a simple algorithm with a proven bound is judge-defensible.
- **Diversity via log-determinant.** Represent each peptide as a vector (ESM2 embedding). Diversity of a set = log det(X^T X + I) = the (regularized) squared volume of the box spanned by the vectors. Near-duplicates collapse the volume toward zero. This catches set-level redundancy that pairwise "drop things above 0.9 similarity" filtering misses.
- **DPP connection.** A Determinantal Point Process gives P(S) proportional to det(L_S). Greedy MAP inference of a DPP = greedy log-determinant submodular maximization. Same machinery.
- **THE objective (quality x diversity).** Decompose the kernel as L = diag(q) * S * diag(q), i.e. L_ij = q_i * S_ij * q_j.
  Then: **log det(L_A) = 2 * sum_i log(q_i)  +  log det(S_A)**
  - First term (modular): rewards individually high-quality items. q_i = the value/quality of peptide i.
  - Second term (submodular): the diversity penalty; collapses toward minus infinity for redundant sets.
  This single objective trades quality against diversity automatically. This is the objective function the whole project is built on.
- **Monotonicity condition.** log det(K_S) is monotone iff the smallest eigenvalue of K is >= 1. Regularize with +I (log det(K_S + I)) to guarantee monotonicity and submodularity unconditionally.
- **Guarantee is on the log-determinant, NOT the raw determinant.** Say "near-optimal with respect to the log-determinant objective." Do NOT claim "63% of optimal diversity" — exponentiating an additive bound gives an exponentially weak multiplicative one. This is exactly the kind of precision the judge may probe.
- **Cardinality vs knapsack budget (decided).**
  - Cardinality (pick exactly k): standard greedy keeps the full 1 - 1/e guarantee.
  - Knapsack (each item has a cost, total <= B): standard greedy AND cost-benefit greedy can each be arbitrarily bad alone. Combined heuristic (run both, take the better) gives 1/2(1 - 1/e) approximately 31.6% (Leskovec et al. 2007). Sviridenko (2004) partial enumeration restores the full 1 - 1/e.
  - **Decision: use cardinality (pick k) for the hackathon.** Mention cost-weighting as an extension. Cost budget halves the guarantee or needs enumeration.
- **Embedding normalization gotcha (must apply).** From SubMo-GNN: make embeddings non-negative (ReLU) and L2-normalize to the unit sphere before the log-det selection. Otherwise the volume objective favors large-norm (often redundant) vectors and diversity silently breaks. Apply this to the ESM2 embeddings — not optional.

---

## 2. Selectivity — the candidate innovation direction (UNDER DESIGN, not locked)

Marked as a candidate direction, deliberately not written as final.

- **The idea.** AMPs kill bacteria by tearing membranes; human cells also have membranes, so a great killer can also harm the patient. What matters is the safe window between the kill dose and the harm dose.
- **The two numbers.** MIC = dose that kills bacteria (lower is better). HC50 / toxicity = dose that harms your cells (higher is better).
- **Therapeutic window / selectivity index** approximately HC50 / MIC. A big ratio = kills bugs far below the dose that hurts you = good drug candidate.
- **Why it is the real bottleneck.** Activity is essentially solved; the reason thousands of active AMPs never became drugs is the window (toxicity), not the killing.
- **The move.** Redefine the quality term q_i in the objective from "how well it kills" (activity) to "how wide is its safe window" (activity AND low toxicity, fused). Same value x diversity x budget machinery; toxicity becomes a first-class objective, not an afterthought filter.
- **Honest catch.** Needs two decent predictors (activity + toxicity) and fusing two noisy predictions is harder than activity alone. Validation shifts to "does the tool recover peptides with real safe windows." Data exists to support it (see section 4).

---

## 3. Real numbers, with sources (credibility anchors)

Verified. Solid vs soft is marked.

**AMPs are real approved drugs (solid).**
- Eight AMPs have FDA approval: colistin, polymyxin B, vancomycin, gramicidin, bacitracin, daptomycin, enfuvirtide, telaprevir. ~70 more in the pipeline (27 clinical, 34 preclinical). Source: Drug delivery/formulation review, ScienceDirect S0169409X21001927.
- But only polymyxin/colistin and daptomycin are approved for systemic human use as membrane AMPs against resistant bacteria; thousands are active in vitro, few reach late clinical trials. Source: ACS Infect. Dis. 10.1021/acsinfecdis.2c00640. This is the strongest, fully-citable "wasted resources" story.

**The ~20-tested-per-round funnel (solid).**
- LSSAMP: filtered 5,000 generated sequences down to 21 synthesized for wet-lab testing; testing three Gram-negative panels cost about 30 days. Source: arXiv 2212.09450.
- Marine metagenome study: 1,033 predicted -> 10 selected -> 9 active (cell-free) -> 3 chemically synthesized and validated. Source: PMC12028987 / PubMed 40278299.
- Pattern: thousands computational in, tens wet-lab tested. Your premise is accurate.

**Cost and time (solid).**
- A full synthesis + wet-lab cycle (MIC, hemolysis, toxicity, circular dichroism) ~28 days vs 24 h for cell-free/computational. Source: screening-methods review, PMC11780100.
- Peptide synthesizer costs roughly $50,000-$150,000, plus per-peptide synthesis and assay costs. Source: excedr.com peptide-synthesizer cost writeup.

**Soft — do NOT claim as a number.**
- There is no clean published "X% of budget wasted on near-duplicates" statistic. Redundancy is a logical argument ("top-N concentrates budget on one chemotype"), not a measured percentage. Let the attrition numbers carry the hard evidence.
- Published ML-selection papers report HIGH hit rates (their selling point). So "AI selection wastes budget" is the wrong enemy. The real enemy: hits are redundant and toxicity kills them downstream. This is why the edge is diversity PLUS selectivity, not diversity alone.

---

## 4. Data sources (confirmed usable)

- **DBAASP** — core. Open REST API (dbaasp.org/api/v1). Stores activity as MIC against specific target species (pathogen-specific, exactly what's needed), plus toxicity/hemolytic data. 15,000+ peptides.
- **DRAMP 4.0** — 30,260 entries incl. ~2,900 experimentally measured hemolysis and ~2,700 cytotoxicity entries. Downloadable from Figshare under CC license. Toxicity labels.
- **Hemolytik 2.0** — ~13,200 dedicated hemolysis entries, CSV/FASTA download + REST API. Supplementary toxicity.
- **AmpLyze** — predicts HC50 (as pHC50 = -ln HC50). Dual-branch (ProtT5-XL + ESM2-3B embeddings), residue-level interpretability via Expected Gradients. Reference model for the toxicity side.

**Model note:** use a SMALL ESM2 variant (35M / 150M, at most 650M), NOT ESM2-3B. A 3B model is wrong for a 24-hour build; peptides are short and small variants are plenty for a downstream gradient-boosted classifier.

---

## 5. Open design questions (to resolve before building)

1. **What is q_i numerically?** If q_i = P(active) in (0,1), all log q_i are negative; harmless under a fixed budget k (every set has k terms) but scale-sensitive — probabilities near zero produce huge negative logs that swamp the diversity term. Likely need to rescale (an exponent theta, or map to a sensible positive range). This is the last piece that fully specifies the objective.
2. **Toxicity: hard filter or folded into q?** Hard filter (drop predicted-toxic, then select on activity+diversity) is cleaner to explain and validate. Folding it in is the selectivity-first move. Decision pending point-2 lock.
3. **Budget: cardinality (chosen) vs cost/knapsack (extension).**
4. **Objective type:** expected hits (exploitation, right for a triage tool) vs information gain (BATCHIE-style active learning, exploration). Chosen: expected hits.

---

## 6. Reference list

Core method (the NotebookLM sources, ingestible open-access forms):
- Krause & Golovin, Submodular Function Maximization — https://www.cs.cmu.edu/afs/cs/Web/People/dgolovin/papers/submodular_survey12.pdf
- Kulesza & Taskar, Determinantal Point Processes for ML — arXiv 1207.6083
- SubMo-GNN (diverse molecule selection, log-det) — https://www.nature.com/articles/s41598-022-04967-9 (open mirror: PMC8782878)
- BATCHIE (Bayesian active learning, batch drug screens) — https://www.nature.com/articles/s41467-024-55287-7 (open mirror: PMC11696745)
- Constrained DPP greedy MAP — https://arxiv.org/pdf/1607.01551
- SMART-RAG (determinantal selection for retrieval) — https://arxiv.org/abs/2409.13992
- RAG original (Lewis et al. 2020) — https://arxiv.org/abs/2005.11401
- ESM2 (Lin et al., Science 2023) — https://www.science.org/doi/10.1126/science.ade2574 ; code https://github.com/facebookresearch/esm
- AmpLyze (hemolytic concentration prediction) — https://arxiv.org/html/2507.08162v1
- WHO-priority-pathogen AMP ML (ACS Omega) — https://pubs.acs.org/doi/10.1021/acsomega.3c08676 (open mirror: PMC10905719)

Data sources:
- DBAASP v3 — https://academic.oup.com/nar/article/49/D1/D288/5957160 (open mirror: PMC33151284 area) ; API dbaasp.org/api/v1
- DRAMP 4.0 — https://academic.oup.com/nar/article/53/D1/D403/7889245 (open mirror: PMC11701585)
- Hemolytik 2.0 — https://www.biorxiv.org/content/10.1101/2025.05.12.653624

Numbers / credibility sources:
- LSSAMP (5000 -> 21 synthesized; ~30 days) — arXiv 2212.09450
- Marine metagenome (1033 -> 10 -> 3) — PMC12028987 / PubMed 40278299
- Screening-methods review (~28 days synthesis+wet-lab) — PMC11780100
- Approved AMP drugs + pipeline — ScienceDirect S0169409X21001927
- Only 2 systemic AMPs / attrition — ACS Infect. Dis. 10.1021/acsinfecdis.2c00640
- Peptide synthesizer cost — excedr.com

---

## 7. Lessons and corrections (carry these)

- Don't pitch as world-first. Honest framing: integration + a selectivity-first objective, validated. Name the state of the art yourself.
- The 1 - 1/e guarantee is on the log-determinant objective, not raw diversity/probability. Precise wording matters with this judge.
- No clean "% wasted on duplicates" statistic exists — argue redundancy logically, let attrition carry the hard numbers.
- The real enemy is redundant hits + downstream toxicity, not "AI wastes budget." Hence diversity PLUS selectivity.
- Write candidate directions as candidates, not final. (This is the repeated project lesson.)

---

## 8. Dataset download links (verified, hackathon-ready)

Activity data (MIC by pathogen) — core:
- DBAASP site: http://dbaasp.org/home
- DBAASP API: https://dbaasp.org/api/v1  (ranking_search gives MIC by target_species_id; peptide_card gives full record)
- API curl examples / helper: https://github.com/melomcr/dbaasp_api_helper_libraries
- 15,700+ entries; MIC/IC50 against specific target species; also hemolytic/cytotoxic fields.

Toxicity / hemolysis data:
- DRAMP 4.0 download page (CSV by subset, CC-BY, one-click): http://dramp.cpu-bioinfor.org/
- DRAMP 4.0 Figshare (DOI): https://doi.org/10.6084/m9.figshare.27233508
- 30,260 entries; 2,891 experimental hemolysis + 2,674 cytotoxicity entries.
- Hemolytik 2.0 (dedicated hemolysis, ~13,200): https://www.biorxiv.org/content/10.1101/2025.05.12.653624

ESM2 weights: https://github.com/facebookresearch/esm  (use a SMALL variant: 35M/150M, at most 650M — NOT 3B)

PubMed (RAG layer): https://pubmed.ncbi.nlm.nih.gov/  ; API: https://www.ncbi.nlm.nih.gov/home/develop/api/

Practical order: pull DRAMP first (one-click). DBAASP needs the API — use the GitHub curl examples.

---

## 9. Competitive landscape (positioning, verified)

Existing AMP tools (CAMPR3/R4, AI4AMP, dbAMP, recent capsule-net tools) are all the same shape: paste a sequence (FASTA) → get an AMP/not-AMP label + a probability, one peptide at a time, CSV out. None of them help CHOOSE A BATCH: no budget, no diversity, no "why this one vs that one," no side-by-side comparison, no scientist-facing reasoning. That is the UX gap our product fills — we treat "which candidates should a lab actually pursue" as the product, with an assistant-style explainable interface.

## 10. Visualization / structure notes (verified)

- Helical wheel: computed deterministically from sequence in ms; the standard AMP visual; shows the amphipathic split (hydrophobic vs cationic faces) that explains BOTH activity and toxicity. Safe, fast, judge-legible. Primary structural visual.
- 3D structure prediction TRAP: AlphaFold2 and similar are unreliable for short peptides; different tools disagree (high RMSD); many AMPs are disordered in water and only fold on membrane contact. Do NOT present confident 3D structures. If shown, mark as low-confidence illustration, lowest priority.
- Per-residue toxicity attribution (Expected Gradients, AmpLyze-style) is real model interpretability, not decoration — shows which residues drive danger. Stretch goal.


---

## 11. Cleaned data pipeline — real numbers (verified; source: cleaned data report, 28 Aug 2026)

The data pair cleaned the raw files into experimental tables, preserving one row per measurement (not flattened).

- peptide_master.csv — 11,433 unique normalized sequences. Sequence-level table for ML splitting and peptide features.
- dbaasp_activity_experimental.csv — 20,384 activity measurements across 1,743 unique sequences. Target species, activity measure/value, units, conditions, references. This is the activity label source (MIC by species).
- dbaasp_lysis_experimental.csv — 1,609 lysis/toxicity measurements across 717 unique sequences. Target cell, lysis measure, concentration, units. This is the ONLY usable toxicity label source.
- dramp_toxicity_experimental.csv — 11,612 DRAMP records. Free-text hemolysis/cytotoxicity annotations. NOT usable as a toxicity label (see trap below).

Sequence matches (exact, after trim + uppercase; no fuzzy matching):
- DRAMP and DBAASP-activity = 803 sequences.
- DRAMP and DBAASP-lysis = 441 sequences.
- Activity and lysis overlap approx 714 (dual-labeled set) — the ceiling for any selectivity / therapeutic-window work. Small; confirms selectivity is data-limited.

Traps and rules recorded:
- has_dramp_toxicity_annotation does NOT mean toxic. It only signals a non-empty DRAMP annotation, which may literally say "no information found." Never use it as a toxic/safe label.
- Split by normalized_sequence, never by experimental row (anti-leakage). Locked.
- 111 activity rows + 1 lysis row have missing sequences — drop.
- Aggregate measurements only AFTER labeling rules (target, assay type, organism/cell, unit, concentration, censored-value handling) are set.

## 12. Decision 1 — model outputs (LOCKED, rationale)

Both predictors are binary classifiers. Activity outputs P(active); toxicity outputs P(toxic).

- Chosen over regression because: MIC inter-lab noise is 2-4x (the class label survives it, a regression target chases the noise); per-species data is thin; P(active) in (0,1) fits the q_i log term with no rescaling; fastest to a working demo.
- A classifier's probability output is still a smooth, rankable score, so classification does not force coarse ranking. The threshold only shapes the training labels.
- Regression on log-MIC is a later upgrade for data-rich species (physical interpretability), not the Round-1 target.

Open (pending, from Decision 1):
- Class-balance histogram must be checked before thresholds are locked (actives likely dominate). If lopsided, move threshold or bin.
- Threshold values not locked: activity breakpoint (candidate MIC <= 32 ug/ml, needs citation, applied per species); toxicity "toxic" definition (human RBC, reference concentration, hemolysis % cut).

## 13. Decision 2 — toxicity handling (LOCKED)

Pure fold, no hard pre-filter. q_i = fusion of P(active) and (1 - P(toxic)) per peptide. Selection engine (log det(L_A) = 2 sum log(q_i) + log det(S_A)) runs directly on this fused q_i, no separate safety gate step before it.

Rationale: this is the selectivity-first move from research_findings section 2, now locked as the actual q_i definition, expressed via classifier probabilities rather than a precise therapeutic-window ratio (the ~714-peptide dual-labeled set and coarse hemolysis-at-one-concentration data cannot support a precise HC50/MIC number).

Exact fusion formula — LOCKED: q_i = P(active) * (1 - P(toxic)).

## 14. q_i scaling (LOCKED mechanism, theta value open)

Raw q_i in (0,1) as a product of two probabilities can be very small, making log(q_i) swing strongly negative for weak candidates and risking domination over the log det(S_A) diversity term.
Fix: use q_i^theta in the objective. theta=1 neutral default. theta<1 favors diversity, theta>1 favors quality.
theta is not fixed yet — tune once real P(active)/P(toxic) distributions exist from trained models.


---

## 15. Measured results and corrections (29 Aug 2026, post-build)

Everything below was measured on the real pipeline. Where it contradicts an earlier section
of this file, this section is correct.

### Corrections to earlier sections

**Section 11 said the dual-labeled ceiling is ~714. It is 248.** That figure came from a raw
sequence overlap taken before filtering to standard amino acids, human erythrocytes,
parseable dose and parseable hemolysis percentage. The usable human-RBC toxicity set is ~480
sequences, of which **272** carry a confident label, and **248** of those also have activity
labels. The toxicity classifier trains on 231 sequences. Small — quote the CV standard
deviation, never the mean alone.

**The DBAASP lysis table schema was misread.** `Activity Measure for Lysis` holds the effect
level ("50% Hemolysis", "0% Hemolysis") and `Peptide Concentration` holds the dose that
produced it. Each row is a point on a dose-response curve, so a toxicity label cannot be a
percentage cut at a fixed concentration. The label used is dose-anchored: toxic = reaches
≥50% hemolysis at ≤100 µg/ml; safe = tested at ≥100 µg/ml without reaching 50%.

**Censored measurements carry the negative class.** 2,533 activity rows read `>100`, `>256`
and similar; 1,328 more are ranges. A naive `to_numeric().dropna()` deletes ~3,900 rows,
almost all inactives, and swings class balance from ~62/38 to ~90/10. This was the single
largest trap in the dataset and it is not mentioned anywhere in the original plan.

**Structural coverage is 434 sequences, not 2,578.** A working figure of "26% of sequences
have experimental structures" was wrong: it counted every DRAMP row with a non-empty
`PDB_ID`, but **3,855 of those 4,310 values are literally the string "Not available"**. Only
455 rows carry a real PDB code, mapping to 434 embeddable sequences (~4%). Never quote 26%.

### The class-balance gate passed

Contrary to the concern in section 12, actives do **not** dominate once censoring is handled
correctly. At MIC ≤ 32 µg/ml: E. coli 59.9% active, S. aureus 58.9%, P. aeruginosa 56.7%,
K. pneumoniae 49.2%, A. baumannii 67.6%; toxicity 36.0% toxic. Nothing near the 85/15 limit.

### Model performance

| Model | CV ROC-AUC | test ROC-AUC |
|---|---|---|
| E. coli | 0.817 ± 0.032 | 0.797 |
| P. aeruginosa | 0.818 ± 0.033 | 0.812 |
| S. aureus | 0.732 ± 0.028 | 0.795 |
| K. pneumoniae | 0.746 ± 0.053 | 0.805 |
| A. baumannii | 0.586 ± 0.112 | 0.722 |
| Toxicity, human RBC | 0.849 ± 0.052 | 0.849 |

### The objective behaves as the theory predicts

Greedy matched the brute-force optimum on a small instance, and the incremental Cholesky
agrees with a direct `slogdet` to 1e-6. Marginal gains are non-increasing — submodularity
visible in the output. The θ knob is real: raising it monotonically increases mean raw q and
decreases diversity, converging to plain top-N at θ=5 (19/20 overlap). Worth saying out loud:
top-N is not a rival algorithm, it is this objective with diversity switched off.

### Validation — the claim had to change

Section 3 warned that "AI selection wastes budget" is the wrong enemy. That proved exactly
right, and it applies to our own headline too. Measured across five species and three seeds
on a clean pool with hidden actives drawn only from held-out test data:

- Raw hits: greedy 8.27 mean vs top-N 7.80. A wash — as expected, since raw hit count is
  precisely what a top-N sort optimises.
- Chemotypes reached: greedy 1.80 vs top-N 1.13. **Top-N reached exactly one chemotype in
  all fifteen runs. Greedy never lost a single run.**
- On E. coli specifically: 13.0 hits across 3.7 scaffolds versus 12.3 across 1.0.
- Cost of diversity, reported openly: greedy picks slightly more toxic candidates, mean
  P(toxic) 0.076 vs 0.043.

The defensible claim is coverage, not count. Say "the same number of hits spread across four
scaffolds instead of one". Do not say "we find more hits" — the data does not support it.

### Evidence layer discipline

An early implementation shipped a hardcoded citation bank named `REAL_FALLBACK_CITATIONS`.
All six PMIDs were verified against live PubMed and every one pointed to an unrelated paper
(PFAS exposure, dental resin cement, dengue, neuroblastoma). It was removed entirely. The
rule now enforced: never emit a citation that did not come back from a live NCBI query in
that request, never substitute another species' papers, and quote abstracts verbatim rather
than generating prose about a paper that has not been read. An empty evidence pane is
acceptable; an invented one is not.
