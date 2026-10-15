"""Unattended supervision with a closed ground loop (ported from PEINN_v2 docs/11_ops_loop.md).

Three processes: the launcher (what Eugene starts) restarts the supervisor whenever it exits with RELOAD; the supervisor
runs `python -m <module> --child ...` and is the PC's half of the loop; the child runs the steps.

PC -> ground (telemetry): results/runner/status.md and status.json, pushed at every event and every
PEINN2_HEARTBEAT_MIN minutes while running or waiting: verdict, running code commit, current step and its age, minutes
since the last output line, GPU memory and load, next planned action, last acknowledged command, last log lines.
Ground -> PC: (1) code fixes pushed to main; while a failure waits, the supervisor fetches every PEINN2_POLL_MIN
minutes and retries as soon as new code arrives (a change to any .py file restarts the supervisor itself through the
launcher, so fixes to the loop also take effect); (2) commands in commands/<study>.json on main, read from origin while
running or waiting, executed once and acknowledged in the telemetry. Actions: abort (stop the child, wait for a fix),
restart (stop the child, pull, run again), rerun (as restart, after forgetting the listed finished steps), retry (end
a wait now), stop (end the run), standby (stop the child and hold: beacons and commands only, nothing runs, survives
supervisor reloads), resume (leave standby: pull and run), update (safe code update: pull and reload at the next step
boundary, so no step is cut; immediately when nothing runs). Without new code a failure is retried PEINN2_MAX_BLIND times every
PEINN2_RETRY_WAIT_MIN minutes (transient errors), then the supervisor only waits for code or a command, up to
PEINN2_MAX_WAIT_H hours. A child that prints nothing for PEINN2_STALL_MIN minutes is stopped as stalled.
Windows pipes are read as UTF-8 explicitly.
"""
from __future__ import annotations

import collections
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

from . import paths
from .gitutil import NO_WINDOW, commit_and_push, git, locked

RELOAD = 75
ACTIONS = ("abort", "restart", "rerun", "retry", "stop", "standby", "resume", "update")
KILLS = ("abort", "restart", "rerun", "stop", "standby")      # stop the running child at once


def _env_f(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def launch(module: str, argv: list[str], call=subprocess.call) -> int:
    """Outermost loop: run the supervisor; start it again (with the pulled code) while it asks for a reload."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    first = True
    while True:
        args = [*argv, "--fresh"] if first else [a for a in argv if a != "--restart"]
        rc = call([sys.executable, "-u", "-m", module, "--inner", *args], cwd=paths.RUN, env=env)
        if rc != RELOAD:
            return rc
        print("[launcher] new code pulled; restarting the supervisor", flush=True)
        first = False


class Ops:
    """The supervisor's view of git and the machine (replaced by a fake in tests)."""

    def __init__(self, study: str):
        self.study = study

    def head(self) -> str:
        return git("rev-parse", "HEAD").stdout.strip()

    def subject(self, rev: str) -> str:
        return git("log", "-1", "--format=%h %s", rev).stdout.strip()[:120]

    def fetch(self) -> str | None:
        with locked():
            r = git("fetch", "-q", "origin", "main")
        if r.returncode:
            return None
        return git("rev-parse", "origin/main").stdout.strip() or None

    def changed(self, a: str, b: str) -> list[str]:
        return [f for f in git("diff", "--name-only", a, b).stdout.split() if f]

    def pull(self) -> str:
        with locked():
            r = git("pull", "--rebase", "--autostash", "origin", "main")
            return self._after_pull(r)

    @staticmethod
    def _after_pull(r) -> str:
        if r.returncode and ((paths.REPO / ".git" / "rebase-merge").exists() or (paths.REPO / ".git" / "rebase-apply").exists()):
            git("rebase", "--abort")
        return (r.stdout + r.stderr).strip()[:300]

    def command(self) -> dict | None:
        r = git("show", f"origin/main:{paths.CMD}/{self.study}.json")
        if r.returncode:
            return None
        try:
            c = json.loads(r.stdout)
        except json.JSONDecodeError:
            return None
        return c if isinstance(c, dict) and c.get("id") and c.get("action") in ACTIONS else None

    def push(self, targets: list[Path], message: str) -> bool:
        try:
            return commit_and_push(targets, message)
        except Exception as e:  # noqa: BLE001  telemetry must never stop the run
            print(f"[ops] push failed: {type(e).__name__}: {e}", flush=True)
            return False

    def gpu(self) -> str:
        try:
            r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu",
                                "--format=csv,noheader"], capture_output=True, text=True, encoding="utf-8", timeout=20,
                               creationflags=NO_WINDOW)
            return r.stdout.strip().replace("\n", " | ") or "nvidia-smi: no output"
        except Exception as e:  # noqa: BLE001
            return f"nvidia-smi unavailable ({type(e).__name__})"

    def kill(self, p) -> None:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True, creationflags=NO_WINDOW)
        else:
            p.kill()


def _is_code(f: str) -> bool:
    return f.endswith(".py")


class Supervisor:
    def __init__(self, module: str, argv: list[str], runner: Path, state: Path, steps: list, label: str, log: Path,
                 ops: Ops | None = None, popen=subprocess.Popen, clock=time.time, sleep=time.sleep, tick: float = 10.0,
                 titles: dict | None = None):
        self.module, self.runner, self.state, self.steps, self.label, self.log = module, runner, state, steps, label, log
        self.titles = titles or {}                                   # step key -> plain Korean title (beacon)
        self.study = state.stem.replace("_state", "")
        self.ops = ops or Ops(self.study)
        self.popen, self.clock, self.sleep, self.tick = popen, clock, sleep, tick
        self.retry = "--no-retry" not in argv
        self.fresh = "--fresh" in argv
        self.args = [a for a in argv if a not in ("--no-retry", "--fresh")]
        self.heartbeat = _env_f("PEINN2_HEARTBEAT_MIN", 10) * 60     # beacon period
        self.poll = _env_f("PEINN2_POLL_MIN", 2) * 60                # command latency
        self.retry_wait = _env_f("PEINN2_RETRY_WAIT_MIN", 30) * 60
        self.max_blind = int(_env_f("PEINN2_MAX_BLIND", 3))
        self.max_wait = _env_f("PEINN2_MAX_WAIT_H", 48) * 3600
        self.stall = _env_f("PEINN2_STALL_MIN", 180) * 60
        self.ops_path = state.with_name(f"{self.study}_ops.json")
        self.tail: collections.deque[str] = collections.deque(maxlen=150)
        self.step, self.step_t0, self.last_out = None, None, None
        self.steps_seen = 0                                          # step headers printed by the current child
        self.o = self._load_ops()

    # ---- persistent loop state (survives supervisor reloads) ----
    def _load_ops(self) -> dict:
        try:
            o = json.loads(self.ops_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            o = {}
        if self.fresh or not o:
            seen = o.get("done_cmds", [])
            o = {"attempt": 1, "blind": 0, "wait_since": None, "done_cmds": seen, "ack": o.get("ack"), "standby": False,
                 "seq": o.get("seq", 0)}
            c = self.ops.command()                            # a command already on main at a fresh start is history
            if c and c["id"] not in seen:
                o["done_cmds"].append(c["id"])
        return o

    def _save_ops(self) -> None:
        self.ops_path.parent.mkdir(parents=True, exist_ok=True)
        self.ops_path.write_text(json.dumps(self.o, indent=1), encoding="utf-8")

    # ---- telemetry ----
    def _done(self) -> dict:
        try:
            return json.loads(self.state.read_text(encoding="utf-8")).get("done", {})
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _title(self, key: str) -> str:
        return f"{self.titles[key]} (`{key}`)" if key in self.titles else key

    def report(self, verdict: str, nxt: str = "", reason: str = "", push: bool = True) -> None:
        now = self.clock()
        done = self._done()
        left = [k for k, _, _ in self.steps if k not in done]
        head = self.ops.head()
        self.o["seq"] = self.o.get("seq", 0) + 1
        self._save_ops()
        t = {"verdict": verdict, "seq": self.o["seq"], "standby": bool(self.o.get("standby")),
             "beacon_min": self.heartbeat / 60, "poll_min": self.poll / 60,
             "time_local": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
             "time_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now)), "attempt": self.o["attempt"],
             "code": self.ops.subject(head) if head else None, "step": self.step,
             "step_min": round((now - self.step_t0) / 60, 1) if self.step_t0 else None,
             "since_output_min": round((now - self.last_out) / 60, 1) if self.last_out else None,
             "gpu": self.ops.gpu(), "next": nxt, "reason": reason, "ack": self.o.get("ack"),
             "done": list(done), "left": left}
        L = [f"# {self.label} 무인 실행 상태: {verdict}", "",
             f"- 시각 {t['time_local']} (UTC {t['time_utc']}), 시도 {t['attempt']}, 비컨 #{t['seq']} "
             f"(주기 {t['beacon_min']:g}분, 명령 확인 {t['poll_min']:g}분마다, 명령 파일 `{paths.CMD}/{self.study}.json`)",
             f"- 실행 코드: {t['code']}",
             f"- 현재 단계: {self._title(t['step']) if t['step'] else '없음'}" + (f" ({t['step_min']}분째)" if t["step_min"] is not None else ""),
             f"- 마지막 출력 후: {t['since_output_min']}분" if t["since_output_min"] is not None else "- 마지막 출력 후: –",
             f"- GPU(사용 MiB, 전체 MiB, 사용률, 온도): {t['gpu']}",
             f"- 다음 동작: {nxt or '–'}", f"- 사유: {reason or '–'}",
             f"- 마지막으로 처리한 명령: {t['ack'] or '없음'}",
             f"- 남은 단계: {'; '.join(self._title(k) for k in left) or '없음'}",
             f"- 끝난 단계(코드): {', '.join(done) or '없음'}", ""]
        tail = list(self.tail)[-40:] if verdict in ("실행 중", "대기 모드(standby)") else list(self.tail)
        if tail:
            L += ["## 마지막 로그", "", "```", *tail, "```"]
        self.runner.mkdir(parents=True, exist_ok=True)
        (self.runner / "status.md").write_text("\n".join(L) + "\n", encoding="utf-8")
        (self.runner / "status.json").write_text(json.dumps(t, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        if push:
            self.ops.push([self.runner], f"{self.label} runner: {verdict} (attempt {self.o['attempt']})")

    # ---- commands ----
    def _new_command(self) -> dict | None:
        c = self.ops.command()
        return c if c and c["id"] not in self.o["done_cmds"] else None

    def _ack(self, c: dict, what: str) -> None:
        self.o["done_cmds"].append(c["id"])
        self.o["ack"] = f"{c['id']} {c['action']} ({what}, {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(self.clock()))} UTC)"
        self._save_ops()
        print(f"[{self.label}] command {c['id']}: {c['action']} ({what})", flush=True)

    def _forget(self, keys: list[str]) -> None:
        try:
            st = json.loads(self.state.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return
        for k in keys:
            st.get("done", {}).pop(k, None)
        self.state.write_text(json.dumps(st, indent=1), encoding="utf-8")

    # ---- one child run ----
    def _read(self, p, logf) -> None:
        for raw in p.stdout:
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            print(line, flush=True)
            logf.write(line + "\n")
            logf.flush()
            self.tail.append(line[:400])
            self.last_out = self.clock()
            m = re.search(r"===== (\S+): ", line)
            if m:
                self.step, self.step_t0 = m.group(1), self.last_out
                self.steps_seen += 1

    def run_child(self) -> tuple[int, str | None, dict | None]:
        """(return code, reason it was stopped or None, command that stopped it or None)."""
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        args = self.args if self.o["attempt"] == 1 else [a for a in self.args if a != "--restart"]
        self.tail.clear()
        self.step = self.step_t0 = None
        self.steps_seen = 0
        self.last_out = self.clock()
        stopped, cmd = None, None
        update, update_at = None, 0                                  # pending safe update, step count when received
        with open(self.log, "a", encoding="utf-8") as logf:
            p = self.popen([sys.executable, "-u", "-m", self.module, "--child", *args], cwd=paths.RUN,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
            reader = threading.Thread(target=self._read, args=(p, logf), daemon=True)
            reader.start()
            self.report("실행 중", "단계 진행", "시작")
            last_beat = last_poll = self.clock()
            while p.poll() is None:
                self.sleep(self.tick)
                now = self.clock()
                if now - last_poll >= self.poll:
                    last_poll = now
                    if self.ops.fetch():
                        c = self._new_command()
                        if c and c["action"] in KILLS:
                            stopped, cmd = f"명령 {c['id']} ({c['action']})", c
                            self.ops.kill(p)
                            break
                        if c and c["action"] == "update" and update is None:
                            update, update_at = c, self.steps_seen
                            self._ack(c, "수신, 다음 단계 경계에서 적용")
                            self.report("실행 중", "다음 단계가 시작되면 멈추고 새 코드로 다시 실행", "안전 업데이트 대기")
                        elif c and c["action"] in ("resume", "retry"):
                            self._ack(c, "이미 실행 중, 할 일 없음")
                if update is not None and self.steps_seen > update_at:
                    stopped, cmd = f"명령 {update['id']} (update, 단계 경계)", update
                    self.ops.kill(p)                                 # the new step had just started: nothing is lost
                    break
                if now - self.last_out >= self.stall:
                    stopped = f"출력 없음 {round((now - self.last_out) / 60)}분(정지로 판단)"
                    self.ops.kill(p)
                    break
                if now - last_beat >= self.heartbeat:
                    last_beat = now
                    self.report("실행 중", "단계 진행", "정기 보고")
            rc = p.wait()
            reader.join(timeout=30)
        if update is not None and stopped is None and rc == 0:   # the child finished before the next step began:
            stopped, cmd = f"명령 {update['id']} (update, 임무 끝)", update   # rerun with the new code (it may add steps)
        return rc, stopped, cmd

    # ---- waiting for a fix ----
    def wait_for_fix(self, base: str) -> str:
        """'retry', 'reload', 'stop' or 'give-up'."""
        if self.o["wait_since"] is None:
            self.o["wait_since"] = self.clock()
            self._save_ops()
        t0 = self.clock()
        last_beat = t0
        while True:
            now = self.clock()
            blind_due = self.o["blind"] < self.max_blind and now - t0 >= self.retry_wait
            if now - self.o["wait_since"] >= self.max_wait:
                return "give-up"
            origin = self.ops.fetch()
            c = self._new_command() if origin else None
            if c:
                if c["action"] == "stop":
                    self._ack(c, "실행 종료")
                    return "stop"
                if c["action"] == "standby":
                    self._ack(c, "대기 모드 진입")
                    return "standby"
                if c["action"] == "rerun":
                    self._forget(list(c.get("steps") or []))
                self._ack(c, "대기 끝, 재시도")
                return self._pull_then(base, origin)
            if origin and any(_is_code(f) for f in self.ops.changed(base, origin)):
                print(f"[{self.label}] new code on main; pulling and retrying", flush=True)
                self.o["blind"] = 0
                return self._pull_then(base, origin)
            if blind_due:
                self.o["blind"] += 1
                self._save_ops()
                return self._pull_then(base, origin)
            if now - last_beat >= self.heartbeat:
                last_beat = now
                waited = round((now - self.o["wait_since"]) / 60)
                nxt = (f"새 코드나 명령이 오면 즉시 재시도. 없으면 {round((t0 + self.retry_wait - now) / 60)}분 뒤 자동 재시도"
                       if self.o["blind"] < self.max_blind else
                       f"새 코드나 명령만 기다림(자동 재시도 {self.max_blind}회 소진, 최대 {self.max_wait / 3600:.0f}시간)")
                self.report("실패 후 대기", nxt, f"대기 {waited}분째")
            self.sleep(self.poll)

    # ---- standby ----
    def standby_wait(self, base: str) -> str:
        """Hold with beacons until resume/restart/rerun/retry ('retry' or 'reload') or stop ('stop'). update pulls
        while holding; a code change reloads the supervisor, which comes back into standby (kept in the ops state)."""
        self.o["standby"] = True
        self._save_ops()
        self.report("대기 모드(standby)", "resume 명령을 기다림", "명령")
        last_beat = self.clock()
        while True:
            self.sleep(self.poll)
            origin = self.ops.fetch()
            c = self._new_command() if origin else None
            if c:
                a = c["action"]
                if a == "stop":
                    self._ack(c, "실행 종료")
                    return "stop"
                if a == "update":
                    self._ack(c, "대기 중 코드 갱신")
                    if self._pull_then(base, origin) == "reload":
                        return "reload"
                    self.report("대기 모드(standby)", "resume 명령을 기다림", "코드 갱신(코드 변경 없음)")
                    continue
                if a in ("resume", "restart", "rerun", "retry"):
                    if a == "rerun":
                        self._forget(list(c.get("steps") or []))
                    self._ack(c, "대기 모드 해제, 실행 재개")
                    self.o["standby"] = False
                    self._save_ops()
                    return self._pull_then(base, origin)
                self._ack(c, "대기 모드에서는 할 일 없음")
            now = self.clock()
            if now - last_beat >= self.heartbeat:
                last_beat = now
                self.report("대기 모드(standby)", "resume 명령을 기다림", "정기 보고")

    def _pull_then(self, base: str, origin: str | None) -> str:
        if origin:
            print(f"[{self.label}] git pull: {self.ops.pull()}", flush=True)
        new = self.ops.head()
        if any(_is_code(f) for f in self.ops.changed(base, new)):
            return "reload"
        return "retry"

    # ---- main loop ----
    def run(self) -> int:
        self.log.parent.mkdir(parents=True, exist_ok=True)
        self._save_ops()
        while True:
            base = self.ops.head()
            if self.o.get("standby"):                                # standby survives a reload
                what = self.standby_wait(base)
                if what == "stop":
                    self.report("중지", "없음(명령으로 종료)", "대기 모드에서 stop")
                    return 3
                self.o["attempt"] += 1
                self._save_ops()
                if what == "reload":
                    return RELOAD
                continue
            rc, stopped, cmd = self.run_child()
            if rc == 0 and not stopped:
                self.o["wait_since"], self.o["blind"] = None, 0
                self._save_ops()
                self.report("완료", "없음(모든 단계 끝)")
                return 0
            if cmd:
                if cmd["action"] == "stop":
                    self._ack(cmd, "실행 종료")
                    self.report("중지", "없음(명령으로 종료)", stopped)
                    return 3
                if cmd["action"] == "standby":
                    self._ack(cmd, "자식 종료, 대기 모드 진입")
                    self.o["standby"] = True
                    self._save_ops()
                    continue
                if cmd["action"] == "update":                        # acknowledged on receipt
                    self.o["attempt"] += 1
                    self._save_ops()
                    self.report("명령 처리", "끌어온 코드로 다시 실행", stopped)
                    if self._pull_then(base, self.ops.fetch()) == "reload":
                        return RELOAD
                    continue
                if cmd["action"] == "rerun":
                    self._forget(list(cmd.get("steps") or []))
                if cmd["action"] in ("restart", "rerun"):
                    self._ack(cmd, "자식 종료 후 재실행")
                    self.o["attempt"] += 1
                    self._save_ops()
                    self.report("명령 처리", "끌어온 코드로 다시 실행", stopped)
                    if self._pull_then(base, self.ops.fetch()) == "reload":
                        return RELOAD
                    continue
                self._ack(cmd, "자식 종료, 수정 대기")
            if not self.retry:
                self.report("실패", "없음(--no-retry)", stopped or f"코드 {rc}")
                return 1
            self.report("실패 후 대기", "새 코드나 명령을 기다림", stopped or f"코드 {rc}")
            print(f"\n[{self.label}] step failed; waiting for new code on main or a command ({paths.CMD}/{self.study}.json)",
                  flush=True)
            what = self.wait_for_fix(base)
            if what == "standby":
                self.o["standby"], self.o["wait_since"] = True, None
                self._save_ops()
                continue
            if what in ("stop", "give-up"):
                self.report("중지" if what == "stop" else "실패", "없음",
                            "명령으로 종료" if what == "stop" else f"{self.max_wait / 3600:.0f}시간 동안 수정 없음")
                return 3 if what == "stop" else 1
            self.o["attempt"] += 1
            self.o["wait_since"] = None
            self._save_ops()
            if what == "reload":
                return RELOAD


def supervise(module: str, argv: list[str], runner: Path, state: Path, steps: list, label: str, log: Path, **kw) -> int:
    return Supervisor(module, argv, runner, state, steps, label, log, **kw).run()
