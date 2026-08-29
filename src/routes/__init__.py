"""FastAPI routers.

api.py is a thin composition root: it imports and includes these, and owns nothing
else. One router per parallel track so two people never edit the same file.

    runs.py         phase 6b   the engine track
    auth.py         phase 7    the product track
    projects.py     phase 7    the product track
    experiments.py  phase 8    the engine track
    analytics.py    phase 9
"""
