"""The satellite in orbit between missions: beacons and commands with nothing running.

    python -m ops.station   # from revision/aai_r1; start once on the PC; it idles, beacons every 10 min and waits for a mission

Commands in revision/aai_r1/commands/station.json on main (same channel as the pipelines, executed once, echoed in the beacon):
    launch  {"module": "ops.run", "args": [...]}  run that pipeline (its own launcher, supervisor and
            beacons); the station waits for it and returns to standby when it ends
    update  pull main; restart the station on new code (only between missions)
    stop    end the station
Only modules named <pkg>.run are launched. Beacon: results/station/status.json and status.md.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from . import paths
from .gitutil import git
from .supervisor import RELOAD, Ops, _env_f, _is_code, launch

STATION_ACTIONS = ("launch", "update", "stop")
MODULE = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)*\.run$")
RUNNER = paths.RESULTS / "station"
STATE = paths.CACHE / "station_ops.json"


def _recent(c: dict, now: float, hours: float = 6) -> bool:
    try:
        import calendar
        t = calendar.timegm(time.strptime(str(c.get("issued_utc")), "%Y-%m-%d %H:%M:%S"))
    except ValueError:
        return False
    return 0 <= now - t <= hours * 3600


class StationOps(Ops):
    def command(self) -> dict | None:
        r = git("show", f"origin/main:{paths.CMD}/station.json")
        if r.returncode:
            return None
        try:
            c = json.loads(r.stdout)
        except json.JSONDecodeError:
            return None
        return c if isinstance(c, dict) and c.get("id") and c.get("action") in STATION_ACTIONS else None


class Station:
    def __init__(self, argv: list[str], ops: Ops | None = None, popen=subprocess.Popen, clock=time.time,
                 sleep=time.sleep, runner: Path = RUNNER, state: Path = STATE):
        self.ops = ops or StationOps("station")
        self.popen, self.clock, self.sleep, self.runner, self.state = popen, clock, sleep, runner, state
        self.heartbeat = _env_f("PEINN2_HEARTBEAT_MIN", 10) * 60
        self.poll = _env_f("PEINN2_POLL_MIN", 2) * 60
        try:
            self.o = json.loads(state.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            self.o = {}
        self.o.setdefault("done_cmds", [])
        self.o.setdefault("seq", 0)
        self.o.setdefault("ack", None)
        self.o.setdefault("history", [])
        if "--fresh" in argv:            # an old command already on main is history; one issued in the last 6 h waits
            c = self.ops.command()
            if c and c["id"] not in self.o["done_cmds"] and not _recent(c, self.clock()):
                self.o["done_cmds"].append(c["id"])
        self.mission = None

    def _save(self) -> None:
        self.state.parent.mkdir(parents=True, exist_ok=True)
        self.state.write_text(json.dumps(self.o, indent=1, ensure_ascii=False), encoding="utf-8")

    def beacon(self, verdict: str, reason: str = "") -> None:
        now = self.clock()
        self.o["seq"] += 1
        self._save()
        head = self.ops.head()
        b = {"verdict": verdict, "seq": self.o["seq"], "mission": self.mission,
             "time_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now)),
             "time_local": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
             "code": self.ops.subject(head) if head else None, "gpu": self.ops.gpu(), "ack": self.o["ack"],
             "reason": reason, "history": self.o["history"][-5:], "beacon_min": self.heartbeat / 60,
             "poll_min": self.poll / 60}
        L = [f"# 위성(station) 상태: {verdict}", "",
             f"- 시각 {b['time_local']} (UTC {b['time_utc']}), 비컨 #{b['seq']} (주기 {b['beacon_min']:g}분, 명령 확인 "
             f"{b['poll_min']:g}분마다, 명령 파일 `{paths.CMD}/station.json`)",
             f"- 임무: {self.mission or '없음(대기)'}", f"- 실행 코드: {b['code']}", f"- GPU: {b['gpu']}",
             f"- 마지막으로 처리한 명령: {b['ack'] or '없음'}", f"- 사유: {reason or '–'}",
             "- 최근 임무: " + ("; ".join(f"{h['module']} → 코드 {h['rc']} ({h['end_utc']} UTC)" for h in b["history"]) or "없음")]
        self.runner.mkdir(parents=True, exist_ok=True)
        (self.runner / "status.md").write_text("\n".join(L) + "\n", encoding="utf-8")
        (self.runner / "status.json").write_text(json.dumps(b, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        self.ops.push([self.runner], f"station: {verdict}")

    def _ack(self, c: dict, what: str) -> None:
        self.o["done_cmds"].append(c["id"])
        self.o["ack"] = f"{c['id']} {c['action']} ({what}, {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(self.clock()))} UTC)"
        self._save()
        print(f"[station] command {c['id']}: {c['action']} ({what})", flush=True)

    def run_mission(self, module: str, args: list[str]) -> int:
        """Run a pipeline launcher and wait; its own supervisor beacons on its own channel."""
        self.mission = module
        self.beacon("임무 실행 중", f"{module} 시작")
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        p = self.popen([sys.executable, "-u", "-m", module, *args], cwd=paths.RUN, env=env)
        last = self.clock()
        while p.poll() is None:
            self.sleep(self.poll)
            if self.clock() - last >= self.heartbeat:
                last = self.clock()
                self.beacon("임무 실행 중", "정기 보고")
        rc = p.wait()
        self.o["history"].append({"module": module, "rc": rc,
                                  "end_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(self.clock()))})
        self.mission = None
        self._save()
        self.beacon("대기", f"{module} 종료(코드 {rc})")
        return rc

    def run(self) -> int:
        self._save()
        self.beacon("대기", "시작")
        last = self.clock()
        while True:
            self.sleep(self.poll)
            origin = self.ops.fetch()
            c = self._new() if origin else None
            if c:
                a = c["action"]
                if a == "stop":
                    self._ack(c, "위성 종료")
                    self.beacon("종료", "명령")
                    return 0
                if a == "update":
                    base = self.ops.head()
                    self.ops.pull()
                    self._ack(c, "코드 갱신")
                    if any(_is_code(f) for f in self.ops.changed(base, self.ops.head())):
                        self.beacon("재시작", "새 코드로 위성 재시작")
                        return RELOAD
                    self.beacon("대기", "코드 갱신(코드 변경 없음)")
                    last = self.clock()
                    continue
                if a == "launch":
                    module, args = str(c.get("module", "")), [str(x) for x in c.get("args") or []]
                    if not MODULE.match(module):
                        self._ack(c, f"거부: 허용되지 않은 모듈 {module!r}")
                        self.beacon("대기", "명령 거부")
                        continue
                    self.ops.pull()                                 # missions start on the latest main
                    self._ack(c, f"임무 시작 {module}")
                    self.run_mission(module, args)
                    last = self.clock()
                    continue
            if self.clock() - last >= self.heartbeat:
                last = self.clock()
                self.beacon("대기", "정기 보고")

    def _new(self) -> dict | None:
        c = self.ops.command()
        return c if c and c["id"] not in self.o["done_cmds"] else None


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--inner" in argv:
        return Station([a for a in argv if a != "--inner"]).run()
    return launch("ops.station", argv)


if __name__ == "__main__":
    sys.exit(main())
