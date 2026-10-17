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


def _tiny_qwen2(d, tied=True):
    """A one-layer Qwen2 checkpoint in bf16 safetensors with a 6-token BPE vocabulary and two added tokens."""
    import json as _j
    import struct
    d.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(0)
    H, F, V = 8, 16, 10
    shapes = {"model.embed_tokens.weight": (V, H), "model.norm.weight": (H,),
              "model.layers.0.self_attn.q_proj.weight": (H, H), "model.layers.0.self_attn.q_proj.bias": (H,),
              "model.layers.0.self_attn.k_proj.weight": (4, H), "model.layers.0.self_attn.k_proj.bias": (4,),
              "model.layers.0.self_attn.v_proj.weight": (4, H), "model.layers.0.self_attn.v_proj.bias": (4,),
              "model.layers.0.self_attn.o_proj.weight": (H, H), "model.layers.0.mlp.gate_proj.weight": (F, H),
              "model.layers.0.mlp.up_proj.weight": (F, H), "model.layers.0.mlp.down_proj.weight": (H, F),
              "model.layers.0.input_layernorm.weight": (H,), "model.layers.0.post_attention_layernorm.weight": (H,)}
    if not tied:
        shapes["lm_head.weight"] = (V, H)
    head, blob, vals = {}, b"", {}
    for k, s in shapes.items():
        x = rng.normal(0, 1, s).astype(np.float32)
        u = (x.view(np.uint32) >> 16).astype(np.uint16)
        vals[k] = (u.astype(np.uint32) << 16).view(np.float32)
        head[k] = {"dtype": "BF16", "shape": list(s), "data_offsets": [len(blob), len(blob) + u.nbytes]}
        blob += u.tobytes()
    hj = _j.dumps(head).encode()
    (d / "model.safetensors").write_bytes(struct.pack("<Q", len(hj)) + hj + blob)
    (d / "config.json").write_text(_j.dumps({"model_type": "qwen2", "num_hidden_layers": 1, "max_position_embeddings": 64,
                                             "hidden_size": H, "intermediate_size": F, "num_attention_heads": 2,
                                             "num_key_value_heads": 1, "rope_theta": 1e6, "rms_norm_eps": 1e-6,
                                             "tie_word_embeddings": tied}))
    vocab = {"a": 0, "b": 1, "ab": 2, "c": 3, "abc": 4, "Ġ": 5}
    added = [{"id": 6, "content": "<|endoftext|>", "special": True}, {"id": 7, "content": "<|im_end|>", "special": True},
             {"id": 8, "content": "<|fim_pad|>", "special": False}]
    (d / "tokenizer.json").write_text(_j.dumps({"model": {"type": "BPE", "vocab": vocab, "merges": [["a", "b"], "ab c"]},
                                                "added_tokens": added}))
    (d / "tokenizer_config.json").write_text(_j.dumps({"eos_token": "<|im_end|>", "pad_token": "<|endoftext|>",
                                                       "bos_token": None, "chat_template": "{{ x }}"}))
    return vals


@pytest.mark.parametrize("tied", [True, False])
def test_gguf_qwen2_writes_what_llama_cpp_writes(tmp_path, tied):
    import struct
    from v21r import gguf_qwen2 as G
    from v21r import wcheck as W
    vals = _tiny_qwen2(tmp_path / "m", tied)
    out = tmp_path / "m.f16.gguf"
    rep = G.write(tmp_path / "m", out, "tiny", log=lambda *_: None)
    assert rep["tensors"] == 15 and rep["vocab"] == 10
    assert G.check(tmp_path / "m", out, log=lambda *_: None)["ok"]
    with open(out, "rb") as h:
        h.read(4)
        _, nt, nk = struct.unpack("<IQQ", h.read(20))
        kv = {}
        for _ in range(nk):
            k = W._str(h)
            (t,) = struct.unpack("<I", h.read(4))
            kv[k] = W._val(h, t)
    assert kv["general.architecture"] == "qwen2" and kv["general.file_type"] == 1
    assert kv["qwen2.attention.head_count_kv"] == 1 and kv["qwen2.context_length"] == 64
    assert kv["tokenizer.ggml.tokens"] == ["a", "b", "ab", "c", "abc", "Ġ", "<|endoftext|>", "<|im_end|>", "<|fim_pad|>",
                                           "[PAD9]"]
    assert kv["tokenizer.ggml.token_type"] == [1, 1, 1, 1, 1, 1, 3, 3, 3, 5]     # <|..|> looks special; padding unused
    assert kv["tokenizer.ggml.merges"] == ["a b", "ab c"]
    assert (kv["tokenizer.ggml.eos_token_id"], kv["tokenizer.ggml.padding_token_id"],
            kv["tokenizer.ggml.bos_token_id"], kv["tokenizer.ggml.add_bos_token"]) == (7, 6, 6, False)
    _, g = W.read_gguf(out)
    assert g["blk.0.attn_q.weight"][1] == W.GGUF_F16 and g["blk.0.attn_q.bias"][1] == W.GGUF_F32
    assert g["blk.0.attn_k.weight"][0] == (4, 8) and g["blk.0.ffn_down.weight"][0] == (8, 16)
    want = vals["model.embed_tokens.weight"] if tied else vals["lm_head.weight"]
    assert np.array_equal(W.gguf_tensor(out, g["output.weight"]), want.astype(np.float16).astype(np.float32))
    assert np.array_equal(W.gguf_tensor(out, g["blk.0.attn_q.weight"]),        # no llama q/k permutation for Qwen2
                          vals["model.layers.0.self_attn.q_proj.weight"].astype(np.float16).astype(np.float32))


def test_gguf_qwen2_check_catches_a_changed_tensor(tmp_path):
    from v21r import gguf_qwen2 as G
    from v21r import wcheck as W
    _tiny_qwen2(tmp_path / "m")
    out = tmp_path / "m.gguf"
    G.write(tmp_path / "m", out, "tiny", log=lambda *_: None)
    _, g = W.read_gguf(out)
    shape, t, off = g["blk.0.ffn_up.weight"]
    a = np.memmap(out, dtype=np.float16, mode="r+", offset=off, shape=shape)
    a[0, 0] += 1
    a.flush()
    del a
    r = G.check(tmp_path / "m", out, log=lambda *_: None)
    assert not r["ok"] and r["unequal"] == ["blk.0.ffn_up.weight"]
