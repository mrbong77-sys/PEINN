"""A8: peaos_driver.py run, plus --model-map JSON {served model: replacement}.

    python peaos_driver_a8.py run --out DIR --tag a8 --runs JSON --arms H05 --phase gen|judge --judge M
        --model-map '{"qwen2.5:7b-instruct": "qwen2.5-a8:latest"}'

The map is applied to every generation call before the seed and store layer sees it (so stored answers key on the
replacement model); judge calls use their own model and are left alone. Everything else is peaos_driver.py.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _driver():
    spec = importlib.util.spec_from_file_location("peaos_driver", HERE / "peaos_driver.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def remap(L, mapping: dict, judge: str | None) -> None:
    """Outermost wrapper of EvalLLMClient.call_local: replace the model of generation calls found in `mapping`."""
    inner = L.EvalLLMClient.call_local
    jk = (judge or "").split(":latest")[0]

    async def call(self, system_prompt="", user_prompt="", model_override="", max_tokens=None, stop=None, options=None):
        m = model_override or getattr(getattr(self, "_ollama_config", None), "model", "") or ""
        if m in mapping and m.split(":latest")[0] != jk:
            model_override = mapping[m]
        return await inner(self, system_prompt=system_prompt, user_prompt=user_prompt, model_override=model_override,
                           max_tokens=max_tokens, stop=stop, options=options)
    L.EvalLLMClient.call_local = call


def split_argv(argv: list[str]) -> tuple[list[str], dict]:
    argv = list(argv)
    if "--model-map" not in argv:
        return argv, {}
    i = argv.index("--model-map")
    mapping = json.loads(argv[i + 1])
    del argv[i:i + 2]
    return argv, mapping


def main(argv=None) -> int:
    argv, mapping = split_argv(sys.argv[1:] if argv is None else argv)
    P = _driver()
    seeds = P.seeds

    def seeds_then_remap(E, L, judge, out, tag, phase, capture=None):
        seeds(E, L, judge, out, tag, phase, capture)
        if mapping:
            remap(L, mapping, judge)
            print(f"[a8] generation model map {mapping}", flush=True)
    P.seeds = seeds_then_remap
    return P.main(argv)


if __name__ == "__main__":
    sys.exit(main())
