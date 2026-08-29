"""Scientist-Assistant Analytics, Physics, and Live Literature Grounding.

Implements deterministic peptide physics, helical-wheel geometry, hydrophobic
moment vectors, multi-tier structure resolution, and live PubMed evidence retrieval.

Strict Evidence Rules:
1. Zero fabricated citations: Every paper must be retrieved live from NCBI PubMed E-utilities.
2. Real excerpts: Abstracts are extracted verbatim from NCBI XML without synthesized text.
3. Real mechanism extraction: Mechanism terms are extracted strictly from retrieved text.
4. If no papers are found or NCBI is unreachable, returns an empty list with explicit status.
"""
from __future__ import annotations

import json
import math
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import numpy as np

SRC_DIR = Path(__file__).resolve().parent
import config as C
from peptides import is_standard_peptide


# --- 1. Constants & Biophysical Scales ---------------------------------------

# Eisenberg consensus hydrophobicity scale (Eisenberg et al. 1984, PNAS)
EISENBERG_SCALE: dict[str, float] = {
    "I": 0.73, "F": 0.61, "V": 0.54, "L": 0.53, "W": 0.37,
    "M": 0.26, "A": 0.25, "G": 0.16, "C": 0.04, "T": -0.18,
    "S": -0.26, "Y": -0.00, "P": -0.07, "H": -0.40, "Q": -0.69,
    "N": -0.64, "E": -0.62, "K": -1.10, "D": -0.72, "R": -1.76,
}

# EMBOSS standard pKa values
PKA_VALUES = {
    "N_term": 9.69,
    "C_term": 2.34,
    "K": 10.53,
    "R": 12.48,
    "H": 6.00,
    "D": 3.86,
    "E": 4.25,
    "C": 8.33,
    "Y": 10.07,
}

HYDROPHOBIC_RESIDUES = set("AVILMFWP")
CATIONIC_RESIDUES = set("KRH")
ANIONIC_RESIDUES = set("DE")
POLAR_RESIDUES = set("STNQYG")

# Antimicrobial resistance and membrane mechanism keyword patterns
MECHANISM_PATTERNS = [
    ("Lipid A modification / charge alteration", re.compile(r"\b(lipid\s*A|pmr[AB]|pho[PQ]|arn[A-T]|aminoarabinose|phosphoethanolamine)\b", re.IGNORECASE)),
    ("MprF lysinylation / surface charge repulsion", re.compile(r"\b(mprF|lysyl|lysinylation|dlt[A-D]|teichoic)\b", re.IGNORECASE)),
    ("Efflux pump expulsion", re.compile(r"\b(efflux|acrAB|tolC|mex[A-Z]|norA|ade[A-Z]|qac)\b", re.IGNORECASE)),
    ("Biofilm matrix sequestration", re.compile(r"\b(biofilm|extracellular polysaccharide|alginate matrix|pellicle)\b", re.IGNORECASE)),
    ("Outer membrane vesicle trapping", re.compile(r"\b(vesicle|OMV|shedding|outer membrane permeability)\b", re.IGNORECASE)),
    ("Envelope / cell wall stress response", re.compile(r"\b(envelope stress|cpx|rpoE|baeSR)\b", re.IGNORECASE)),
    ("Proteolytic degradation", re.compile(r"\b(protease|peptidase|degradation|cleavage|clpP|lon|ompt)\b", re.IGNORECASE)),
    ("Capsule polysaccharide barrier", re.compile(r"\b(capsule|capsular|polysaccharide coat|wzc|cps)\b", re.IGNORECASE)),
    ("Membrane permeabilization / pore formation", re.compile(r"\b(pore|permeabiliz|membrane disrupt|lysis|barrel-stave|toroidal|carpet model)\b", re.IGNORECASE)),
]


# --- 2. Peptide Properties & Isoelectric Point --------------------------------

def compute_net_charge(sequence: str, pH: float = 7.0) -> float:
    """Computes net charge via Henderson-Hasselbalch across charged groups at given pH."""
    seq = sequence.upper()
    charge = 1.0 / (1.0 + 10.0 ** (pH - PKA_VALUES["N_term"]))
    charge -= 1.0 / (1.0 + 10.0 ** (PKA_VALUES["C_term"] - pH))

    for aa in seq:
        if aa in ("K", "R", "H"):
            charge += 1.0 / (1.0 + 10.0 ** (pH - PKA_VALUES[aa]))
        elif aa in ("D", "E", "C", "Y"):
            charge -= 1.0 / (1.0 + 10.0 ** (PKA_VALUES[aa] - pH))

    return round(float(charge), 2)


def compute_isoelectric_point(sequence: str, tol: float = 0.01) -> float:
    """Computes exact isoelectric point (pI) by bisecting the Henderson-Hasselbalch curve."""
    low, high = 0.0, 14.0
    for _ in range(35):
        mid = (low + high) / 2.0
        q = compute_net_charge(sequence, pH=mid)
        if abs(q) < tol:
            return round(mid, 2)
        if q > 0:
            low = mid
        else:
            high = mid
    return round((low + high) / 2.0, 2)


def compute_hydrophobic_moment(sequence: str, angle_deg: float = 100.0) -> tuple[float, float, float]:
    """Computes Eisenberg hydrophobic moment (uH) and angle for an alpha-helix (100 deg/residue).

    Reference: Eisenberg et al. (1984), PNAS 81(1): 140-144.
    """
    seq = sequence.upper()
    n = len(seq)
    if n == 0:
        return 0.0, 0.0, 0.0

    delta = math.radians(angle_deg)
    vx = 0.0
    vy = 0.0

    for i, aa in enumerate(seq):
        h = EISENBERG_SCALE.get(aa, 0.0)
        theta = i * delta
        vx += h * math.cos(theta)
        vy += h * math.sin(theta)

    uH = math.sqrt(vx * vx + vy * vy) / n
    return round(float(uH), 3), vx, vy


def compute_properties(sequence: str, pH: float = 7.0) -> dict[str, Any]:
    """Calculates biochemical and structural properties for a peptide."""
    seq = sequence.strip().upper()
    if not is_standard_peptide(seq):
        raise ValueError(f"Invalid sequence containing non-standard amino acids: {sequence}")

    n = len(seq)
    charge = compute_net_charge(seq, pH=pH)
    pi = compute_isoelectric_point(seq)
    uH, _, _ = compute_hydrophobic_moment(seq)

    comp: dict[str, int] = {}
    for aa in seq:
        comp[aa] = comp.get(aa, 0) + 1

    hydrophobic_count = sum(1 for aa in seq if aa in HYDROPHOBIC_RESIDUES)
    cationic_count = sum(1 for aa in seq if aa in CATIONIC_RESIDUES)
    anionic_count = sum(1 for aa in seq if aa in ANIONIC_RESIDUES)
    polar_count = sum(1 for aa in seq if aa in POLAR_RESIDUES)

    mean_hydrophobicity = sum(EISENBERG_SCALE.get(aa, 0.0) for aa in seq) / n

    return {
        "sequence": seq,
        "length": n,
        "net_charge_pH7": charge,
        "isoelectric_point": pi,
        "hydrophobic_moment_uH": uH,
        "mean_hydrophobicity": round(mean_hydrophobicity, 3),
        "hydrophobic_fraction": round(hydrophobic_count / n, 3),
        "cationic_fraction": round(cationic_count / n, 3),
        "anionic_fraction": round(anionic_count / n, 3),
        "polar_fraction": round(polar_count / n, 3),
        "composition": comp,
    }


# --- 3. Helical Wheel SVG Generator ------------------------------------------

def get_residue_color(aa: str) -> tuple[str, str, str]:
    if aa in HYDROPHOBIC_RESIDUES:
        return "#e08700", "#a86400", "Hydrophobic"
    elif aa in CATIONIC_RESIDUES:
        return "#005ea5", "#003d6b", "Cationic (+)"
    elif aa in ANIONIC_RESIDUES:
        return "#ba1a1a", "#93000a", "Anionic (-)"
    else:
        return "#006b55", "#004536", "Polar"


def generate_helical_wheel_svg(sequence: str, size: int = 480) -> str:
    """Deterministic helical wheel with the hydrophobic moment drawn as a vector.

    Pure geometry from the sequence -- residues placed at 100 degrees per turn, which is
    the rise of an alpha helix. No prediction and no uncertainty anywhere in it.

    Layout notes, learned the hard way:
      - the moment label is offset perpendicular to the arrow, so it never lands on the
        arrow, the centre hub, or a residue;
      - the connector path is drawn first and kept faint, otherwise a 30-mer reads as a
        ball of wool;
      - legend swatches come from the same colour function as the residues, so the two
        cannot drift apart again.
    """
    seq = sequence.strip().upper()
    n = max(len(seq), 1)

    width = size
    wheel_h = size - 40
    height = wheel_h + 42
    cx = width / 2.0
    cy = wheel_h / 2.0 + 6
    base_radius = 150.0
    node_r = 16.0 if n <= 24 else 13.0
    font_aa = 13 if n <= 24 else 11

    uH, vx, vy = compute_hydrophobic_moment(seq)
    charge = compute_net_charge(seq, 7.0)

    positions = []
    for i, aa in enumerate(seq):
        rad = math.radians(-90.0 + i * 100.0)
        r = base_radius - (i // 18) * 26.0 - (i % 18) * 0.6
        positions.append((cx + r * math.cos(rad), cy + r * math.sin(rad), aa, i + 1))

    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="100%%" height="%d" '
        'preserveAspectRatio="xMidYMid meet" style="font-family: ui-sans-serif, system-ui, sans-serif;">'
        % (width, height, height),
        '<defs>',
        '  <marker id="wheelArrow" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" '
        'markerHeight="5" orient="auto-start-reverse">',
        '    <path d="M 0 1 L 10 5 L 0 9 z" fill="#7c3aed" />',
        '  </marker>',
        '</defs>',
        '<rect width="%d" height="%d" fill="#ffffff" rx="8" />' % (width, height),
        '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="#e3e8ee" stroke-width="1" '
        'stroke-dasharray="3 5" />' % (cx, cy, base_radius),
    ]

    if len(positions) > 1:
        d = " ".join(("M" if i == 0 else "L") + " %.1f %.1f" % (x, y)
                     for i, (x, y, _, _) in enumerate(positions))
        out.append('<path d="%s" fill="none" stroke="#c9d1dc" stroke-width="1" opacity="0.55" />' % d)

    if uH > 0.01:
        arrow_len = min(base_radius - 46, max(38.0, uH * 170.0))
        ang = math.atan2(vy, vx)
        ax, ay = cx + arrow_len * math.cos(ang), cy + arrow_len * math.sin(ang)
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#7c3aed" stroke-width="2.5" '
                   'marker-end="url(#wheelArrow)" opacity="0.9" />' % (cx, cy, ax, ay))
        px, py = -math.sin(ang), math.cos(ang)
        mx = cx + (arrow_len * 0.62) * math.cos(ang) + px * 17
        my = cy + (arrow_len * 0.62) * math.sin(ang) + py * 17
        out.append('<text x="%.1f" y="%.1f" fill="#6d28d9" font-size="11" font-weight="600" '
                   'text-anchor="middle" dominant-baseline="middle">\u03bcH %.2f</text>' % (mx, my, uH))

    out.append('<circle cx="%.1f" cy="%.1f" r="30" fill="#ffffff" stroke="#c0c7d4" stroke-width="1.5" />' % (cx, cy))
    out.append('<text x="%.1f" y="%.1f" fill="#707784" font-size="8" text-anchor="middle" '
               'letter-spacing="0.08em">CHARGE</text>' % (cx, cy - 7))
    out.append('<text x="%.1f" y="%.1f" fill="#161d1f" font-size="15" font-weight="700" '
               'text-anchor="middle">%+.1f</text>' % (cx, cy + 11, charge))

    for x, y, aa, pos_num in positions:
        fill, stroke, _ = get_residue_color(aa)
        out.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" stroke-width="1.5" />'
                   % (x, y, node_r, fill, stroke))
        out.append('<text x="%.1f" y="%.1f" fill="#ffffff" font-size="%d" font-weight="700" '
                   'text-anchor="middle" dominant-baseline="middle">%s</text>' % (x, y - 2, font_aa, aa))
        out.append('<text x="%.1f" y="%.1f" fill="#ffffff" opacity="0.7" font-size="7" '
                   'text-anchor="middle">%d</text>' % (x, y + node_r - 3.5, pos_num))

    leg_y = height - 14
    swatches = [("A", "Hydrophobic"), ("K", "Cationic (+)"), ("D", "Anionic (\u2212)"), ("S", "Polar")]
    span = width / len(swatches)
    for i, (probe, label) in enumerate(swatches):
        colour, _, _ = get_residue_color(probe)
        lx = span * i + 26
        out.append('<circle cx="%.1f" cy="%.1f" r="5" fill="%s" />' % (lx, leg_y, colour))
        out.append('<text x="%.1f" y="%.1f" fill="#707784" font-size="10">%s</text>'
                   % (lx + 11, leg_y + 3.5, label))

    out.append('</svg>')
    return "\n".join(out)

# --- 4. Live PubMed Grounding via NCBI E-utilities ---------------------------

_NAME_MAP_FILE = C.PROCESSED / "sequence_name_map.json"
_SEQUENCE_NAMES: dict[str, dict[str, Any]] | None = None
_LIVE_EVIDENCE_CACHE: dict[str, dict[str, Any]] = {}


def _get_name_mapping() -> dict[str, dict[str, Any]]:
    global _SEQUENCE_NAMES
    if _SEQUENCE_NAMES is None:
        if _NAME_MAP_FILE.exists():
            with open(_NAME_MAP_FILE, "r", encoding="utf-8") as f:
                _SEQUENCE_NAMES = json.load(f)
        else:
            _SEQUENCE_NAMES = {}
    return _SEQUENCE_NAMES


def _extract_mechanisms_from_text(text: str) -> list[str]:
    """Extracts resistance/mechanism tags only if explicitly present in the retrieved text."""
    found = []
    for label, pattern in MECHANISM_PATTERNS:
        if pattern.search(text):
            found.append(label)
    return found


def _first_sentences(text: str, max_sentences: int = 3) -> str | None:
    """Extracts the first 2-3 sentences verbatim from abstract text."""
    if not text or not text.strip():
        return None
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    excerpt = " ".join(sentences[:max_sentences])
    return excerpt if len(excerpt) > 20 else text.strip()


def fetch_pubmed_evidence(sequence: str, species: str) -> dict[str, Any]:
    """Retrieves real, live PubMed literature from NCBI E-utilities.

    Returns:
        {
            "status": "success" | "empty" | "unavailable",
            "match_level": "peptide" | "pathogen" | null,
            "query_used": str,
            "peptide_name": str | null,
            "papers": list[dict],
            "reason": str | null
        }
    """
    clean_seq = sequence.strip().upper()
    cache_key = f"{clean_seq}::{species}"
    if cache_key in _LIVE_EVIDENCE_CACHE:
        return _LIVE_EVIDENCE_CACHE[cache_key]

    name_map = _get_name_mapping()
    meta = name_map.get(clean_seq)
    peptide_name = meta.get("name") if meta else None

    # Step A: Attempt peptide-specific query if known name exists
    id_list: list[str] = []
    match_level = None
    query_used = ""

    if peptide_name:
        clean_name = re.sub(r"[^A-Za-z0-9\- ]", "", peptide_name).strip()
        if len(clean_name) >= 3:
            query_used = f'("{clean_name}"[Title/Abstract]) AND ("{species}"[Title/Abstract] OR "antibacterial"[Title/Abstract])'
            try:
                search_url = (
                    f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?"
                    f"db=pubmed&term={urllib.parse.quote(query_used)}&retmode=json&retmax=3"
                )
                req = urllib.request.Request(search_url, headers={"User-Agent": "AMPTriage/1.0 (academic-research-tool)"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    search_data = json.loads(resp.read().decode("utf-8"))
                id_list = search_data.get("esearchresult", {}).get("idlist", [])
                if id_list:
                    match_level = "peptide"
            except Exception:
                pass

    # Step B: Pathogen-level query fallback (tightly scoped to antimicrobial peptides)
    if not id_list:
        query_used = (
            f'("{species}"[Title/Abstract]) AND '
            f'("antimicrobial peptide"[Title/Abstract] OR "cationic antimicrobial peptide"[Title/Abstract]) AND '
            f'("activity"[Title/Abstract] OR "MIC"[Title/Abstract] OR "resistance"[Title/Abstract] OR "membrane"[Title/Abstract])'
        )
        try:
            search_url = (
                f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?"
                f"db=pubmed&term={urllib.parse.quote(query_used)}&retmode=json&retmax=3"
            )
            req = urllib.request.Request(search_url, headers={"User-Agent": "AMPTriage/1.0 (academic-research-tool)"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                search_data = json.loads(resp.read().decode("utf-8"))
            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            if id_list:
                match_level = "pathogen"
        except Exception as e:
            res_err = {
                "status": "unavailable",
                "match_level": None,
                "query_used": query_used,
                "peptide_name": peptide_name,
                "papers": [],
                "reason": f"NCBI E-utilities connection error: {e}",
            }
            return res_err

    if not id_list:
        res_empty = {
            "status": "empty",
            "match_level": None,
            "query_used": query_used,
            "peptide_name": peptide_name,
            "papers": [],
            "reason": f"No published PubMed records found matching criteria for {species}.",
        }
        _LIVE_EVIDENCE_CACHE[cache_key] = res_empty
        return res_empty

    # Step C: Fetch exact XML records via efetch.fcgi
    papers: list[dict[str, Any]] = []
    try:
        fetch_url = (
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?"
            f"db=pubmed&id={','.join(id_list)}&retmode=xml"
        )
        req2 = urllib.request.Request(fetch_url, headers={"User-Agent": "AMPTriage/1.0 (academic-research-tool)"})
        with urllib.request.urlopen(req2, timeout=6) as resp2:
            xml_text = resp2.read().decode("utf-8")

        root = ET.fromstring(xml_text)
        for article in root.findall(".//PubmedArticle"):
            pmid_el = article.find(".//PMID")
            pmid = pmid_el.text.strip() if (pmid_el is not None and pmid_el.text) else "Unknown"

            title_el = article.find(".//ArticleTitle")
            title = "".join(title_el.itertext()).strip() if title_el is not None else "No Title"

            journal_el = article.find(".//Journal/Title")
            journal_name = journal_el.text.strip() if (journal_el is not None and journal_el.text) else "Journal"
            year_el = article.find(".//JournalIssue/PubDate/Year")
            year = year_el.text.strip() if (year_el is not None and year_el.text) else ""
            journal_display = f"{journal_name} ({year})" if year else journal_name

            abstract_parts = []
            for ab in article.findall(".//AbstractText"):
                abstract_parts.append("".join(ab.itertext()).strip())
            raw_abstract = " ".join(abstract_parts)
            abstract_excerpt = _first_sentences(raw_abstract, max_sentences=3)

            # Strict mechanism extraction from actual text only
            combined_text = f"{title} {raw_abstract}"
            mechanisms = _extract_mechanisms_from_text(combined_text)

            papers.append({
                "pmid": pmid,
                "title": title.rstrip("."),
                "journal": journal_display,
                "abstract_excerpt": abstract_excerpt,
                "resistance_mechanisms": mechanisms,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            })

    except Exception as e:
        res_err = {
            "status": "unavailable",
            "match_level": match_level,
            "query_used": query_used,
            "peptide_name": peptide_name,
            "papers": [],
            "reason": f"NCBI XML fetch error: {e}",
        }
        return res_err

    result = {
        "status": "success",
        "match_level": match_level,
        "query_used": query_used,
        "peptide_name": peptide_name,
        "papers": papers,
        "reason": None,
    }
    _LIVE_EVIDENCE_CACHE[cache_key] = result
    return result


def generate_relationship_graph(sequence: str, species: str) -> dict[str, Any]:
    """Generates relationship graph strictly from live PubMed evidence."""
    ev_data = fetch_pubmed_evidence(sequence, species)
    papers = ev_data.get("papers", [])
    props = compute_properties(sequence)

    nodes = [
        {
            "id": "compound",
            "label": f"AMP Candidate ({sequence[:8]}...)",
            "type": "compound",
            "properties": {
                "sequence": sequence,
                "charge": props["net_charge_pH7"],
                "hydrophobic_moment": props["hydrophobic_moment_uH"],
            },
        },
        {
            "id": "target",
            "label": species,
            "type": "pathogen",
            "properties": {"priority": "WHO Priority Pathogen"},
        },
    ]

    edges = [
        {
            "source": "compound",
            "target": "target",
            "relation": "targets",
            "label": "Antimicrobial Action",
        }
    ]

    for i, paper in enumerate(papers, start=1):
        paper_id = f"paper_{i}"
        nodes.append({
            "id": paper_id,
            "label": f"PMID:{paper['pmid']} ({paper['journal']})",
            "type": "paper",
            "properties": {
                "title": paper["title"],
                "pmid": paper["pmid"],
                "url": paper["url"],
            },
        })
        edges.append({
            "source": paper_id,
            "target": "compound",
            "relation": "supports_evidence_for",
            "label": "Grounded Evidence",
        })

        # Only add mechanism nodes that were verified in the actual paper
        for m_idx, mech in enumerate(paper.get("resistance_mechanisms", [])):
            mech_id = f"mech_{i}_{m_idx}"
            nodes.append({
                "id": mech_id,
                "label": mech,
                "type": "mechanism",
            })
            edges.append({
                "source": "target",
                "target": mech_id,
                "relation": "exhibits_mechanism",
                "label": "Resistance Pathway",
            })
            edges.append({
                "source": "compound",
                "target": mech_id,
                "relation": "interacts_with",
                "label": "Observed in Literature",
            })

    return {"nodes": nodes, "edges": edges}


# --- 5. Multi-Tier 3D Structure Retrieval & RMSD -----------------------------

STRUCTURE_CACHE_DIR = C.DATA / "structures"
PDB_MAP_FILE = C.PROCESSED / "sequence_pdb_map.json"

_PDB_MAPPING: dict[str, str] | None = None


def get_pdb_mapping() -> dict[str, str]:
    global _PDB_MAPPING
    if _PDB_MAPPING is None:
        if PDB_MAP_FILE.exists():
            with open(PDB_MAP_FILE, "r", encoding="utf-8") as f:
                _PDB_MAPPING = json.load(f)
        else:
            _PDB_MAPPING = {}
    return _PDB_MAPPING


def fetch_structure(sequence: str) -> dict[str, Any]:
    """Multi-tier 3D structure resolution:
    - Tier 1: 'experimental' (RCSB PDB if known PDB ID exists)
    - Tier 2: 'predicted' (ESMFold API with per-residue pLDDT)
    - Tier 3: 'unavailable' (graceful fallback)
    """
    clean_seq = sequence.strip().upper()
    STRUCTURE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    mapping = get_pdb_mapping()

    # Tier 1: Experimental PDB
    if clean_seq in mapping:
        pdb_id = mapping[clean_seq]
        cache_file = STRUCTURE_CACHE_DIR / f"{pdb_id}.pdb"
        if cache_file.exists():
            pdb_text = cache_file.read_text(encoding="utf-8")
            return {
                "tier": "experimental",
                "pdb_id": pdb_id,
                "pdb_text": pdb_text,
                "plddt": None,
                "mean_plddt": None,
                "source": f"RCSB Protein Data Bank (PDB ID: {pdb_id}, experimentally determined)",
            }
        try:
            rcsb_url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
            with urllib.request.urlopen(rcsb_url, timeout=6) as resp:
                pdb_text = resp.read().decode("utf-8")
            cache_file.write_text(pdb_text, encoding="utf-8")
            return {
                "tier": "experimental",
                "pdb_id": pdb_id,
                "pdb_text": pdb_text,
                "plddt": None,
                "mean_plddt": None,
                "source": f"RCSB Protein Data Bank (PDB ID: {pdb_id}, experimentally determined)",
            }
        except Exception:
            pass

    # Tier 2: Predicted via ESMFold (ESM Atlas API)
    try:
        esm_url = "https://api.esmatlas.com/foldSequence/v1/pdb/"
        req = urllib.request.Request(
            esm_url,
            data=clean_seq.encode("utf-8"),
            headers={"Content-Type": "text/plain", "User-Agent": "AMPTriage/1.0"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            pdb_text = resp.read().decode("utf-8")

        plddts: list[float] = []
        seen_res = set()
        for line in pdb_text.splitlines():
            if line.startswith("ATOM") and line[12:16].strip() == "CA":
                res_seq = int(line[22:26].strip())
                if res_seq not in seen_res:
                    seen_res.add(res_seq)
                    b_factor = float(line[60:66].strip())
                    plddts.append(round(b_factor, 2))

        mean_plddt = round(float(np.mean(plddts)), 2) if plddts else None
        return {
            "tier": "predicted",
            "pdb_id": None,
            "pdb_text": pdb_text,
            "plddt": plddts,
            "mean_plddt": mean_plddt,
            "source": "ESMFold (ESM Atlas API, pLDDT confidence included)",
        }
    except Exception:
        pass

    # Tier 3: Unavailable
    return {
        "tier": "unavailable",
        "pdb_id": None,
        "pdb_text": None,
        "plddt": None,
        "mean_plddt": None,
        "source": "Structure unavailable",
        "reason": "Structure not in RCSB and ESMFold service unreachable.",
    }


def _parse_ca_coords(pdb_text: str) -> np.ndarray:
    coords = []
    seen = set()
    for line in pdb_text.splitlines():
        if line.startswith("ATOM") and line[12:16].strip() == "CA":
            res_num = int(line[22:26].strip())
            if res_num not in seen:
                seen.add(res_num)
                x = float(line[30:38].strip())
                y = float(line[38:46].strip())
                z = float(line[46:54].strip())
                coords.append([x, y, z])
    return np.array(coords, dtype=np.float64)


def _kabsch_rmsd(P: np.ndarray, Q: np.ndarray) -> float:
    L = min(len(P), len(Q))
    if L < 3:
        return 0.0
    p = P[:L] - P[:L].mean(axis=0)
    q = Q[:L] - Q[:L].mean(axis=0)

    H = p.T @ q
    U, S, Vt = np.linalg.svd(H)
    d = np.linalg.det(Vt.T @ U.T)
    Vt[-1, :] *= np.sign(d)
    R = Vt.T @ U.T

    p_rot = p @ R
    diff = p_rot - q
    return float(np.sqrt(np.mean(np.sum(diff ** 2, axis=1))))


def compare_structures(seq_a: str, seq_b: str) -> dict[str, Any]:
    struct_a = fetch_structure(seq_a)
    struct_b = fetch_structure(seq_b)

    tier_a = struct_a.get("tier")
    tier_b = struct_b.get("tier")

    if tier_a == "experimental" and tier_b == "experimental" and struct_a.get("pdb_text") and struct_b.get("pdb_text"):
        ca_a = _parse_ca_coords(struct_a["pdb_text"])
        ca_b = _parse_ca_coords(struct_b["pdb_text"])
        rmsd = _kabsch_rmsd(ca_a, ca_b)
        return {
            "rmsd": round(rmsd, 3),
            "tier_a": tier_a,
            "tier_b": tier_b,
            "pdb_id_a": struct_a.get("pdb_id"),
            "pdb_id_b": struct_b.get("pdb_id"),
            "reason": "Calculated on experimentally determined PDB structures via Kabsch CA alignment.",
        }
    else:
        return {
            "rmsd": None,
            "tier_a": tier_a,
            "tier_b": tier_b,
            "reason": (
                "RMSD comparison disabled for predicted short peptide structures (unreliable / "
                "disordered in aqueous solution). Comparison defaults to defensible axes: "
                "hydrophobic moment, net charge, helical-wheel overlay, and embedding distance."
            ),
        }
