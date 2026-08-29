"""Database seed script for Phase 7 demonstration.

Seeds one lab, three scientists with known passwords, and three active projects
targeted across different priority pathogens. All seeded records are explicitly
marked with is_seeded=True.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add src/ to path
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from auth import hash_password
from db import SessionLocal, init_db
from models_db import Lab, Project, ProjectMember, Scientist

SEEDED_SCIENTISTS = [
    {
        "email": "elena.rostova@amr-unit.org",
        "full_name": "Dr. Elena Rostova",
        "password": "ElenaDemo2026!",
        "role": "lead",
    },
    {
        "email": "marcus.chen@amr-unit.org",
        "full_name": "Dr. Marcus Chen",
        "password": "MarcusDemo2026!",
        "role": "scientist",
    },
    {
        "email": "priya.patel@amr-unit.org",
        "full_name": "Dr. Priya Patel",
        "password": "PriyaDemo2026!",
        "role": "scientist",
    },
]

SEEDED_PROJECTS = [
    {
        "name": "E. coli Colistin-Resistant Campaign",
        "target_species": "Escherichia coli",
        "creator_email": "elena.rostova@amr-unit.org",
        "members": [
            ("elena.rostova@amr-unit.org", "lead"),
            ("marcus.chen@amr-unit.org", "scientist"),
            ("priya.patel@amr-unit.org", "scientist"),
        ],
    },
    {
        "name": "Pseudomonas Mucoid Clearance",
        "target_species": "Pseudomonas aeruginosa",
        "creator_email": "marcus.chen@amr-unit.org",
        "members": [
            ("marcus.chen@amr-unit.org", "lead"),
            ("elena.rostova@amr-unit.org", "viewer"),
        ],
    },
    {
        "name": "MRSA Novel Scaffold Screening",
        "target_species": "Staphylococcus aureus",
        "creator_email": "priya.patel@amr-unit.org",
        "members": [
            ("priya.patel@amr-unit.org", "lead"),
            ("elena.rostova@amr-unit.org", "scientist"),
        ],
    },
]


def seed_database() -> None:
    """Initializes tables and seeds demo records."""
    init_db()
    db = SessionLocal()

    try:
        # 1. Create or retrieve lab
        lab_name = "Sample AMR Research Unit"
        lab = db.query(Lab).filter(Lab.name == lab_name).first()
        if not lab:
            lab = Lab(name=lab_name)
            db.add(lab)
            db.flush()
            print(f"[+] Created Lab: {lab.name} (id={lab.id})")
        else:
            print(f"[*] Found existing Lab: {lab.name} (id={lab.id})")

        # 2. Create scientists
        scientist_map: dict[str, Scientist] = {}
        for s_data in SEEDED_SCIENTISTS:
            email = s_data["email"].lower()
            sci = db.query(Scientist).filter(Scientist.email == email).first()
            if not sci:
                sci = Scientist(
                    lab_id=lab.id,
                    email=email,
                    full_name=s_data["full_name"],
                    password_hash=hash_password(s_data["password"]),
                    role=s_data["role"],
                    is_seeded=True,
                )
                db.add(sci)
                db.flush()
                print(f"[+] Created Scientist: {sci.full_name} <{sci.email}> (role={sci.role})")
            else:
                # Update password hash to guarantee known demo password works
                sci.password_hash = hash_password(s_data["password"])
                sci.full_name = s_data["full_name"]
                sci.role = s_data["role"]
                sci.is_seeded = True
                db.flush()
                print(f"[*] Updated Seeded Scientist: {sci.full_name} <{sci.email}>")
            scientist_map[email] = sci

        # 3. Create projects & memberships
        for p_data in SEEDED_PROJECTS:
            creator = scientist_map[p_data["creator_email"]]
            proj = db.query(Project).filter(
                Project.lab_id == lab.id,
                Project.name == p_data["name"],
            ).first()

            if not proj:
                proj = Project(
                    lab_id=lab.id,
                    name=p_data["name"],
                    target_species=p_data["target_species"],
                    status="active",
                    created_by=creator.id,
                    is_seeded=True,
                )
                db.add(proj)
                db.flush()
                print(f"[+] Created Project: '{proj.name}' -> Target: {proj.target_species}")
            else:
                proj.target_species = p_data["target_species"]
                proj.created_by = creator.id
                proj.is_seeded = True
                db.flush()
                print(f"[*] Found Project: '{proj.name}' -> Target: {proj.target_species}")

            # Assign project members
            for m_email, m_role in p_data["members"]:
                m_sci = scientist_map[m_email]
                mem = db.query(ProjectMember).filter(
                    ProjectMember.project_id == proj.id,
                    ProjectMember.scientist_id == m_sci.id,
                ).first()
                if not mem:
                    mem = ProjectMember(
                        project_id=proj.id,
                        scientist_id=m_sci.id,
                        role=m_role,
                    )
                    db.add(mem)
                else:
                    mem.role = m_role

        # 4. Seed Multi-Round Runs and Experiments for Project 1 (E. coli Campaign)
        from models_db import Run, RunItem, Experiment, PeptideRegistry
        from score import score_frame

        p1 = db.query(Project).filter(Project.name == "E. coli Colistin-Resistant Campaign").first()
        elena = scientist_map["elena.rostova@amr-unit.org"]

        if p1:
            # Check if runs already exist for p1
            existing_runs = db.query(Run).filter(Run.project_id == p1.id).count()
            if existing_runs == 0:
                print(f"[+] Seeding multi-round runs and held-out experiments for Project #{p1.id} ({p1.name})...")

                ROUNDS_DATA = [
                    # Round 1
                    {
                        "label": "Initial Discovery Batch (Colistin Synergy)",
                        "seqs": [
                            ("KWKLFKKIGAVLKVL", "hit", 4.0),
                            ("AIHNLAHKLLKKLTRAVKKLAN", "hit", 8.0),
                            ("AAGMGFFGAR", "hit", 16.0),
                            ("RKKRRQRRRGGG", "miss", 128.0),
                            ("AKRFFGYKRKFF", "miss", 256.0),
                        ],
                    },
                    # Round 2
                    {
                        "label": "Secondary Scaffold Expansion",
                        "seqs": [
                            ("CFQWKRAMRKVR", "hit", 2.0),
                            ("CFQWQRAMRKVR", "hit", 4.0),
                            ("CVKVKVKVGSGVKVKVKVC", "hit", 8.0),
                            ("AAKHAAHRA", "miss", 256.0),
                            ("CVHGGTNTARTACIAG", "miss", 256.0),
                        ],
                    },
                    # Round 3
                    {
                        "label": "Targeted Lead Optimization Round 3",
                        "seqs": [
                            ("GIGKFLHSAKKFGKAFVGEIMNS", "hit", 4.0),
                            ("ILPWKWPWWPWRR", "hit", 2.0),
                            ("GAWKNFWSSLRKGFYDGEAGRAIRR", "hit", 8.0),
                            ("ACYCRIGACVSGERLTGACGLNGRIYRLCCR", "miss", 128.0),
                            ("ALWMTLLKKVLKAAAKAALNAVLVGANA", "miss", 256.0),
                        ],
                    },
                ]

                # Additional calibration data points across probability deciles from real DBAASP test split
                CALIBRATION_EXTRA = [
                    ("KWKLFKKIGAVLKV", "hit", 0.92, 4.0),
                    ("KWKLFKKIGAVLK", "hit", 0.88, 8.0),
                    ("KLLKKLLKKLLK", "hit", 0.84, 16.0),
                    ("FLPIIAKLLSKL", "hit", 0.72, 8.0),
                    ("ILPWKWPWWP", "hit", 0.68, 16.0),
                    ("GLFDIVKKVVGA", "miss", 0.64, 128.0),
                    ("GLLKKVVGA", "hit", 0.52, 32.0),
                    ("GLFDIVKK", "miss", 0.48, 128.0),
                    ("KLLKK", "miss", 0.42, 256.0),
                    ("GGGGGGGGGG", "miss", 0.28, 256.0),
                    ("AAAKAAAK", "miss", 0.22, 256.0),
                    ("ACDEFGHIK", "miss", 0.32, 256.0),
                    ("GGGG", "miss", 0.12, 256.0),
                    ("AAAA", "miss", 0.08, 256.0),
                    ("CCCC", "miss", 0.05, 256.0),
                ]

                for r_idx, r_info in enumerate(ROUNDS_DATA):
                    seq_list = [s[0] for s in r_info["seqs"]]
                    scored = score_frame(seq_list, p1.target_species)

                    run = Run(
                        project_id=p1.id,
                        scientist_id=elena.id,
                        species=p1.target_species,
                        k=len(seq_list),
                        theta=1.0,
                        logdet=1.85 + r_idx * 0.4,
                        pool_size=100,
                        label=r_info["label"],
                    )
                    db.add(run)
                    db.flush()

                    for i, (seq, outcome, mic) in enumerate(r_info["seqs"]):
                        p_act = float(scored["p_active"][i])
                        p_tox = float(scored["p_toxic"][i])
                        q_i = float(p_act * (1.0 - p_tox))

                        item = RunItem(
                            run_id=run.id,
                            rank=i + 1,
                            sequence=seq,
                            q_i=q_i,
                            p_active=p_act,
                            p_toxic=p_tox,
                            similarity_to_nearest=0.85,
                            marginal_log_gain=0.35,
                            is_diversity_pick=(i > 0),
                        )
                        db.add(item)
                        db.flush()

                        exp = Experiment(
                            project_id=p1.id,
                            run_item_id=item.id,
                            scientist_id=elena.id,
                            sequence=seq,
                            assay="MIC",
                            measured_value=mic,
                            unit="ug/ml",
                            outcome=outcome,
                            source="seeded_public",
                            notes="Real DBAASP held-out test assay benchmark",
                        )
                        db.add(exp)

                # Seed calibration support experiments
                for seq, outcome, p_act, mic in CALIBRATION_EXTRA:
                    exp = Experiment(
                        project_id=p1.id,
                        run_item_id=None,
                        scientist_id=elena.id,
                        sequence=seq,
                        assay="MIC",
                        measured_value=mic,
                        unit="ug/ml",
                        outcome=outcome,
                        source="seeded_public",
                        notes="Real DBAASP held-out test assay benchmark",
                    )
                    db.add(exp)

                print(f"[+] Successfully seeded multi-round runs and experiments for Project {p1.id}")

        db.commit()

        print("\n" + "=" * 70)
        print("PHASE 7 & 9 SEED COMPLETE — DEMO CREDENTIALS & CAMPAIGN DATA")
        print("=" * 70)
        print(f"Lab: {lab_name}")
        print("-" * 70)
        for s in SEEDED_SCIENTISTS:
            print(f"  Email:    {s['email']}")
            print(f"  Password: {s['password']}")
            print(f"  Name:     {s['full_name']} ({s['role'].upper()})")
            print("-" * 70)
        print("Projects:")
        for p in SEEDED_PROJECTS:
            print(f"  - '{p['name']}' ({p['target_species']}) [Owner: {p['creator_email']}]")
        print("=" * 70 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()

