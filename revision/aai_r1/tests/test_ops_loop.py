"""The closed ground loop (ops/supervisor.py, ported from PEINN_v2) with a fake git and fake children."""
from __future__ import annotations

import json
import threading

from ops import supervisor as SV


class Clock:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


class FakeOps:
    def __init__(self, clock):
        self.clock = clock
        self.local, self.origin = "c0", "c0"
        self.files = {}                     # commit -> changed files relative to the previous one
        self.cmd = None
        self.pushes, self.killed, self.pulls = [], [], 0
        self.on_poll = None                 # callback(clock time) -> may push code or commands

    def head(self):
        return self.local

    def subject(self, rev):
        return f"{rev} subject"

    def fetch(self):
        if self.on_poll:
            self.on_poll(self)
        return self.origin

    def changed(self, a, b):
        order = sorted(set([a, b]) | set(self.files), key=lambda c: int(c[1:]))
        lo, hi = int(a[1:]), int(b[1:])
        return [f for c in order if lo < int(c[1:]) <= hi for f in self.files.get(c, [])]

    def pull(self):
        self.pulls += 1
        self.local = self.origin
        return "pulled"

    def command(self):
        return self.cmd

    def push(self, targets, message):
        self.pushes.append(message)
        return True

    def gpu(self):
        return "1000 MiB, 32607 MiB, 50 %, 60"

    def kill(self, p):
        self.killed.append(p)
        p.kill()

    def commit(self, files):
        n = f"c{int(self.origin[1:]) + 1}"
        self.files[n] = files
        self.origin = n


class FakeChild:
    """Prints its lines, then exits with rc; with hang=True it never exits until killed."""

    def __init__(self, lines, rc, hang=False):
        self.rc, self.hang, self.done = rc, hang, threading.Event()
        self.pid = 123
        self._lines = [(ln + "\n").encode() for ln in lines]
        self.stdout = self._iter()

    def _iter(self):
        yield from self._lines
        if self.hang:
            self.done.wait(5)
        self.done.set()

    def poll(self):
        if self.hang and not self.done.is_set():
            return None
        self.done.wait(5)
        return self.rc

    def wait(self):
        self.done.wait(5)
        return self.rc

    def kill(self):
        self.rc = -9
        self.done.set()


def make(tmp_path, children, ops, clock, argv=(), steps=("A", "B")):
    state = tmp_path / "scale_state.json"
    it = iter(children)

    def popen(cmd, **kw):
        assert cmd[3:5] == ["ops.run", "--child"]
        return next(it)()

    sv = SV.Supervisor("ops.run", list(argv), tmp_path / "runner", state,
                       [(s, s, None) for s in steps], "test", tmp_path / "log.txt", ops=ops, popen=popen,
                       clock=clock, sleep=clock.sleep, tick=60)
    return sv, state


def test_failure_waits_then_new_code_reloads_the_supervisor(tmp_path, monkeypatch):
    monkeypatch.setenv("PEINN2_POLL_MIN", "5")
    clock = Clock()
    ops = FakeOps(clock)
    sv, state = make(tmp_path, [lambda: FakeChild(["[scale] ===== A: a =====", "boom"], 1)], ops, clock, ["--fresh"])
    polls = []

    def on_poll(o):
        polls.append(clock())
        if len(polls) == 3:
            o.commit(["ops/study.py"])      # the ground station pushes a fix
    ops.on_poll = on_poll
    assert sv.run() == SV.RELOAD
    assert ops.local == "c1" and ops.pulls == 1
    st = json.loads((tmp_path / "runner" / "status.json").read_text(encoding="utf-8"))
    assert st["verdict"] == "실패 후 대기" and st["step"] == "A"
    assert json.loads((tmp_path / "scale_ops.json").read_text())["attempt"] == 2
    assert clock() - 1_000_000 < 20 * 60                 # retried within minutes, not after a fixed wait


def test_results_only_commits_do_not_count_as_a_fix_and_blind_retry_succeeds(tmp_path, monkeypatch):
    monkeypatch.setenv("PEINN2_RETRY_WAIT_MIN", "30")
    clock = Clock()
    ops = FakeOps(clock)
    ops.on_poll = lambda o: o.commit(["results/scale/x.json"]) if o.origin == "c0" else None
    sv, _ = make(tmp_path, [lambda: FakeChild(["x"], 1), lambda: FakeChild(["ok"], 0)], ops, clock, ["--fresh"])
    t0 = clock()
    assert sv.run() == 0
    assert clock() - t0 >= 30 * 60
    assert json.loads((tmp_path / "runner" / "status.json").read_text(encoding="utf-8"))["verdict"] == "완료"


def test_rerun_command_while_running_forgets_steps_and_runs_again(tmp_path, monkeypatch):
    monkeypatch.setenv("PEINN2_POLL_MIN", "1")
    clock = Clock()
    ops = FakeOps(clock)
    sv, state = make(tmp_path, [lambda: FakeChild(["[scale] ===== B: b ====="], 0, hang=True),
                                lambda: FakeChild(["ok"], 0)], ops, clock, ["--fresh"])
    state.write_text(json.dumps({"done": {"A": "t"}}))

    def on_poll(o):
        o.cmd = {"id": "cmd-1", "action": "rerun", "steps": ["A"]}
    ops.on_poll = on_poll
    assert sv.run() == 0
    assert ops.killed and "A" not in json.loads(state.read_text())["done"]
    st = json.loads((tmp_path / "runner" / "status.json").read_text(encoding="utf-8"))
    assert st["ack"].startswith("cmd-1 rerun")


def test_stall_kills_the_child_and_stop_command_ends_the_wait(tmp_path, monkeypatch):
    monkeypatch.setenv("PEINN2_STALL_MIN", "10")
    monkeypatch.setenv("PEINN2_POLL_MIN", "100")
    clock = Clock()
    ops = FakeOps(clock)
    sv, _ = make(tmp_path, [lambda: FakeChild(["start"], 0, hang=True)], ops, clock, ["--fresh"])
    seen = []

    def on_poll(o):
        seen.append(1)
        if len(seen) >= 1:
            o.cmd = {"id": "cmd-stop", "action": "stop"}
    ops.on_poll = on_poll
    assert sv.run() == 3
    assert ops.killed
    assert any("실패 후 대기" in m for m in ops.pushes)
    st = json.loads((tmp_path / "runner" / "status.json").read_text(encoding="utf-8"))
    assert st["verdict"] == "중지"


def test_fresh_start_treats_an_old_command_as_history(tmp_path):
    clock = Clock()
    ops = FakeOps(clock)
    ops.cmd = {"id": "old", "action": "stop"}
    sv, _ = make(tmp_path, [lambda: FakeChild(["ok"], 0)], ops, clock, ["--fresh"])
    assert sv.run() == 0


def test_heartbeat_reports_while_running(tmp_path, monkeypatch):
    monkeypatch.setenv("PEINN2_HEARTBEAT_MIN", "30")
    monkeypatch.setenv("PEINN2_POLL_MIN", "1000")
    clock = Clock()
    ops = FakeOps(clock)
    child = FakeChild(["[scale] ===== D1-evaluate: x ====="], 0, hang=True)
    sv, _ = make(tmp_path, [lambda: child], ops, clock, ["--fresh"])
    beats = []
    orig = sv.report

    def report(verdict, *a, **k):
        beats.append(verdict)
        if beats.count("실행 중") >= 3:
            child.kill()
            child.rc = 0
        return orig(verdict, *a, **k)
    sv.report = report
    assert sv.run() == 0
    assert beats.count("실행 중") >= 3                 # start + heartbeats
    st = json.loads((tmp_path / "runner" / "status.json").read_text(encoding="utf-8"))
    assert st["gpu"].startswith("1000 MiB")


def test_launcher_restarts_on_reload_and_marks_only_the_first_start_fresh():
    calls = []

    def call(cmd, **kw):
        calls.append(cmd)
        return SV.RELOAD if len(calls) == 1 else 0
    assert SV.launch("ops.run", ["--restart"], call=call) == 0
    assert "--fresh" in calls[0] and "--restart" in calls[0]
    assert "--fresh" not in calls[1] and "--restart" not in calls[1] and "--inner" in calls[1]


def test_real_git_round_trip_telemetry_fix_and_command(tmp_path, monkeypatch):
    """Real git: the PC pushes telemetry to a bare origin; the ground pushes a .py fix from another clone; the PC
    sees it, pulls and asks for a reload. Then a command file is acknowledged."""
    import subprocess
    import sys
    from ops import gitutil, paths

    def sh(*a, cwd):
        subprocess.run(a, cwd=cwd, check=True, capture_output=True)
    origin, pc, ground = tmp_path / "origin.git", tmp_path / "pc", tmp_path / "ground"
    sh("git", "init", "-q", "--bare", "-b", "main", str(origin), cwd=tmp_path)
    sh("git", "clone", "-q", str(origin), str(pc), cwd=tmp_path)
    for d in (pc,):
        sh("git", "config", "user.email", "t@t", cwd=d)
        sh("git", "config", "user.name", "t", cwd=d)
    (pc / "a.py").write_text("x = 1\n")
    sh("git", "add", ".", cwd=pc)
    sh("git", "commit", "-q", "-m", "init", cwd=pc)
    sh("git", "push", "-q", "origin", "HEAD:main", cwd=pc)
    sh("git", "clone", "-q", str(origin), str(ground), cwd=tmp_path)
    sh("git", "config", "user.email", "g@g", cwd=ground)
    sh("git", "config", "user.name", "g", cwd=ground)
    monkeypatch.setattr(paths, "REPO", pc)
    monkeypatch.setattr(gitutil.time, "sleep", lambda s: None)
    monkeypatch.setenv("PEINN2_POLL_MIN", "1")
    clock = Clock()
    pushed = []

    def sleep(s):
        clock.sleep(s)
        if not pushed:                                   # the ground station reacts to the failure telemetry
            sh("git", "pull", "-q", "origin", "main", cwd=ground)
            assert "실패 후 대기" in (ground / "results" / "runner" / "status.md").read_text(encoding="utf-8")
            (ground / "a.py").write_text("x = 2\n")
            sh("git", "commit", "-qam", "fix", cwd=ground)
            sh("git", "push", "-q", "origin", "HEAD:main", cwd=ground)
            pushed.append(1)

    def popen(cmd, **kw):
        return subprocess.Popen([sys.executable, "-c", "print('[scale] ===== A: a ====='); print('boom'); raise SystemExit(1)"],
                                cwd=pc, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    sv = SV.Supervisor("ops.run", ["--fresh"], pc / "results" / "runner", pc / ".cache" / "scale_state.json",
                       [("A", "a", None)], "test", pc / ".cache" / "log.txt", popen=popen, clock=clock, sleep=sleep, tick=0.05)
    (pc / ".gitignore").write_text(".cache/\n")
    assert sv.run() == SV.RELOAD
    assert (pc / "a.py").read_text() == "x = 2\n"           # the fix reached the PC's checkout
    # a command written by the ground is read from origin and acknowledged once
    (ground / paths.CMD).mkdir(parents=True)
    (ground / paths.CMD / "scale.json").write_text(json.dumps({"id": "c-1", "action": "stop"}))
    sh("git", "add", ".", cwd=ground)
    sh("git", "commit", "-qm", "cmd", cwd=ground)
    sh("git", "push", "-q", "origin", "HEAD:main", cwd=ground)
    sv2 = SV.Supervisor("ops.run", [], pc / "results" / "runner", pc / ".cache" / "scale_state.json",
                        [("A", "a", None)], "test", pc / ".cache" / "log.txt", popen=popen, clock=clock,
                        sleep=clock.sleep, tick=0.05)
    assert sv2.run() == 3
    sh("git", "pull", "-q", "origin", "main", cwd=ground)
    st = json.loads((ground / "results" / "runner" / "status.json").read_text(encoding="utf-8"))
    assert st["verdict"] == "중지" and st["ack"].startswith("c-1 stop")
    assert not (pc / ".git" / "peinn-ops-git.lock").exists()


def test_git_lock_is_exclusive_and_clears_stale(tmp_path, monkeypatch):
    import os
    import time as _t
    from ops import gitutil, paths
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(paths, "REPO", tmp_path)
    lock = tmp_path / ".git" / "peinn-ops-git.lock"
    with gitutil.locked():
        assert lock.exists()
    assert not lock.exists()
    lock.write_text("999")
    old = _t.time() - 3600
    os.utime(lock, (old, old))
    with gitutil.locked(timeout=2):
        assert lock.read_text() != "999"


class SlowClock(Clock):
    """Fake time, but yields to the reader thread so child output is seen between ticks."""

    def sleep(self, s):
        import time as _t
        _t.sleep(0.002)
        self.t += s


class StagedChild(FakeChild):
    """Prints the first header, waits for `go`, prints the second header, then hangs until killed."""

    def __init__(self):
        super().__init__([], 0, hang=True)
        self.go = threading.Event()
        self.stdout = self._staged()

    def _staged(self):
        yield b"[scale] ===== A: a =====\n"
        self.go.wait(5)
        yield b"[scale] ===== B: b =====\n"
        self.done.wait(5)
        self.done.set()


def test_standby_holds_with_beacons_then_resume_runs_again(tmp_path, monkeypatch):
    monkeypatch.setenv("PEINN2_POLL_MIN", "1")
    monkeypatch.setenv("PEINN2_HEARTBEAT_MIN", "10")
    monkeypatch.setenv("PEINN2_STALL_MIN", "100000")
    clock = SlowClock()
    ops = FakeOps(clock)
    sv, _ = make(tmp_path, [lambda: FakeChild(["[scale] ===== A: a ====="], 0, hang=True),
                            lambda: FakeChild(["ok"], 0)], ops, clock, ["--fresh"])
    polls = []

    def on_poll(o):
        polls.append(clock())
        if len(polls) == 1:
            o.cmd = {"id": "s-1", "action": "standby"}
        elif len(polls) == 30:                            # ~30 min of standby, then resume
            o.cmd = {"id": "r-1", "action": "resume"}
    ops.on_poll = on_poll
    assert sv.run() == 0
    standby_beacons = [m for m in ops.pushes if "대기 모드(standby)" in m]
    assert len(standby_beacons) >= 3                       # entry + beacons every 10 min
    st = json.loads((tmp_path / "runner" / "status.json").read_text(encoding="utf-8"))
    assert st["verdict"] == "완료" and st["ack"].startswith("r-1 resume") and st["standby"] is False
    assert st["seq"] >= 5


def test_update_waits_for_the_step_boundary_then_reloads(tmp_path, monkeypatch):
    monkeypatch.setenv("PEINN2_POLL_MIN", "1")
    monkeypatch.setenv("PEINN2_STALL_MIN", "100000")
    clock = SlowClock()
    ops = FakeOps(clock)
    child = StagedChild()
    sv, _ = make(tmp_path, [lambda: child], ops, clock, ["--fresh"])
    seen = []

    def on_poll(o):
        seen.append(1)
        if len(seen) == 2:
            o.commit(["ops/study.py"])             # the fix is on main
            o.cmd = {"id": "u-1", "action": "update"}
        if len(seen) == 5:
            assert not o.killed                              # step A still running: nothing cut
            child.go.set()                                   # step A ends, step B starts
    ops.on_poll = on_poll
    assert sv.run() == SV.RELOAD
    assert ops.killed and ops.local == ops.origin
    assert json.loads((tmp_path / "scale_ops.json").read_text())["ack"].startswith("u-1 update")


def test_update_received_during_the_last_step_still_reloads(tmp_path, monkeypatch):
    monkeypatch.setenv("PEINN2_POLL_MIN", "1")
    monkeypatch.setenv("PEINN2_STALL_MIN", "100000")
    clock = SlowClock()
    ops = FakeOps(clock)
    child = FakeChild(["[scale] ===== B: b ====="], 0, hang=True)
    sv, _ = make(tmp_path, [lambda: child], ops, clock, ["--fresh"])
    seen = []

    def on_poll(o):
        seen.append(1)
        if len(seen) == 2:
            o.commit(["ops/run.py"])               # new steps are on main
            o.cmd = {"id": "u-2", "action": "update"}
        if len(seen) == 4:
            child.done.set()                                 # the last step ends: the child exits cleanly
    ops.on_poll = on_poll
    assert sv.run() == SV.RELOAD                             # not "완료": the new code may hold new steps
    assert ops.local == ops.origin


def test_standby_survives_a_reload_and_stop_ends_it(tmp_path, monkeypatch):
    monkeypatch.setenv("PEINN2_POLL_MIN", "1")
    clock = Clock()
    ops = FakeOps(clock)
    (tmp_path / "scale_ops.json").write_text(json.dumps({"attempt": 3, "blind": 0, "wait_since": None, "done_cmds": [],
                                                         "ack": None, "standby": True, "seq": 7}))
    sv, _ = make(tmp_path, [], ops, clock, [])               # reloaded supervisor: no child may start
    ops.on_poll = lambda o: setattr(o, "cmd", {"id": "x-1", "action": "stop"})
    assert sv.run() == 3
    st = json.loads((tmp_path / "runner" / "status.json").read_text(encoding="utf-8"))
    assert st["verdict"] == "중지" and st["seq"] > 7


def _station(tmp_path, ops, clock, children=(), argv=("--fresh",)):
    from ops import station as ST
    it = iter(children)
    launched = []

    def popen(cmd, **kw):
        launched.append(cmd[3:])
        return next(it)()
    st = ST.Station(list(argv), ops=ops, popen=popen, clock=clock, sleep=clock.sleep,
                    runner=tmp_path / "station", state=tmp_path / "station_ops.json")
    return st, launched


def test_station_idles_with_beacons_then_runs_a_mission_and_returns_to_standby(tmp_path, monkeypatch):
    monkeypatch.setenv("PEINN2_POLL_MIN", "2")
    monkeypatch.setenv("PEINN2_HEARTBEAT_MIN", "10")
    clock = Clock()
    ops = FakeOps(clock)
    polls = []

    def on_poll(o):
        polls.append(1)
        if len(polls) == 12:                                 # ~24 min of standby
            o.cmd = {"id": "m-1", "action": "launch", "module": "ops.run", "args": ["--no-retry"]}
        if len(polls) == 20:
            o.cmd = {"id": "s-1", "action": "stop"}
    ops.on_poll = on_poll
    st, launched = _station(tmp_path, ops, clock, [lambda: FakeChild(["mission"], 0)])
    assert st.run() == 0
    assert launched == [["ops.run", "--no-retry"]]
    b = json.loads((tmp_path / "station" / "status.json").read_text(encoding="utf-8"))
    assert b["verdict"] == "종료" and b["history"][0]["module"] == "ops.run" and b["history"][0]["rc"] == 0
    assert sum("station: 대기" in m for m in ops.pushes) >= 3   # start + idle beacons + back to standby


def test_station_refuses_modules_outside_the_repo_pipelines(tmp_path, monkeypatch):
    monkeypatch.setenv("PEINN2_POLL_MIN", "2")
    clock = Clock()
    ops = FakeOps(clock)
    polls = []

    def on_poll(o):
        polls.append(1)
        if len(polls) == 1:
            o.cmd = {"id": "bad", "action": "launch", "module": "os.system"}
        if len(polls) == 3:
            o.cmd = {"id": "s", "action": "stop"}
    ops.on_poll = on_poll
    st, launched = _station(tmp_path, ops, clock)
    seen = []
    orig = st._ack
    st._ack = lambda c, what: (seen.append((c["id"], what)), orig(c, what))
    assert st.run() == 0 and launched == []
    assert seen[0][0] == "bad" and seen[0][1].startswith("거부")


def test_station_update_reloads_on_new_code(tmp_path, monkeypatch):
    monkeypatch.setenv("PEINN2_POLL_MIN", "2")
    clock = Clock()
    ops = FakeOps(clock)

    def on_poll(o):
        if o.cmd is None:
            o.commit(["ops/station.py"])
            o.cmd = {"id": "u", "action": "update"}
    ops.on_poll = on_poll
    st, _ = _station(tmp_path, ops, clock)
    assert st.run() == SV.RELOAD and ops.local == ops.origin


def test_station_fresh_start_runs_a_recent_launch_but_not_an_old_one(tmp_path, monkeypatch):
    import time as _t
    monkeypatch.setenv("PEINN2_POLL_MIN", "2")
    for age_h, expect in ((1, [["ops.run"]]), (30, [])):
        clock = Clock()
        clock.t = _t.time()
        ops = FakeOps(clock)
        ops.cmd = {"id": f"l{age_h}", "action": "launch", "module": "ops.run",
                   "issued_utc": _t.strftime("%Y-%m-%d %H:%M:%S", _t.gmtime(clock.t - age_h * 3600))}
        polls = []

        def on_poll(o, polls=polls):
            polls.append(1)
            if len(polls) == 4:
                o.cmd = {"id": "stop", "action": "stop"}
        ops.on_poll = on_poll
        st, launched = _station(tmp_path / str(age_h), ops, clock, [lambda: FakeChild(["m"], 0)])
        assert st.run() == 0 and launched == expect






















































































