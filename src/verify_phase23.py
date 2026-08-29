"""Phase 2 + 3 exit criteria. Run: python src/verify_phase23.py

Phase 2: score.py returns P(active)/P(toxic) for a sequence in under a second (warm).
Phase 3: greedy selection demonstrably suppresses near-duplicates, marginal gains are
         non-increasing (submodularity visible in the output), and the ranking is
         deterministic across runs.
"""
from __future__ import annotations

import sys
import time

import numpy as np

import config as C
from score import score_frame, score_one
from select import compute_q, fast_greedy_map, select, top_n

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print("  %s  %s%s" % ("PASS" if cond else "FAIL", name,
                          ("  -- " + detail) if detail and not cond else
                          ("  (" + detail + ")" if detail else "")))
    if not cond:
        failures.append(name)


MAGAININ = "GIGKFLHSAKKFGKAFVGEIMNS"

print("\n[1] phase 2 - models load and score")
for species in C.PRIORITY_SPECIES:
    r = score_one(MAGAININ, species)
    ok = 0.0 <= r["p_active"] <= 1.0 and 0.0 <= r["p_toxic"] <= 1.0
    check("score against %s" % species, ok,
          "P(act)=%.3f P(tox)=%.3f" % (r["p_active"], r["p_toxic"]))

print("\n[2] phase 2 - warm scoring latency")
score_one(MAGAININ, "Escherichia coli")  # warm the caches
start = time.time()
for _ in range(10):
    score_one(MAGAININ, "Escherichia coli")
warm = (time.time() - start) / 10
check("cached sequence scores in < 1s", warm < 1.0, "%.1f ms" % (warm * 1000))

# The first uncached sequence pays a one-off ESM2 load. In the app that happens at
# startup, not per request, so time the steady state and report the cold start apart.
start = time.time()
score_one("KWKLFKKIGAVLKVLWWQ", "Escherichia coli")
cold = time.time() - start
start = time.time()
for i in range(5):
    score_one("KWKLFKKIGAVLKVLWW" + "ACDEF"[i], "Escherichia coli")
live = (time.time() - start) / 5
print("      (one-off ESM2 load on first what-if: %.0f ms)" % (cold * 1000))
check("uncached what-if sequence scores in < 1s once ESM2 is warm", live < 1.0,
      "%.1f ms" % (live * 1000))

print("\n[3] phase 3 - q_i formula (Decision 3)")
q = compute_q(np.array([0.9, 0.5]), np.array([0.1, 0.5]))
check("q = P(active) * (1 - P(toxic))", np.allclose(q, [0.81, 0.25]))
check("theta>1 sharpens quality",
      compute_q(np.array([0.5]), np.array([0.5]), theta=2.0)[0] < 0.25 + 1e-9)
check("theta<1 softens quality",
      compute_q(np.array([0.5]), np.array([0.5]), theta=0.5)[0] > 0.25)
check("q never hits zero (log stays finite)",
      np.isfinite(np.log(compute_q(np.array([0.0]), np.array([1.0])))).all())

print("\n[4] phase 3 - THE DIVERSITY TEST (plan.md exit criterion)")
# A synthetic pool: five near-identical copies of one strong peptide, plus a set of
# genuinely different ones. Top-N should hoard the duplicates; greedy must not.
rng = np.random.default_rng(C.RANDOM_SEED)
dim = 64
base = rng.normal(size=dim)
dupes = np.array([base + 0.001 * rng.normal(size=dim) for _ in range(5)])
others = rng.normal(size=(25, dim))
pool = np.vstack([dupes, others])
pool = np.maximum(pool, 0.0)
pool /= np.maximum(np.linalg.norm(pool, axis=1, keepdims=True), 1e-12)

# Give the five duplicates the highest quality, so a pure score sort grabs all of them.
p_active = np.concatenate([np.full(5, 0.99), rng.uniform(0.55, 0.95, size=25)])
p_toxic = np.concatenate([np.full(5, 0.01), rng.uniform(0.05, 0.45, size=25)])

result = select(pool, p_active, p_toxic, k=10, theta=1.0)
greedy_dupes = sum(1 for i in result["selected"] if i < 5)
topn_dupes = sum(1 for i in result["baseline_top_n"] if i < 5)
print("      top-N picked %d/5 duplicates; greedy picked %d/5" % (topn_dupes, greedy_dupes))
check("top-N hoards the duplicates (the failure mode we fix)", topn_dupes == 5)
check("greedy does NOT take all five duplicates", greedy_dupes < 5)
check("greedy still takes the best duplicate", greedy_dupes >= 1)

print("\n[5] phase 3 - submodularity and correctness")
gains = np.array(result["marginal_gains"])
check("marginal gains are non-increasing (diminishing returns)",
      bool(np.all(np.diff(gains) <= 1e-9)),
      "first=%.4f last=%.4f" % (gains[0], gains[-1]))
check("selection is exactly k", len(result["selected"]) == 10)
check("no duplicate picks", len(set(result["selected"])) == 10)
check("log det is the sum of marginal gains",
      abs(result["logdet"] - gains.sum()) < 1e-9)

again = select(pool, p_active, p_toxic, k=10, theta=1.0)
check("selection is deterministic", again["selected"] == result["selected"])

# Brute-force the exact optimum on a small instance and confirm greedy is within 1-1/e.
small = pool[:12]
qs = compute_q(p_active[:12], p_toxic[:12])
V = small * qs[:, None]
K = V @ V.T + np.eye(12)
from itertools import combinations
best = max(np.linalg.slogdet(K[np.ix_(c, c)])[1] for c in combinations(range(12), 4))
g_idx, g_gains = fast_greedy_map(V, 4, tie_break=qs)
got = float(np.sum(g_gains))
exact = float(np.linalg.slogdet(K[np.ix_(g_idx, g_idx)])[1])
check("incremental Cholesky matches a direct slogdet", abs(got - exact) < 1e-6,
      "greedy=%.6f direct=%.6f" % (got, exact))
check("greedy achieves >= (1-1/e) of the brute-force optimum",
      got >= (1 - 1 / np.e) * best - 1e-9, "greedy=%.4f optimum=%.4f" % (got, best))

print("\n[6] phase 3 - end to end on real peptides")
index, raw_all, norm_all = None, None, None
cache = np.load(C.EMBEDDING_CACHE, allow_pickle=True)
seqs = [str(s) for s in cache["sequences"]][:400]
scored = score_frame(seqs, "Escherichia coli")
real = select(scored["embeddings_normalized"], scored["p_active"], scored["p_toxic"], k=20)
sims = np.array(real["nearest_selected_similarity"][1:])
top_idx = top_n(real["q"], 20)
emb = scored["embeddings_normalized"]
topn_sims = [float(np.max(emb[top_idx[:i]] @ emb[top_idx[i]])) for i in range(1, 20)]
print("      mean similarity-to-nearest-selected: greedy %.3f vs top-N %.3f"
      % (sims.mean(), np.mean(topn_sims)))
check("greedy shortlist is less internally redundant than top-N",
      sims.mean() < np.mean(topn_sims))
check("shortlist has 20 distinct peptides", len(set(real["selected"])) == 20)

print("\n" + "=" * 62)
if failures:
    print("PHASES 2-3 INCOMPLETE - %d check(s) failed:" % len(failures))
    for f in failures:
        print("  - %s" % f)
    sys.exit(1)
print("PHASES 2 AND 3 COMPLETE - all checks passed.")
