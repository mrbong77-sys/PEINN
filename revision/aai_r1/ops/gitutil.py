"""Commit and push results at the end of an unattended run (branch: main)."""
from __future__ import annotations

import contextlib
import os
import subprocess
import time
from pathlib import Path

from . import paths

TRAILER = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
# Windows: background git / nvidia-smi calls get a hidden console (no window flashing every poll; professor 2026-10-05)
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def git(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")   # never wait on a credential prompt
    return subprocess.run(["git", *args], cwd=paths.REPO, capture_output=True, stdin=subprocess.DEVNULL,
                          text=True, encoding="utf-8", errors="replace", env=env, creationflags=NO_WINDOW)


@contextlib.contextmanager
def locked(timeout: float = 600, stale: float = 900):
    """One git writer at a time across processes (the supervisor's telemetry and the child's result pushes)."""
    lock = paths.REPO / ".git" / "peinn-ops-git.lock"
    t0 = time.time()
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > stale:     # left behind by a killed process
                    lock.unlink()
                    continue
            except FileNotFoundError:
                continue
            if time.time() - t0 > timeout:
                break                                              # proceed unlocked rather than stall the run
            time.sleep(1)
    try:
        yield
    finally:
        with contextlib.suppress(FileNotFoundError):
            lock.unlink()


def commit_and_push(targets: list[Path], message: str, branch: str = "main") -> bool:
    with locked():
        return _commit_and_push(targets, message, branch)


def _commit_and_push(targets: list[Path], message: str, branch: str) -> bool:
    git("add", "--", *[str(t) for t in targets])
    if not git("diff", "--cached", "--quiet").returncode:
        print("[git] nothing to commit", flush=True)
        git("fetch", "origin", branch)
        if git("rev-list", "--count", f"origin/{branch}..HEAD").stdout.strip() in ("", "0"):
            return True                                        # nothing new and nothing unpushed
        print("[git] earlier commits not yet pushed; pushing them", flush=True)
    else:
        r = git("commit", "-m", f"{message}\n\n{TRAILER}")
        if r.returncode:
            print(f"[git] commit failed: {r.stderr.strip()}", flush=True)
            return False
    for wait in (0, 2, 4, 8, 16):
        time.sleep(wait)
        # --autostash: a run that leaves tracked files modified must still be able to take commits pushed meanwhile
        pr = git("pull", "--rebase", "--autostash", "origin", branch)
        if pr.returncode:
            print(f"[git] pull failed: {(pr.stdout + pr.stderr).strip()[:200]}", flush=True)
            if (paths.REPO / ".git" / "rebase-merge").exists() or (paths.REPO / ".git" / "rebase-apply").exists():
                git("rebase", "--abort")                       # never leave the checkout mid-rebase
        r = git("push", "origin", f"HEAD:{branch}")
        if not r.returncode:
            print(f"[git] pushed to {branch}", flush=True)
            return True
        print(f"[git] push failed: {r.stderr.strip()[:200]}", flush=True)
    return False
