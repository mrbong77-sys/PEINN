"""Start the satellite from the PEINN checkout:  python revision/aai_r1/station.py"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.chdir(HERE)
sys.path.insert(0, str(HERE))

from ops import station  # noqa: E402

sys.exit(station.main())
