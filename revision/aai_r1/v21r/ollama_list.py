"""The models Ollama holds on the satellite, and the source of every R2D2 or
zephyr build (its Modelfile FROM line and template) -> results/diag/ollama_list.md (pushed)."""
from __future__ import annotations

import subprocess

from . import common as C
from . import data as D


def _run(*args: str) -> str:
    try:
        r = subprocess.run(["ollama", *args], capture_output=True, encoding="utf-8", errors="replace")
    except OSError as e:
        return f"[{e}]"
    return (r.stdout or "") + (r.stderr or "")


def ollama_list(check: bool = False, log=print) -> int:
    lst = _run("list")
    L = ["# ollama list (위성)", "", "```", lst.strip(), "```", ""]
    names = [ln.split()[0] for ln in lst.splitlines()[1:] if ln.strip()]
    for n in names:
        if any(k in n.lower() for k in ("r2d2", "zephyr")):
            mf = _run("show", n, "--modelfile")
            keep = [ln for ln in mf.splitlines() if ln.startswith(("FROM", "PARAMETER", "# FROM"))]
            L += [f"## {n}", "", "```", *keep, "```", "", "템플릿:", "```", _run("show", n, "--template").strip(), "```", ""]
    out = D.odir(check) / "diag" / "ollama_list.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    log("\n".join(L))
    if check:
        return 0
    return 0 if C.publish([out], "v21r diag: ollama list and the R2D2 / zephyr builds on the satellite") else 1
