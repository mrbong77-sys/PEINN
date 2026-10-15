"""Run a fixed list of steps unattended: skip finished steps, stop at the first failure."""
from __future__ import annotations

import argparse
import json
import time
import traceback
from pathlib import Path
from typing import Callable

Step = tuple[str, str, Callable[[], int]]


def run(name: str, steps: list[Step], state_path: Path, argv=None, doc: str | None = None) -> int:
    ap = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--restart", action="store_true", help="forget finished steps")
    a = ap.parse_args(argv)
    try:
        st = {"done": {}} if a.restart else json.loads(state_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        st = {"done": {}}
    t0 = time.time()
    for key, what, fn in steps:
        if key in st["done"]:
            print(f"[{name}] skip {key} ({what}): finished {st['done'][key]}", flush=True)
            continue
        print(f"\n[{name}] ===== {key}: {what} =====", flush=True)
        try:
            rc = fn()
        except SystemExit as e:                       # preflight and data checks exit with a message
            rc = e.code if isinstance(e.code, int) else 1
            if not isinstance(e.code, int):
                print(f"[{name}] {key} stopped: {e.code}", flush=True)
        except Exception:                             # noqa: BLE001
            traceback.print_exc()
            rc = 1
        if rc:
            print(f"[{name}] {key} failed (code {rc}); fix it and run the same command again", flush=True)
            return 1
        st["done"][key] = time.strftime("%Y-%m-%d %H:%M:%S")
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(st, indent=1), encoding="utf-8")
    print(f"\n[{name}] all steps finished and pushed in {(time.time() - t0) / 60:.1f} min", flush=True)
    return 0
