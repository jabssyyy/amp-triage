# Project Context — Tech Sangamam 2026 (AMR / AMP Triage)

Living project brief. Read fully before responding in a new chat. Companion file: research_findings.md (verified method knowledge, real numbers, references).

Last updated: 30 August 2026.
Changelog: v9 — phases 6-9 complete. Repo is github.com/jabssyyy/amp-companion; data is
local only and gitignored; no AI-tool attribution anywhere. Read docs/06-build-status.md
first in a new session — it opens with a handoff block and supersedes this file on facts.
Changelog: v8 — BUILD COMPLETE through phase 5 plus the React UI. See docs/06-build-status.md
for measured results; that file supersedes this one wherever they disagree. Three figures in
this document were corrected during the build: the dual-labeled ceiling is 248 (not ~714),
structural coverage is 434 sequences (not 2,578 — most DRAMP PDB_ID values read "Not
available"), and the lysis table schema is (effect level, dose), not (dose, percent).
Changelog: v7 — schedule corrected (Round 1 = ideation/workflow, done; Round 2 = work structure + basic working product; Round 3 = full demo). Moving to build in the engine track; plan.md created as the phased execution guide.
Changelog: v6 — locked Decision 3 (q_i formula = P(active)*(1-P(toxic)), scaling via theta exponent).
Changelog: v5 — build phase: locked Decision 1 (model outputs = classification, P(active) and P(toxic)); added class-balance gate before thresholds; folded in cleaned-data pipeline facts and the split-by-sequence anti-leakage rule; team split recorded; Decision 2 opened as candidate.
Changelog: v4 — corrected the judging note (Vijayakumar is chief guest, NOT confirmed judge); folded the what-if requirement into a scientist-assistant visualization UX (helical wheel, compare, live re-score); flagged 3D-structure-prediction as a trap to avoid.
Changelog: v3 — PharmaMind pivot: hackathon switched to problem-statement format; chose problem statement #6 (PharmaMind). AMP work reframed to fit, niche decision locked, budget moved to business scope, what-if feature flagged as gap.

---

## PIVOT — PharmaMind (problem statement #6), locked 28 Aug 2026

The hackathon moved to a problem-statement format. Of ten statements, chose #6: "PharmaMind: Intelligent Drug Discovery Assistant." Its ask: an AI research assistant that finds relationships between diseases, biological targets, and compounds; ranks promising candidates; explains the evidence per prediction; identifies similar previously studied compounds; lets researchers explore hypothetical relationships; framed as research-support, not a medical decision-maker. Tech listed: ML, DL, NLP, GenAI, Knowledge Graphs, GNNs, Molecular AI.

**Decision: go niche and deep — instantiate PharmaMind directly as antimicrobial drug discovery, not a general tool.** For this validation-minded judge, narrow-and-validated beats broad-and-shallow. The niche maps onto their exact wording: disease = drug-resistant bacterial infection (AMR); biological target = the pathogen (WHO priority species); compound = antimicrobial peptide. State this mapping in the first 30 seconds of the pitch so "why so narrow" is pre-empted.

**Framing sentence (lock with team):** "An AI research assistant for antimicrobial drug discovery — it ranks candidate compounds against drug-resistant pathogens, grounds every prediction in published evidence, surfaces similar known compounds, and lets researchers explore what-if hypotheses. A research-support tool, not a medical decision-maker."

**Budget → business scope (decided).** Cost/rupee economics is NOT in their ask, so it is off-brief as a technical headline. Move it to the business/impact slide (why a lab pays, market demand, bottleneck removed). BUT keep the diversity-aware + selectivity-aware RANKING math (submodular / log-det) as a core, on-brief technical feature — reframed as ranking quality (non-redundant shortlist of active-and-safe candidates), not as "budget." Do not bury the ranking math in business scope; it is the differentiator.

**Requirement coverage:**
1. Rank promising candidates — prediction + diversity/selectivity ranking. Have it.
2. Explain evidence per prediction — PubMed RAG layer. Have it (their core ask).
3. Identify similar studied compounds — ESM2 similarity + RAG over known peptides. Have it.
4. Explore hypothetical relationships — was the gap; now folded into the scientist-assistant UX (below). The "what-if" = let the researcher edit or propose a peptide, score it live against a chosen pathogen, and see it re-ranked and compared. Non-negotiable (explicitly asked). Build it.
5. Research-support not decision-maker — exact framing already. Have it.

**Product identity: an assistant to the scientist, not a black-box ranker.** The tool should help a researcher SEE and REASON, not just output scores. Core UX ideas (decided direction):
- Helical wheel per peptide (deterministic from sequence, no prediction uncertainty) showing the hydrophobic vs cationic faces — makes activity AND toxicity visually legible in one diagram. This is the safe way to give structural intuition.
- Composition/property panel: charge, hydrophobic fraction, length, key residues.
- Per-residue toxicity attribution (AmpLyze-style Expected Gradients) — which residues drive danger; points to what to change. Stretch goal.
- Side-by-side compare: two selected peptides, their wheels, properties, and embedding distance (the actual number the selector used to call them different) — answers "why both and not two copies of the better one" visually.
- The what-if lives here: edit a residue or type a hypothetical sequence, re-score and re-place it live, see the wheel/props update. This satisfies requirement #4 AND makes the tool feel like an assistant.
- AVOID confident 3D structure prediction (AlphaFold on short peptides is unreliable; AMPs are often disordered until they hit a membrane). If shown at all, mark as low-confidence illustration, last priority.

**Optional cheap add for the KG/GNN language in their tech list:** render the evidence layer as a small relationship graph (compound - target/pathogen - resistance mechanism - supporting paper), sourced from RAG. Explainability surface, NOT the engine — do not rebuild TxGNN-style KG link prediction.

**Next:** lock framing sentence with team; design the what-if feature (the gap); then Round-1 build order (core prediction + ranking must demo first).

---

---

## How to work with me (Sir Jabin)

- Be a brutally honest guide. Never blindly agree. If reasoning is weak, off track, or unrealistic, say it directly and explain why.
- Short, clear, plain language. No heavy formatting, no walls of bullet points. Humanised writing, minimal hyphenated compound words.
- Do not stall with endless clarifying questions when I ask for forward movement.
- Verification over trust. Check claims, do not take assertions at face value.
- Plan before building. No execution until the plan has no holes.
- For routine work (docs, formatting, abstracts), just do it efficiently, no lectures.
- When explaining a new domain or concept, explain it beginner-clear, with visuals where they help.

---

## The competition

- Event: Tech Sangamam 2026, National Level Open Innovation Hackathon. Organisers: IEEE Student Chapter and SIMATS Engineering.
- Format: 24-hour onsite BUILD hackathon (not pitch-only), 28-29 August 2026. Three live evaluation checkpoints (~4 PM Day 1, ~2 AM, ~8:30 AM Day 2). Real progress must show at each.
- Team of 4. Prize pool ~50,000 rupees. No shortlisting round — everyone who registers competes. Track: Open Innovation (flagship), AI/ML theme.
- Winning criteria confirmed by coordinators: innovation and uniqueness. Any domain accepted.

### The judging (corrected)

NOTE: Dr. K. Vijayakumar is the event's CHIEF GUEST, not confirmed as the judge. The actual judge(s) are unknown. Do NOT over-tailor to his profile. Build and pitch to satisfy any rigorous technical judge.

His profile is still useful as a reasonable proxy for the calibre of person likely evaluating (AI/ML + biomedical informatics academic; values clean methodology, honest validation, solid data handling; recognises derivative or overclaimed work). So the same discipline holds regardless of who judges:
- Do NOT pitch as world-first. Pitch as an honest, validated, integrated applied tool; name the state of the art; position against it.
- Lead with rigor, honest validation, and a clear demo. Hype and overclaiming lose.
- Assume the judge may or may not be deeply biomedical, so the pitch must land for a general strong-technical audience AND survive a domain expert's scrutiny.

---

## The locked problem statement (decided, do not reopen)

**Title:** AI-Powered Budget-Aware Triage System for Antimicrobial Peptide Discovery Against Drug-Resistant Bacteria.

**One line:** The real bottleneck in AMP development is not prediction accuracy, it is cost-constrained selection. We build a triage tool that turns a huge pool of candidate peptides into the smartest shortlist a lab can actually afford to test.

**The problem:** Antimicrobial resistance is a fast-growing crisis; AMPs (short protein chains that kill bacteria in a hard-to-resist way) are a leading replacement for failing antibiotics. AI already predicts activity and safety well — that part is saturated. Where teams get stuck is money: a lab can generate thousands of candidates computationally but can only afford to synthesise and wet-lab test a small handful per round (~20). Today that final cut is made crudely by taking the top scorers, which wastes budget on near-duplicates, ignores safety trade-offs, and misses the real goal — maximising actual working hits within a fixed testing budget.

**What the tool does:** Given a candidate pool, it (1) scores activity against specific WHO-priority drug-resistant pathogens, (2) filters/penalises candidates likely to harm human cells (toxicity/selectivity), (3) removes near-duplicates so the shortlist stays diverse, (4) ranks by expected real hits within a defined testing budget, (5) cross-checks top picks against literature for a confidence signal. Output: a ranked, budget-fit, evidence-backed shortlist.

**Planned stack:** ESM2 embeddings; gradient-boosted classifiers for activity and toxicity; diversity-aware budget-optimised selection (log-determinant / DPP greedy); retrieval-augmented generation over PubMed for evidence grounding.

**Validation (non-negotiable):** Hide known active peptides in the pool and measure how well the tool recovers them within budget. A concrete, honest metric vs top-N.

---

## Current design status (as of 26 Aug 2026)

- **Research phase complete.** Method knowledge verified against sources and hand-checked (see research_findings.md section 1). The objective function is settled: maximise log det(L_A) = 2 sum log(q_i) + log det(S_A), a quality term + a diversity term, greedily under a cardinality (pick-k) budget, with regularised (+I) log-det and unit-normalised embeddings.
- **Candidate innovation direction (UNDER DESIGN, not locked): selectivity-first.** Redefine the quality term q_i from "how well it kills" (activity) to "how wide is its safe window" (activity AND low toxicity fused; therapeutic window ~ HC50/MIC). Rationale: activity is solved; toxicity is the actual reason AMP candidates fail (only ~2 AMPs used systemically despite thousands active in vitro). This makes selectivity a first-class objective rather than an afterthought filter. Raises the modelling bar (needs activity + toxicity predictors); data supports it. To be locked after design.
- **Decisions taken:** cardinality budget (not knapsack); expected-hits objective (not information-gain); small ESM2 variant (not 3B); guarantee stated w.r.t. the log-determinant objective (not raw diversity).
- **Still open:** exact q_i definition/scaling; toxicity as hard filter vs folded into q (tied to the selectivity lock). See research_findings.md section 5.

---

## How we got here (reframing journey — do not re-enter dead ends)

Started chasing a high-novelty biomedical idea; ~8 verification searches showed every clean idea already published. Killed, in order: de novo protein binder design (needs wet lab); drug repurposing via KG link prediction (= TxGNN, Nature Medicine 2024); explainable clinical AI (saturated); AI co-scientist (Google/FutureHouse own it); enzyme mutation effect prediction (ESM, AlphaMissense, ProteinGym); AMP activity+toxicity prediction as a novelty claim (PyAMPA, MAC-AMP, HMAMP etc.); budget-constrained selection as virgin ground (DrugGym, BATCHIE, active-learning papers).

**Conclusion locked:** at the level of a novel base idea/method, AI+biology in 2026 is picked clean. A 4-person student team won't find a virgin idea in a week. Novelty for us = execution, integration, sharp application, judged against other 24-hour teams. Assemble known components into one working, validated, usable triage pipeline aimed at the exact cost + selectivity bottleneck. Pitch honestly as integration, never world-first.

---

## Honest risks

- Novelty is modest and rests on execution + framing. Selectivity-first is the strongest lever to lift it from "good feature" to "real innovation" — but it must be genuinely built and validated, not hand-waved.
- The budget-aware/diversity step must be the real log-det objective, not a thin wrapper on a score sort.
- Don't import a whole SOTA model wholesale as the engine — own enough of the stack to answer "what did you actually build."
- Demoability across three checkpoints: core (activity scoring + budget ranking) pre-built and bulletproof for Round 1; evidence layer = Round 2 wow; toxicity/selectivity, diversity, UI polish = Round 3. Design for graceful degradation.
- Timeline: event is 28-29 Aug; today is 26 Aug. ~2 days of prep, not 6. Strategy is done; the build plan (data pipeline, objective code, validation harness, role split, pre-build vs live) is the crunch.

---

## Registration abstract (271 words, approved)

Antimicrobial resistance is one of the fastest growing health crises today. Conventional antibiotics are losing effectiveness, and antimicrobial peptides have emerged as one of the most promising alternatives because bacteria find them far harder to resist. AI can already predict which peptides are likely active and safe. But that is not where progress stalls.

The real bottleneck is selection under cost. Labs can generate thousands of candidate peptides computationally, but physically testing each one is expensive. In practice a lab can only afford to test around twenty candidates per round. Right now teams solve this by picking the top scoring ones, which wastes money on near identical candidates, ignores safety trade offs, and misses the actual goal of getting the most real hits out of a limited budget.

We are building a triage tool that solves exactly this. Given a large pool of candidates, our system scores each peptide for predicted activity against WHO priority drug resistant pathogens, filters out candidates that could harm human cells, removes near duplicates to keep the shortlist diverse, and ranks everything by expected real hits within a defined testing budget. Top candidates are also cross checked against published research to give a confidence score a scientist can trust.

Technology stack: ESM2 protein language model for sequence embeddings, gradient boosted classifiers for activity and toxicity prediction, diversity aware batch selection for budget optimization, and retrieval augmented generation over PubMed for evidence grounding.

We validate by hiding known active peptides in the data and measuring how well the tool recovers them within budget, giving an honest proof of performance.

The impact is direct. Smarter first round screening lowers the cost barrier that stops companies from investing in new antibiotics at a time the world urgently needs them.

---

## Next steps

1. Lock the selectivity-first direction (define what q_i optimises: activity vs therapeutic window).
2. Settle q_i scaling and toxicity handling (hard filter vs folded value).
3. Build the validation harness (held-out recovery within budget vs top-N) early and test it.
4. Confirm data pipeline: DBAASP (MIC by species) + DRAMP/Hemolytik (toxicity), downloaded and usable.
5. Role split for the 4-person team; pre-build vs live-build plan; graceful-degradation design.
6. Demo + pitch narrative: name the SOTA, position against it, lead with validation.


---

## Build phase — locked decisions (28 Aug 2026)

Team: 4 people, split in two. This chat (Sir Jabin + build partner) owns architecture and build. The other pair owns data interpretation and the report; they delivered a schema inspection report, then a cleaned experimental data pipeline (real numbers in research_findings section 11).

**Decision 1 — LOCKED. What each model outputs.**
- Activity model outputs P(active), a probability. "Active" = MIC at or below a chosen breakpoint against a specific pathogen. Binary classification, not regression.
- Toxicity model outputs P(toxic), a probability. "Toxic" = hemolysis percentage above a chosen threshold at the tested concentration. Binary classification.
- Why classification not regression: MIC reads 2-4x differently between labs (a yes/no label survives that wobble, a regression target chases it); per-species data is thin (a coarse label learns from fewer examples); P(active) in (0,1) plugs straight into the q_i log term with no rescaling; fastest route to a working Round 1.
- A classifier's probability output is itself a smooth, rankable score. Choosing classification does NOT force coarse buckets at ranking time; the threshold only shapes the training labels.
- Regression on log-MIC is a stretch upgrade for the 2-3 data-rich species only (gives physically meaningful "MIC approx X"), added after the core is solid. Not first.

**Gate before labels are written (NEW, must do).** AMP databases are enriched for actives, so a single cutoff (e.g. MIC <= 32) may produce a lopsided split that starves the classifier. Before the cleaners bake any threshold into labels, pull the class-balance histogram for activity and for toxicity. If one class dominates badly, move the threshold or bin instead of a single hard cut.

**Threshold values — candidate, not locked.** Common convention MIC <= 32 ug/ml for antibacterial activity; must be justified from a cited breakpoint or the dataset's own convention, and applied per species. Toxicity "toxic" definition pending: human RBC only, one reference concentration, threshold the hemolysis %.

**Anti-leakage rule — LOCKED.** Split by normalized_sequence, never by experimental row, so the same peptide cannot appear in both train and test.

**Decision 2 — LOCKED. Pure fold, no pre-filter.** Toxicity does not gate candidates before selection. Instead q_i = fusion of P(active) and (1 - P(toxic)), so a peptide only scores well if it is both likely active and unlikely toxic. This is the selectivity-first differentiator, expressed as a coarse fused score (not a precise HC50/MIC ratio, data does not support that precision).
Known risk, accepted: without a hard safety floor, a peptide the model is very confident is toxic could still rank if its activity score is high enough, since it is one multiplicative term, not a gate. Sir Jabin chose pure fold over the layered filter+fold option knowingly.


**Decision 3 — LOCKED. q_i formula and scaling.**
q_i = P(active) x (1 - P(toxic)). Plain product, read as approx probability of being both active and safe (treats the two as roughly independent).
Scaling: raise to a tunable power, q_i^theta, before entering the objective (log q_i term). theta=1 default/neutral. theta<1 softens quality's pull (diversity matters more); theta>1 sharpens it (quality dominates). theta tuned after real training numbers exist, not fixed yet.
This resolves the earlier open concern (research_findings section 5, Q1) that raw small probabilities produce large negative log values that could swamp the diversity term.


---

## Schedule (corrected 28 Aug 2026, ~5:30 PM Day 1)

- Round 1 — ideation + workflow. DONE.
- Round 2 — show the work structure AND a basic working product. This is the next checkpoint.
- Round 3 — full demo with the scientist UX layer.

## Handoff to the engine track

Sir Jabin is moving execution to the engine track. Three files travel together:
- context.md (this file): project brief, all locked decisions, constraints, how-to-work.
- research_findings.md: verified numbers, sources, method math, open questions.
- plan.md: phased execution plan built around the revised checkpoint schedule. Read that first for what to do next.


---

## Build complete — 29 August 2026, ~00:20 Day 2

Phases 0 through 5 are built and verified, and the React UI runs against live data. Full
measured results are in `docs/06-build-status.md`. Headlines:

- Five activity classifiers plus one toxicity classifier. E. coli and P. aeruginosa reach
  CV ROC-AUC ~0.82; toxicity reaches 0.849. A. baumannii is 0.586 ± 0.112 — barely above
  chance — and is labelled low-confidence in the product rather than hidden.
- Selection engine verified against brute force. On E. coli the greedy shortlist reaches
  3.7 chemotypes versus top-N's 1.0, from the same budget.
- All 11 API endpoints live; eight UI screens verified in a real browser.

**The validation framing changed and this matters for the pitch.** The original claim was
"more real hits within budget". Measured across five species and three seeds, raw hit count
is a wash. What holds up is coverage: top-N reached exactly one chemotype in all fifteen
runs, greedy never lost one. Pitch it as *the same number of hits spread across four
scaffolds instead of one* — four independent leads for the same money. That is the claim
the data supports; the original one is not.

**Decision taken knowingly:** the Streamlit fallback was skipped. `src/app.py` remains a
stub. If React fails at the venue there is no backup. The hour was judged better spent on
the pitch, which is the remaining gap.


---

## Judge feedback and the platform pivot — 29 August 2026, ~00:30 Day 2

Judges reviewed the working prototype and asked for a **backend database and a scientist
login system**. Not a slide deck. The request is sound: the tool currently forgets
everything between sessions, which makes it a calculator rather than a system.

**Decision: build it, and build the version that changes the science rather than just adding
plumbing.** Design is in `docs/07-system-design.md`, execution phases 6-10 in
`docs/03-plan.md`.

The core idea: the diversity objective today avoids redundancy within one batch of twenty.
Backed by a shared database of everything the lab has already tested, it avoids redundancy
across the lab's entire history. Two scientists working separate pathogens stop duplicating
each other's dead ends. This extends the existing submodular argument along the time axis
and gives a stronger, still-honest pitch line: *we never spend your money learning the same
thing twice.*

Scope: phases 6, 7 and 8 are the realistic target in the remaining ~8 hours, with phase 9
partial. Phase 10 (model feedback) is designed but will not land, and should be presented as
designed rather than done.

**Claim discipline carried forward.** Twenty to a hundred wet-lab results cannot retrain
ESM2 or meaningfully move an XGBoost classifier trained on 845 sequences. What they support
is recalibration and exclusion. Say that. "Our model learns from every experiment" would not
survive a rigorous judge, and would undo the credibility the honest framing has bought
everywhere else in this project.

**Biggest risk is regression.** A verified working product already exists and it is the
asset. Auth is additive, the verified core is untouched, and there is a 07:00 stop rule.
