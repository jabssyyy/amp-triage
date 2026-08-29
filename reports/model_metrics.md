# Model metrics - phase 2

ESM2 esm2_t12_35M_UR50D, mean-pooled (480 dims). XGBoost, depth 4, 300 trees, class-weighted.
CV is 5-fold stratified on train+val. Because phase 1 collapses every peptide to a
single labeled row, ordinary stratified CV is already sequence-aware - no peptide can
appear on both sides of a fold. TEST is the phase-1 held-out split, scored once.

## Activity - P(active), MIC <= 32 ug/ml

| Species | train | test | CV ROC-AUC | CV PR-AUC | test ROC-AUC | test PR-AUC | PR baseline |
|---|---|---|---|---|---|---|---|
| Escherichia coli | 845 | 150 | 0.817 +/- 0.032 | 0.862 +/- 0.027 | 0.797 | 0.835 | 0.593 |
| Staphylococcus aureus | 804 | 142 | 0.732 +/- 0.028 | 0.787 +/- 0.030 | 0.795 | 0.826 | 0.542 |
| Pseudomonas aeruginosa | 599 | 106 | 0.818 +/- 0.033 | 0.858 +/- 0.023 | 0.812 | 0.829 | 0.538 |
| Klebsiella pneumoniae | 155 | 28 | 0.746 +/- 0.053 | 0.721 +/- 0.074 | 0.805 | 0.743 | 0.464 |
| Acinetobacter baumannii | 90 | 15 | 0.586 +/- 0.112 | 0.787 +/- 0.061 | 0.722 | 0.864 | 0.600 |

## Toxicity - P(toxic), >=50% hemolysis of human RBC at <= 100 ug/ml

| train | test | CV ROC-AUC | CV PR-AUC | test ROC-AUC | test PR-AUC | PR baseline |
|---|---|---|---|---|---|---|
| 231 | 41 | 0.849 +/- 0.052 | 0.810 +/- 0.044 | 0.849 | 0.701 | 0.342 |

## Read this honestly

- The three data-rich species (E. coli, S. aureus, P. aeruginosa) sit at ROC-AUC
  0.73-0.82 CV and 0.79-0.81 on held-out test. CV and test agree, so the models are
  not overfit to the split.
- **Acinetobacter baumannii is weak and should be labelled as such in the UI.** CV
  ROC-AUC 0.586 +/- 0.112 is barely above chance with error bars that cross it. Its
  test score of 0.722 comes from 15 sequences and means very little. Klebsiella
  pneumoniae is borderline (CV 0.746 +/- 0.053, 155 training sequences).
- Toxicity is the strongest model (CV 0.849 +/- 0.053, test 0.849) despite only 231
  training sequences, and CV and test agree exactly. Still quote the standard
  deviation, never the mean alone - 231 sequences is a small base.
- PR-AUC should always be read against its baseline (the positive rate), given in the
  last column. A PR-AUC of 0.86 against a 0.59 baseline is a real lift; the same
  number against a 0.85 baseline would not be.