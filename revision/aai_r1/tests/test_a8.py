"""A8 (DESIGN.md 10): target plan, the LoRA layer and its merge, the training loop on a tiny random Qwen2, the
model map of the bench driver. No real data, no downloads."""
from __future__ import annotations

import asyncio
import json

import numpy as np
import pandas as pd
import pytest

from v21r import a8 as A8
from v21r import peaos_driver_a8 as PD


def _corpus(n=30):
    rng = np.random.default_rng(0)
    F = rng.uniform(0, 1, n)
    I = rng.uniform(0, 1, n)
    return pd.DataFrame({"sha": [f"{i:04d}" for i in range(n)], "text": [f"q{i}" for i in range(n)],
                         "T": 1 - F, "I": I, "F": F, "split": ["train"] * 20 + ["val"] * 5 + ["test"] * 5})


def test_plan_keeps_train_and_val_and_the_check_sample():
    df = _corpus()
    full = A8.plan(df, check=False)
    assert set(full.split) == {"train", "val"} and len(full) == 25
    assert set(full.cls) <= {"harm", "dilemma", "safe"}
    small = A8.plan(df, check=True)
    assert (small.groupby("cls").size() <= A8.CHECK_PER_CLASS).all()
    assert set(small.split) == {"train", "val"}


def test_request_by_class():
    tp = {"refusal": "I'm sorry.", "deliberation": "Answer carefully."}
    assert A8.request({"cls": "harm", "text": "x"}, tp) is None
    s = A8.request({"cls": "safe", "text": "x"}, tp)
    assert s["messages"] == [{"role": "user", "content": "x"}] and s["model"] == A8.BASE
    d = A8.request({"cls": "dilemma", "text": "x"}, tp)
    assert d["messages"][0] == {"role": "system", "content": "Answer carefully."}
    assert d["options"]["seed"] == 42 and d["options"]["temperature"] == 0.3


def test_model_map_argv_and_wrapper():
    argv, m = PD.split_argv(["run", "--out", "d", "--model-map", '{"a:1": "b:2"}', "--arms", "H05"])
    assert argv == ["run", "--out", "d", "--arms", "H05"] and m == {"a:1": "b:2"}
    seen = []

    class Cfg:
        model = "a:1"

    class Client:
        _ollama_config = Cfg()

        async def call_local(self, system_prompt="", user_prompt="", model_override="", max_tokens=None, stop=None,
                             options=None):
            seen.append(model_override)
            return "ok"

    class L:
        EvalLLMClient = Client

    PD.remap(L, m, judge="judge:9")
    c = Client()
    asyncio.run(c.call_local(user_prompt="hi"))                    # the arm's own model -> replaced
    asyncio.run(c.call_local(user_prompt="hi", model_override="judge:9"))
    assert seen == ["b:2", "judge:9"]


torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")


def test_lora_merge_equals_the_adapted_forward():
    from v21r import a8_train as T
    torch.manual_seed(0)
    base = torch.nn.Module()
    base.q_proj = torch.nn.Linear(8, 6)
    names = T.wrap(base, r=2, alpha=4, dropout=0.0)
    assert names == ["q_proj"]
    with torch.no_grad():
        base.q_proj.B.normal_()
    x = torch.randn(3, 8)
    y = base.q_proj(x)
    ad = T.merge(base, names)
    assert isinstance(base.q_proj, torch.nn.Linear) and set(ad) == {"q_proj.lora_A", "q_proj.lora_B"}
    assert torch.allclose(base.q_proj(x), y, atol=1e-5)


def _tiny_qwen():
    from transformers import Qwen2Config, Qwen2ForCausalLM
    cfg = Qwen2Config(vocab_size=64, hidden_size=16, intermediate_size=32, num_hidden_layers=2, num_attention_heads=2,
                      num_key_value_heads=1, max_position_embeddings=128)
    return Qwen2ForCausalLM(cfg).to(torch.bfloat16)


class _Tok:
    """Chat template stand-in: user ids then assistant ids, as a real template extends the prompt."""
    pad_token_id, eos_token_id = 0, 1

    def apply_chat_template(self, msgs, add_generation_prompt=False, tokenize=True):
        ids = []
        for m in msgs:
            ids += [2 if m["role"] == "user" else 3] + [4 + (ord(ch) % 50) for ch in m["content"]] + [1]
        return ids + ([3] if add_generation_prompt else [])


def test_encode_masks_the_prompt():
    from v21r import a8_train as T
    ids, lab = T.encode(_Tok(), "ab", "cd", max_len=64)
    p = _Tok().apply_chat_template([{"role": "user", "content": "ab"}], add_generation_prompt=True)
    assert lab[:len(p)] == [-100] * len(p) and lab[len(p):] == ids[len(p):]


def test_train_runs_and_lowers_the_loss_on_a_tiny_model():
    from v21r import a8_train as T
    model = _tiny_qwen()
    data = [{"split": "train" if i < 16 else "val", "cls": "safe", "text": "hello", "target": "world" * 3}
            for i in range(20)]
    hp = dict(T.HP, batch=4, accum=1, epochs=8, lr=5e-2, r=4, alpha=8, dropout=0.0)
    rep = T.train(model, _Tok(), data, hp, torch.device("cpu"), log=lambda *_: None)
    assert rep["steps"] == 32 and rep["wrapped"] == 2 * 7
    assert rep["val_loss_after"] < rep["val_loss_before"]
    assert all(isinstance(m, torch.nn.Linear) for n, m in model.named_modules() if n.endswith("q_proj"))
    json.dumps({k: v for k, v in rep.items() if k != "adapters"})
