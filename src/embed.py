"""Phase 2 - ESM2 embeddings, mean-pooled, cached by normalized_sequence.

Embeds every standard-amino-acid sequence in peptide_master.csv with a SMALL ESM2
variant (35M by default; never 3B - research_findings section 4), mean-pools over
residues, and caches to data/processed/embeddings.npz.

Two consumers, two conventions:
  raw        -> the classifiers (phase 2) use the plain mean-pooled vector
  normalized -> the selection kernel (phase 3) uses ReLU then L2 unit-norm, the
                SubMo-GNN convention. Skipping this makes the log-det objective
                favour large-norm vectors and diversity silently breaks.

Run: python src/embed.py
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
import torch

import config as C
from peptides import is_standard_peptide

BATCH_TOKENS = 8192  # cap per batch so long peptides do not blow memory


def load_sequences() -> list[str]:
    master = pd.read_csv(C.MASTER_CSV, **C.CSV_READ_KWARGS)
    seqs = master["normalized_sequence"].dropna().unique().tolist()
    keep = sorted({s.strip().upper() for s in seqs if is_standard_peptide(s)})
    print("  %d unique sequences in master, %d embeddable (standard AAs, len>=%d)"
          % (len(seqs), len(keep), C.MIN_PEPTIDE_LEN))
    return keep


def embed(sequences: list[str], model_name: str = C.ESM_MODEL) -> np.ndarray:
    import esm

    print("  loading %s ..." % model_name)
    model, alphabet = getattr(esm.pretrained, model_name)()
    model.eval()
    converter = alphabet.get_batch_converter()
    layer = model.num_layers
    dim = model.embed_dim
    print("  %d layers, %d dims" % (layer, dim))

    # Length-sorted batching keeps padding waste low.
    order = np.argsort([len(s) for s in sequences])
    out = np.zeros((len(sequences), dim), dtype=np.float32)

    batch: list[int] = []
    done = 0
    start = time.time()

    def flush(idxs: list[int]) -> None:
        nonlocal done
        if not idxs:
            return
        data = [("s%d" % i, sequences[i]) for i in idxs]
        _, _, tokens = converter(data)
        with torch.no_grad():
            reps = model(tokens, repr_layers=[layer])["representations"][layer]
        for row, i in enumerate(idxs):
            n = len(sequences[i])
            # tokens are [BOS] residues... [EOS]; pool residues only
            out[i] = reps[row, 1:n + 1].mean(0).numpy()
        done += len(idxs)
        if done % 1000 < len(idxs):
            rate = done / max(time.time() - start, 1e-9)
            print("    %d/%d  (%.0f seq/s)" % (done, len(sequences), rate))

    for i in order:
        longest = max([len(sequences[j]) for j in batch] + [len(sequences[i])]) + 2
        if batch and longest * (len(batch) + 1) > BATCH_TOKENS:
            flush(batch)
            batch = []
        batch.append(int(i))
    flush(batch)

    print("  embedded %d sequences in %.1fs" % (len(sequences), time.time() - start))
    return out


def normalize_for_selection(matrix: np.ndarray) -> np.ndarray:
    """ReLU then L2 unit-normalise. Required before the log-det selection kernel."""
    relu = np.maximum(matrix, 0.0)
    norms = np.linalg.norm(relu, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (relu / norms).astype(np.float32)


def main() -> None:
    print("\n[1] collecting sequences")
    sequences = load_sequences()

    print("\n[2] embedding")
    raw = embed(sequences)

    print("\n[3] normalising for the selection kernel")
    norm = normalize_for_selection(raw)
    unit = np.linalg.norm(norm, axis=1)
    nonzero = unit > 0
    print("  %d/%d vectors are unit-norm after ReLU+L2 (rest were all-negative)"
          % (int(np.isclose(unit[nonzero], 1.0).sum()), len(unit)))

    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        C.EMBEDDING_CACHE,
        sequences=np.array(sequences, dtype=object),
        raw=raw,
        normalized=norm,
        model=C.ESM_MODEL,
    )
    print("\n  wrote %s  (%d x %d)" % (C.EMBEDDING_CACHE.name, raw.shape[0], raw.shape[1]))
    print("\nEMBEDDINGS COMPLETE")


if __name__ == "__main__":
    main()
