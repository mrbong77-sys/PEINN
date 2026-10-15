"""Where things are. REPO is the git checkout (this repository); RUN is the folder the modules run from."""
from __future__ import annotations

from pathlib import Path

RUN = Path(__file__).resolve().parents[1]                 # revision/aai_r1
REPO = RUN.parents[1]                                     # the PEINN checkout
RESULTS = RUN / "results"                                 # beacons and results (committed)
CACHE = RUN / "cache"                                     # loop state, logs (not committed)
CMD = "revision/aai_r1/commands"                          # command files, read from origin/main
