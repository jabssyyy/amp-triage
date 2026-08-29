"""Phase 3 - q_i and log-determinant greedy selection under a cardinality budget.

The objective (research_findings section 1):

    log det(L_A) = 2 * sum_i log(q_i) + log det(S_A)

with L = diag(q) S diag(q), quality times diversity. We maximise the REGULARISED
form log det(L_A + I), because log det(K_S) is monotone submodular iff the smallest
eigenvalue of K is at least 1, and L + I guarantees that unconditionally. Greedy then
carries the Nemhauser-Wolsey-Fisher 1 - 1/e bound -- with respect to the
log-determinant objective, NOT "63% of optimal diversity". Say it precisely.

Since (L + I)_A = L_A + I, maximising log det(L_A + I) is just greedy MAP inference
on the kernel K = L + I, which is what fast_greedy_map does.

Implementation note: L = V V^T where v_i = q_i * e_i and e_i is the ReLU'd,
L2-normalised ESM2 embedding. We never materialise the n x n kernel -- columns are
formed on demand as V @ v_j, so memory is O(n*d) not O(n^2). The incremental Cholesky
gives O(n * k^2), not the O(n * k^4) of recomputing a determinant per pick.

Run: python src/select.py --pool candidates.csv --species "Escherichia coli" --k 20
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

import config as C


def compute_q(p_active: np.ndarray, p_toxic: np.ndarray, theta: float = C.DEFAULT_THETA) -> np.ndarray:
    """q_i = (P(active) * (1 - P(toxic))) ** theta   -- Decision 3, locked.

    Read as the approximate probability of being both active and safe (treating the
    two as roughly independent). theta sharpens (>1) or softens (<1) quality's pull
    against diversity. Clipped away from zero so log(q) stays finite.
    """
    q = np.asarray(p_active, dtype=np.float64) * (1.0 - np.asarray(p_toxic, dtype=np.float64))
    q = np.clip(q, 1e-12, 1.0)
    return q ** float(theta)


def fast_greedy_map(
    V: np.ndarray, k: int, tie_break: np.ndarray | None = None
) -> tuple[list[int], list[float]]:
    """Greedy maximisation of log det(K_A) for K = V V^T + I.

    Incremental Cholesky (Chen et al. 2018): maintain per-item residual variance
    d_i^2 and the rows c_i of the partial Cholesky factor. Each pick costs one
    kernel column and one rank-1 update.

    Returns (selected indices, marginal log-gain at each pick). The gains are
    non-increasing -- that is submodularity showing up in the output, and it is
    worth printing when someone asks whether the diversity term is really on.
    """
    n = V.shape[0]
    k = min(k, n)
    if k <= 0:
        return [], []

    # K_ii = ||v_i||^2 + 1
    d2 = np.einsum("ij,ij->i", V, V) + 1.0
    c = np.zeros((n, k), dtype=np.float64)
    selected: list[int] = []
    gains: list[float] = []
    remaining = np.ones(n, dtype=bool)

    for t in range(k):
        masked = np.where(remaining, d2, -np.inf)
        best = float(masked.max())
        if not np.isfinite(best) or best <= 0:
            break
        # Deterministic tie-break: among items within a hair of the best gain,
        # take the highest q. Keeps runs reproducible.
        close = np.flatnonzero(remaining & (d2 >= best - 1e-12))
        if len(close) > 1 and tie_break is not None:
            j = int(close[np.argmax(tie_break[close])])
        else:
            j = int(close[0])

        selected.append(j)
        gains.append(float(np.log(d2[j])))
        remaining[j] = False
        if t == k - 1 or not remaining.any():
            break

        dj = np.sqrt(d2[j])
        # kernel column: K_ji = v_j . v_i  (+1 on the diagonal, which we skip since
        # j is already selected and never re-evaluated)
        kj = V @ V[j]
        e = (kj - c[:, :t] @ c[j, :t]) / dj
        c[:, t] = e
        d2 = d2 - e ** 2
        d2[~remaining] = -np.inf
        np.maximum(d2, 1e-12, out=d2, where=remaining)

    return selected, gains


def top_n(q: np.ndarray, k: int) -> list[int]:
    """The baseline everyone else uses: take the k highest scorers."""
    return list(np.argsort(-q)[:k])


def select(
    embeddings: np.ndarray,
    p_active: np.ndarray,
    p_toxic: np.ndarray,
    k: int = C.DEFAULT_K,
    theta: float = C.DEFAULT_THETA,
) -> dict:
    """Run the full selection. `embeddings` must already be ReLU'd and L2-normalised.

    Returns BOTH forms of q, and they are not interchangeable:
      "q"        raw P(active) * (1 - P(toxic)) -- interpretable, this is what a UI shows
      "q_scaled" q ** theta -- an internal detail of the objective. Displaying this
                 would show tiny numbers at high theta and read as a bug.
    """
    q_raw = np.clip(
        np.asarray(p_active, dtype=np.float64) * (1.0 - np.asarray(p_toxic, dtype=np.float64)),
        1e-12, 1.0,
    )
    q = compute_q(p_active, p_toxic, theta)
    V = embeddings * q[:, None]
    picks, gains = fast_greedy_map(V, k, tie_break=q)

    # similarity of each pick to the nearest previously selected peptide -- the number
    # the UI shows to answer "why both and not two copies of the better one"
    nearest = []
    for i, idx in enumerate(picks):
        if i == 0:
            nearest.append(0.0)
        else:
            prev = embeddings[picks[:i]]
            nearest.append(float(np.max(prev @ embeddings[idx])))

    return {
        "selected": picks,
        "q": q_raw,
        "q_scaled": q,
        "theta": float(theta),
        "marginal_gains": gains,
        "logdet": float(np.sum(gains)),
        "nearest_selected_similarity": nearest,
        # top-N ranks by raw q; x**theta is monotonic for theta > 0 so the order is
        # identical either way, but raw q is the honest description of the baseline.
        "baseline_top_n": top_n(q_raw, k),
    }


def _load_pool(path: str) -> pd.DataFrame:
    pool = pd.read_csv(path)
    needed = {"normalized_sequence"}
    if not needed <= set(pool.columns):
        raise SystemExit("pool CSV needs a normalized_sequence column")
    return pool


def main() -> None:
    ap = argparse.ArgumentParser(description="Diversity-aware shortlist selection")
    ap.add_argument("--pool", required=True, help="CSV with a normalized_sequence column")
    ap.add_argument("--species", required=True, choices=list(C.PRIORITY_SPECIES))
    ap.add_argument("--k", type=int, default=C.DEFAULT_K)
    ap.add_argument("--theta", type=float, default=C.DEFAULT_THETA)
    ap.add_argument("--out", default=None, help="where to write the shortlist CSV")
    args = ap.parse_args()

    from score import score_frame  # local import: score.py needs trained models

    pool = _load_pool(args.pool)
    scored = score_frame(pool["normalized_sequence"].tolist(), args.species)
    emb = scored["embeddings_normalized"]
    result = select(emb, scored["p_active"], scored["p_toxic"], k=args.k, theta=args.theta)

    picks = result["selected"]
    out = pd.DataFrame({
        "rank": range(1, len(picks) + 1),
        "normalized_sequence": [scored["sequences"][i] for i in picks],
        "q_i": result["q"][picks],
        "q_i_scaled": result["q_scaled"][picks],
        "p_active": scored["p_active"][picks],
        "p_toxic": scored["p_toxic"][picks],
        "marginal_log_gain": result["marginal_gains"],
        "similarity_to_nearest_selected": result["nearest_selected_similarity"],
    })
    dest = args.out or "shortlist.csv"
    out.to_csv(dest, index=False)
    print(out.to_string(index=False))
    print("\nlog det(L_A + I) = %.4f   (k=%d, theta=%.2f)" % (result["logdet"], args.k, args.theta))
    print("wrote %s" % dest)


if __name__ == "__main__":
    main()
