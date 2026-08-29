# Data sources and attribution

This repository redistributes data derived from public antimicrobial peptide databases
for reproducibility. All credit belongs to the original authors, and their terms govern
any downstream use. If you use this work, cite the sources below, not this repository.

## Databases

**DBAASP — Database of Antimicrobial Activity and Structure of Peptides**
Activity measurements (MIC/MBC by target species) and haemolysis measurements.
https://dbaasp.org
Pirtskhalava M. et al., *Nucleic Acids Research* 49(D1):D288–D297, 2021.
Files: `data/raw/activity-against-target-species.csv`,
`data/raw/hemolytic-and-cytotoxic-activities.csv`, and the `dbaasp_*` tables in
`data/processed/`.

**DRAMP 4.0 — Data Repository of Antimicrobial Peptides**
Peptide records, annotations and PDB cross-references. Released CC-BY.
http://dramp.cpu-bioinfor.org
Shi G. et al., *Nucleic Acids Research* 53(D1):D403–D410, 2025.
Files: `data/raw/general_amps.xlsx`, `data/processed/dramp_toxicity_experimental.csv`.

**RCSB Protein Data Bank** — experimental structures fetched on demand by PDB ID.
https://www.rcsb.org

**PubMed / NCBI E-utilities** — literature retrieved live at request time. Nothing from
PubMed is stored in this repository.

## Models and tools

**ESM2** (`esm2_t12_35M_UR50D`) — Lin Z. et al., *Science* 379:1123–1130, 2023.
Weights are downloaded at first run and are not redistributed here.
https://github.com/facebookresearch/esm

**ESMFold via the ESM Atlas API** — used for structure prediction where no experimental
structure exists. https://esmatlas.com

## Method references

Nemhauser G., Wolsey L., Fisher M. (1978) — the 1 − 1/e greedy bound for monotone
submodular maximisation under a cardinality constraint.

Kulesza A., Taskar B. (2012) — *Determinantal Point Processes for Machine Learning*,
arXiv:1207.6083.

SubMo-GNN — diverse molecule selection via log-determinant objectives,
*Scientific Reports* 12, 1027 (2022). Source of the ReLU + L2 normalisation convention
applied to embeddings before selection.

## Scope

This is a research-support prototype built for a hackathon. It is not a medical device
and its predictions are not clinical advice.
