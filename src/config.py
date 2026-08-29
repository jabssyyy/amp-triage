"""Locked constants and paths for the AMP triage pipeline.

Every threshold here is a decision recorded in context.md / plan.md.
Do not change a value without also updating its justification string.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
LABELS = DATA / "labels"
MODELS = ROOT / "models"
REPORTS = ROOT / "reports"

ACTIVITY_CSV = PROCESSED / "dbaasp_activity_experimental.csv"
LYSIS_CSV = PROCESSED / "dbaasp_lysis_experimental.csv"
MASTER_CSV = PROCESSED / "peptide_master.csv"
DRAMP_CSV = PROCESSED / "dramp_toxicity_experimental.csv"  # NOT a label source

# The processed CSVs are not clean UTF-8 (micro sign arrives mojibaked),
# so every read must be tolerant and every unit match substring-based.
CSV_READ_KWARGS = dict(low_memory=False, encoding="utf-8", encoding_errors="replace")

# --- Locked label decisions (28 Aug 2026) -----------------------------------

ACTIVITY_MEASURES = ("MIC", "MBC")
ACTIVITY_THRESHOLD_UGML = 32.0
ACTIVITY_THRESHOLD_JUSTIFICATION = (
    "MIC <= 32 ug/ml is the common antibacterial-activity convention named as the "
    "candidate breakpoint in plan.md phase 1. Verified against the data on 28 Aug 2026: "
    "yields 51-74% active across the five priority species (E. coli 62.4%, S. aureus 62.3%, "
    "P. aeruginosa 60.5%, K. pneumoniae 51.4%, A. baumannii 73.9%), all inside the 85/15 "
    "class-balance gate. A 16 ug/ml cut was also measured (~50/50) and kept as a sensitivity option."
)

TOXICITY_TARGET_CELL = "Human erythrocytes"
TOXICITY_HEMOLYSIS_PCT = 50.0
TOXICITY_REF_DOSE_UGML = 100.0
TOXICITY_LABEL_JUSTIFICATION = (
    "The lysis table stores (effect level, dose that produced it), NOT (dose, percent). "
    "So the label is dose-anchored: toxic = reaches >=50% hemolysis of human erythrocytes at "
    "a dose <= 100 ug/ml; safe = tested at >= 100 ug/ml without ever reaching 50%; everything "
    "else is unlabeled and dropped. The 100 ug/ml reference matches the dataset's own Notes "
    "convention ('Not active up to 100 micro g/ml'). Verified 28 Aug 2026: 270 labeled "
    "sequences, 36.3% toxic."
)

# WHO priority pathogens with enough data to train. The first three are data-rich
# (~700-1000 sequences each); the last two are WHO critical-priority and smaller.
PRIORITY_SPECIES = (
    "Escherichia coli",
    "Staphylococcus aureus",
    "Pseudomonas aeruginosa",
    "Klebsiella pneumoniae",
    "Acinetobacter baumannii",
)
MIN_SEQS_PER_SPECIES = 50

# ESM2: small variant only. Never 3B (research_findings section 4).
ESM_MODEL = "esm2_t12_35M_UR50D"
EMBEDDING_CACHE = PROCESSED / "embeddings.npz"

# Peptides shorter than this are junk rows, not peptides.
MIN_PEPTIDE_LEN = 5

# Selection engine defaults (phase 3).
DEFAULT_K = 20
DEFAULT_THETA = 1.0

RANDOM_SEED = 17
