"""The PEAOS harness the revised runs called against its copy in this repository (src/): every code file the runs could
import from PEAOS, with its status (same, differs, only in PEAOS, only in src) and, where it differs, the unified diff
src -> PEAOS, so that the public src/ can be made the code that ran. Secret-like strings withhold a file's diff.
Nothing is run or imported. -> results/peaos_diff.json (pushed)."""
from __future__ import annotations

import ast
import difflib
import hashlib
import re
import subprocess
from pathlib import Path

from . import common as C
from . import data as D

ENTRY_FILES = ("run_stat_batch.py", "scripts/run_shieldstral_bench.py", "scripts/fetch_benchmark_data.py",
               "scripts/fetch_ggb_morables.py", "scripts/build_morables_dataset.py", "scripts/prefetch_fastembed.py")
CONFIG_DIRS = ("config", "pea_eval/config", "pea_eval/nemo_config", "pea_eval/pge")
CODE_EXT = (".py", ".yaml", ".yml", ".co", ".toml", ".cfg", ".ini")
TOP = ("pea_eval", "core", "config", "peinn_v2", "scripts")
SECRET = re.compile(r"(sk-[A-Za-z0-9_-]{16,}|hf_[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
                    r"(api[_-]?key|secret|password|passwd|token)\s*[:=]\s*['\"][^'\"\s]{8,}['\"])", re.I)
MAX_DIFF = 6_000_000


def _modfile(root: Path, name: str) -> Path | None:
    p = root.joinpath(*name.split("."))
    for c in (p.with_suffix(".py"), p / "__init__.py"):
        if c.is_file():
            return c
    return None


def closure(root: Path, modules, files) -> set[str]:
    """Files under root reachable by static imports (absolute, relative, and module-path strings) from the entries."""
    seen: set[Path] = set()
    todo: list[tuple[str | None, Path | None]] = [(m, None) for m in modules] + [(None, root / f) for f in files]
    while todo:
        m, f = todo.pop()
        if f is None:
            f = _modfile(root, m)
        if f is None or not f.is_file() or f in seen:
            continue
        seen.add(f)
        parts = list(f.relative_to(root).with_suffix("").parts)
        for i in range(1, len(parts)):
            todo.append((".".join(parts[:i]), None))
        try:
            t = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        pkg = parts if f.name == "__init__.py" else parts[:-1]
        for n in ast.walk(t):
            if isinstance(n, ast.Import):
                todo += [(a.name, None) for a in n.names]
            elif isinstance(n, ast.ImportFrom):
                base = pkg[:len(pkg) - (n.level - 1)] if n.level else []
                mod = ".".join(base + ([n.module] if n.module else []))
                todo.append((mod, None))
                todo += [(f"{mod}.{a.name}", None) for a in n.names]
            elif isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.split(".")[0] in TOP \
                    and all(x.isidentifier() for x in n.value.split(".")):
                todo.append((n.value, None))
    return {p.relative_to(root).as_posix() for p in seen}


def v21r_imports() -> list[str]:
    """pea_eval modules the revision code imports (it runs them inside the PEAOS checkout)."""
    mods = set()
    for f in Path(__file__).parent.glob("*.py"):
        mods |= set(re.findall(r"(?:from|import)\s+(pea_eval(?:\.\w+)*)", f.read_text(encoding="utf-8")))
    return sorted(mods)


def _sha(f: Path) -> str:
    return hashlib.sha256(f.read_bytes()).hexdigest()


def _git(root: Path, *a: str) -> str:
    try:
        r = subprocess.run(["git", "-C", str(root), *a], capture_output=True, encoding="utf-8", errors="replace")
        return r.stdout.strip() if r.returncode == 0 else f"[git rc {r.returncode}] {r.stderr.strip()[:200]}"
    except OSError as e:
        return f"[{e}]"


def compare(peaos: Path, src: Path) -> dict:
    files = [f for f in ENTRY_FILES]
    for d in CONFIG_DIRS:
        for root in (peaos, src):
            if (root / d).is_dir():
                files += [p.relative_to(root).as_posix() for p in (root / d).rglob("*")
                          if p.is_file() and p.suffix in CODE_EXT and "__pycache__" not in p.parts]
    mods = v21r_imports()
    used = closure(peaos, mods, sorted(set(files)))
    in_src = closure(src, mods, sorted(set(files)))
    rows, total = {}, 0
    for rel in sorted(used | in_src):
        a, b = src / rel, peaos / rel
        if a.is_file() and b.is_file():
            st = "same" if _sha(a) == _sha(b) else "differs"
        else:
            st = "only_peaos" if b.is_file() else "only_src"
        r = {"status": st, "used_by_runs": rel in used}
        if st != "same":
            ta = a.read_text(encoding="utf-8", errors="replace") if a.is_file() else ""
            tb = b.read_text(encoding="utf-8", errors="replace") if b.is_file() else ""
            hit = SECRET.search(tb)
            if hit:
                r["diff"] = None
                r["withheld"] = f"secret-like string at line {tb[:hit.start()].count(chr(10)) + 1}"
            else:
                d = "".join(difflib.unified_diff(ta.splitlines(True), tb.splitlines(True), f"src/{rel}", f"PEAOS/{rel}"))
                total += len(d)
                r["diff"] = d if total <= MAX_DIFF else None
                if total > MAX_DIFF:
                    r["withheld"] = "diff budget exceeded"
            r["lines"] = {"src": ta.count("\n"), "peaos": tb.count("\n")}
        rows[rel] = r
    count = {s: sum(r["status"] == s for r in rows.values()) for s in ("same", "differs", "only_peaos", "only_src")}
    return {"peaos": {"head": _git(peaos, "rev-parse", "HEAD"), "remote": _git(peaos, "remote", "get-url", "origin"),
                      "dirty_files": len([x for x in _git(peaos, "status", "--porcelain").splitlines() if x.strip()])},
            "v21r_imports": mods, "count": count, "files": rows}


PACKAGES = ("torch", "transformers", "sentence-transformers", "safetensors", "huggingface-hub", "peft", "accelerate",
            "nemoguardrails", "langchain", "langchain-core", "langchain-community", "fastembed", "openai", "pydantic",
            "pydantic-settings", "numpy", "pandas", "scipy", "scikit-learn", "matplotlib", "pyyaml", "gguf")


def environment() -> dict:
    """The satellite's software: Python, the packages the steps import, Ollama, the GPU (for the README)."""
    import platform
    from importlib import metadata
    pk = {}
    for n in PACKAGES:
        try:
            pk[n] = metadata.version(n)
        except metadata.PackageNotFoundError:
            pk[n] = None

    def out(*cmd):
        try:
            r = subprocess.run(list(cmd), capture_output=True, encoding="utf-8", errors="replace", timeout=60)
            return (r.stdout or r.stderr).strip()[:300]
        except (OSError, subprocess.TimeoutExpired) as e:
            return f"[{e}]"
    return {"python": platform.python_version(), "os": platform.platform(), "packages": pk,
            "ollama": out("ollama", "--version"),
            "gpu": out("nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader")}


def peaos_diff(check: bool = False, log=print) -> int:
    rep = compare(C.peaos(), C.peinn() / "src")
    rep["environment"] = environment()
    log(f"environment: {rep['environment']}")
    log(f"PEAOS {rep['peaos']['head'][:12]} (dirty files {rep['peaos']['dirty_files']}): {rep['count']}")
    for rel, r in rep["files"].items():
        if r["status"] != "same":
            log(f"  {r['status']:10s} {'used' if r['used_by_runs'] else '    '} {rel} {r.get('withheld', '')}")
    out = C.jdump(rep, D.odir(check) / "peaos_diff.json")
    if check:
        return 0
    return 0 if C.publish([out], "v21r peaos-diff: the PEAOS harness the runs called against its copy in src/") else 1
