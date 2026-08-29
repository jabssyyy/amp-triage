"""Phase 4 - Streamlit app: Score / Shortlist / Validation tabs.

STUB. Built by the product track once phases 0-3 are verified.
"""
import streamlit as st

st.set_page_config(page_title="AMP Triage", layout="wide")
st.title("AMP Triage - antimicrobial peptide shortlisting")
score_tab, shortlist_tab, validation_tab = st.tabs(["Score", "Shortlist", "Validation"])
for tab, phase in ((score_tab, "phase 2"), (shortlist_tab, "phase 3"), (validation_tab, "phase 4")):
    with tab:
        st.info(f"Not wired up yet - waiting on {phase}.")
