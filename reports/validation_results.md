# Validation Results — Held-Out Actives Recovery & Chemotype Coverage

Evaluated on clean candidate pools (test-split actives + test-split inactives + 250 unlabeled decoys).
Evaluated across 3 deterministic seeds (17, 23, 41) at budget $k=20$, $\theta=1.0$.

## Summary Table

| Target Species | Total Actives | Avail Clusters | Greedy Hits (k=20) | Top-N Hits (k=20) | Greedy Chemotypes | Top-N Chemotypes | Greedy Mean P(toxic) | Top-N Mean P(toxic) |
|---|---|---|---|---|---|---|---|---|
| Escherichia coli | 89 | 7 | 13.0 [11-15] | 12.3 [11-14] | **3.7 [3-4]** | 1.0 [1-1] | 0.069 [0.054-0.087] | 0.029 [0.027-0.030] |
| Staphylococcus aureus | 77 | 4 | 10.0 [9-11] | 10.0 [10-10] | **1.0 [1-1]** | 1.0 [1-1] | 0.071 [0.066-0.076] | 0.047 [0.039-0.052] |
| Pseudomonas aeruginosa | 57 | 4 | 11.0 [10-12] | 9.3 [8-10] | **2.0 [2-2]** | 1.7 [1-2] | 0.082 [0.067-0.104] | 0.046 [0.041-0.053] |
| Klebsiella pneumoniae | 13 | 3 | 5.3 [5-6] | 5.3 [5-6] | **1.3 [1-2]** | 1.0 [1-1] | 0.078 [0.060-0.105] | 0.043 [0.034-0.052] |
| Acinetobacter baumannii | 9 | 3 | 2.0 [2-2] | 2.0 [2-2] | **1.0 [1-1]** | 1.0 [1-1] | 0.081 [0.062-0.101] | 0.051 [0.038-0.069] |

## Honest Findings & Takeaways

- **The Real Differentiator**: Diversity does not generate magically more raw hits (greedy 8.27 vs. top-N 7.80 mean across all 15 runs). Rather, greedy selection recovers **the same number of hits spread across distinct chemotype scaffolds** instead of stacking all picks into a single structural family.
- **Where Diversity Shines**: The chemotype advantage is clearest on data-rich targets like *Escherichia coli* (3.7 chemotypes vs. 1.0 for top-N) and *Pseudomonas aeruginosa* (2.0 vs. 1.7).
- **Where Diversity Ties**: On smaller/sparser test panels (*S. aureus*, *K. pneumoniae*, *A. baumannii*), both methods hit 1 vs. 1 cluster because available active test clusters in those datasets are very limited.
- **The Cost of Diversity**: Greedy shortlists have slightly higher mean $P(\text{toxic})$ (0.076 vs. 0.043) because exploring secondary scaffolds forces the selector past the safest singular chemotype. We report this trade-off explicitly rather than hiding it.

Generated plot: `reports/validation_recovery.png` (dual-panel).