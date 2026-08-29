"""Reviewer audit of the phase-4 validation result.

Not part of the pipeline. Answers three questions the single reported number cannot:
  1. Is greedy-loses-to-top-N stable, or is it one unlucky draw?
  2. Does it hold across species and theta?
  3. Raw hit count is the metric top-N optimises by construction. Does diversity buy
     what it is actually supposed to buy -- coverage of distinct active chemotypes?
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering

import config as C
from score import score_frame, species_slug
from select import select


def clean_pool(species: str, n_decoys: int, seed: int):
    """Test-split sequences (never trained on) plus decoys with no label for this species."""
    slug = species_slug(species)
    tr = pd.read_parquet(C.LABELS / ("activity_%s_train.parquet" % slug))
    va = pd.read_parquet(C.LABELS / ("activity_%s_val.parquet" % slug))
    te = pd.read_parquet(C.LABELS / ("activity_%s_test.parquet" % slug))
    seen = set(tr["normalized_sequence"]) | set(va["normalized_sequence"]) | set(te["normalized_sequence"])

    cache = np.load(C.EMBEDDING_CACHE, allow_pickle=True)
    universe = [str(s) for s in cache["sequences"]]
    unlabeled = [s for s in universe if s not in seen]

    rng = np.random.default_rng(seed)
    decoys = list(rng.choice(unlabeled, size=min(n_decoys, len(unlabeled)), replace=False))
    actives = te[te["active"] == 1]["normalized_sequence"].tolist()
    inactives = te[te["active"] == 0]["normalized_sequence"].tolist()
    return actives, inactives + decoys


def cluster_map(embeddings: np.ndarray, threshold: float = 0.10):
    """Group sequences into chemotypes by cosine distance (1 - similarity)."""
    if len(embeddings) < 2:
        return np.zeros(len(embeddings), dtype=int)
    model = AgglomerativeClustering(
        n_clusters=None, distance_threshold=threshold, metric="cosine", linkage="average"
    )
    return model.fit_predict(embeddings)


def run(species: str, k: int, seed: int, theta: float = 1.0):
    actives, background = clean_pool(species, n_decoys=250, seed=seed)
    pool = actives + background
    scored = score_frame(pool, species)
    emb = scored["embeddings_normalized"]
    res = select(emb, scored["p_active"], scored["p_toxic"], k=k, theta=theta)

    hidden = set(actives)
    seqs = scored["sequences"]
    g_idx, t_idx = res["selected"][:k], res["baseline_top_n"][:k]
    g_hits = [i for i in g_idx if seqs[i] in hidden]
    t_hits = [i for i in t_idx if seqs[i] in hidden]

    # chemotype coverage: how many DISTINCT active clusters did each method reach
    active_rows = [i for i, s in enumerate(seqs) if s in hidden]
    labels = cluster_map(emb[active_rows])
    row_to_cluster = {r: int(c) for r, c in zip(active_rows, labels)}
    g_clusters = {row_to_cluster[i] for i in g_hits}
    t_clusters = {row_to_cluster[i] for i in t_hits}

    return {
        "species": species, "seed": seed, "theta": theta,
        "pool": len(pool), "n_actives": len(actives),
        "g_hits": len(g_hits), "t_hits": len(t_hits),
        "g_clusters": len(g_clusters), "t_clusters": len(t_clusters),
        "total_clusters": len(set(labels)),
        "g_toxic": float(np.mean(scored["p_toxic"][g_idx])),
        "t_toxic": float(np.mean(scored["p_toxic"][t_idx])),
    }


print("\n=== raw hits and chemotype coverage, k=20, clean pool ===")
print("%-26s %4s | %5s %5s | %8s %8s %6s | %6s %6s"
      % ("species", "seed", "gHit", "tHit", "gClust", "tClust", "total", "gTox", "tTox"))
rows = []
for sp in C.PRIORITY_SPECIES:
    for seed in (17, 23, 41):
        try:
            r = run(sp, k=20, seed=seed)
        except Exception as exc:
            print("%-26s skipped (%s)" % (sp, str(exc)[:40]))
            continue
        rows.append(r)
        print("%-26s %4d | %5d %5d | %8d %8d %6d | %.3f  %.3f"
              % (sp, seed, r["g_hits"], r["t_hits"], r["g_clusters"],
                 r["t_clusters"], r["total_clusters"], r["g_toxic"], r["t_toxic"]))

df = pd.DataFrame(rows)
print("\n=== aggregate over %d runs ===" % len(df))
print("mean raw hits        greedy %.2f   top-N %.2f" % (df.g_hits.mean(), df.t_hits.mean()))
print("mean chemotypes hit  greedy %.2f   top-N %.2f" % (df.g_clusters.mean(), df.t_clusters.mean()))
print("mean P(toxic)        greedy %.3f  top-N %.3f" % (df.g_toxic.mean(), df.t_toxic.mean()))
print("greedy wins on raw hits:   %d/%d" % (int((df.g_hits > df.t_hits).sum()), len(df)))
print("greedy wins on chemotypes: %d/%d" % (int((df.g_clusters > df.t_clusters).sum()), len(df)))
print("greedy ties on chemotypes: %d/%d" % (int((df.g_clusters == df.t_clusters).sum()), len(df)))

print("\n=== theta sweep, E. coli, averaged over 3 seeds ===")
print("theta |  gHit  tHit | gClust tClust")
for th in (0.2, 0.5, 1.0, 2.0):
    rs = [run("Escherichia coli", k=20, seed=s, theta=th) for s in (17, 23, 41)]
    print("%5.1f | %5.1f %5.1f | %6.1f %6.1f"
          % (th, np.mean([r["g_hits"] for r in rs]), np.mean([r["t_hits"] for r in rs]),
             np.mean([r["g_clusters"] for r in rs]), np.mean([r["t_clusters"] for r in rs])))
