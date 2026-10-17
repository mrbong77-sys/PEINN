"""A8 serving (DESIGN.md 10): the merged Qwen2 checkpoint written as an F16 GGUF, the input llama.cpp's own
convert_hf_to_gguf.py --outtype f16 gives Ollama. Ollama then quantises it to q4_K_M; it no longer quantises a
safetensors folder to K-quants (only int4, int8, nvfp4, mxfp4, mxfp8).

No llama.cpp, no gguf package: the GGUF v3 layout is written directly. Same choices as the converter: 2-D weights
F16, 1-D tensors (norms, biases) F32, Qwen2 tensor names without the llama q/k permutation, the GPT-2 BPE vocabulary
of tokenizer.json padded to the embedding rows with unused [PADn] tokens, special ids from tokenizer_config.json.
`check` reads the file back and compares every tensor with the checkpoint.
"""
from __future__ import annotations

import json
import re
import struct
from pathlib import Path

import numpy as np

from . import wcheck as W

ALIGN = 32
T_U32, T_I32, T_F32, T_BOOL, T_STR, T_ARR = 4, 5, 6, 7, 8, 9
TOK_NORMAL, TOK_CONTROL, TOK_USER, TOK_UNUSED = 1, 3, 4, 5
_LAYER = {"self_attn.q_proj": "attn_q", "self_attn.k_proj": "attn_k", "self_attn.v_proj": "attn_v",
          "self_attn.o_proj": "attn_output", "mlp.gate_proj": "ffn_gate", "mlp.up_proj": "ffn_up",
          "mlp.down_proj": "ffn_down", "input_layernorm": "attn_norm", "post_attention_layernorm": "ffn_norm"}


def gguf_name(hf: str) -> str | None:
    fixed = {"model.embed_tokens.weight": "token_embd.weight", "model.norm.weight": "output_norm.weight",
             "lm_head.weight": "output.weight"}
    if hf in fixed:
        return fixed[hf]
    m = re.fullmatch(r"model\.layers\.(\d+)\.(.+)\.(weight|bias)", hf)
    if m and m.group(2) in _LAYER:
        return f"blk.{m.group(1)}.{_LAYER[m.group(2)]}.{m.group(3)}"
    return None


def _s(b: str) -> bytes:
    e = b.encode("utf-8")
    return struct.pack("<Q", len(e)) + e


def _kv(key: str, t: int, v) -> bytes:
    out = _s(key) + struct.pack("<I", t)
    if t == T_STR:
        return out + _s(v)
    if t == T_ARR:
        et, items = v
        out += struct.pack("<IQ", et, len(items))
        if et == T_STR:
            return out + b"".join(_s(x) for x in items)
        return out + np.asarray(items, dtype={T_I32: "<i4", T_U32: "<u4", T_F32: "<f4"}[et]).tobytes()
    return out + struct.pack({T_U32: "<I", T_I32: "<i", T_F32: "<f", T_BOOL: "<?"}[t], v)


def _looks_special(t: str) -> bool:
    """llama.cpp TextModel.does_token_look_special: added tokens of this shape are control tokens."""
    return t in ("<pad>", "<mask>", "<2mass>", "[@BOS@]") or (t.startswith("<|") and t.endswith("|>")) or \
        (t.startswith("<\uff5c") and t.endswith("\uff5c>")) or (t.startswith("<unused") and t.endswith(">"))


def vocab(src: Path, n_vocab: int) -> tuple[list, list, list, dict]:
    tj = json.loads((src / "tokenizer.json").read_text(encoding="utf-8"))
    tc = json.loads((src / "tokenizer_config.json").read_text(encoding="utf-8"))
    rev = {i: t for t, i in tj["model"]["vocab"].items()}
    added = {a["id"]: a for a in tj.get("added_tokens", [])}
    for a in added.values():
        rev[a["id"]] = a["content"]
    tokens, types = [], []
    for i in range(n_vocab):
        if i not in rev:
            tokens.append(f"[PAD{i}]")
            types.append(TOK_UNUSED)
        elif i in added:
            tokens.append(rev[i])
            types.append(TOK_CONTROL if added[i].get("special") or _looks_special(rev[i]) else TOK_USER)
        else:
            tokens.append(rev[i])
            types.append(TOK_NORMAL)
    merges = [m if isinstance(m, str) else " ".join(m) for m in tj["model"]["merges"]]
    ids = {t: i for i, t in rev.items()}
    sp = {}
    for k in ("bos", "eos", "pad"):
        tok = tc.get(f"{k}_token")
        tok = tok.get("content") if isinstance(tok, dict) else tok
        if tok in ids:
            sp[k] = ids[tok]
    if "bos" not in sp and "pad" in sp:            # as the converter does for Qwen2 (bos = <|endoftext|>)
        sp["bos"] = sp["pad"]
    sp["chat_template"] = tc.get("chat_template") or ((src / "chat_template.jinja").read_text(encoding="utf-8")
                                                     if (src / "chat_template.jinja").exists() else None)
    sp["add_bos"] = bool(tc.get("add_bos_token", False))
    return tokens, types, merges, sp


def _tensors(src: Path) -> dict:
    """{gguf name: (safetensors file, info)}; output.weight from the embedding when the head is tied."""
    out = {}
    for f in sorted(src.glob("*.safetensors")):
        for name, info in W.read_safetensors(f).items():
            g = gguf_name(name)
            if g is None:
                raise SystemExit(f"GGUF: no Qwen2 name for {name}")
            out[g] = (f, info)
    if "output.weight" not in out:
        out["output.weight"] = out["token_embd.weight"]
    return out


def _order(names) -> list:
    def key(n):
        m = re.match(r"blk\.(\d+)\.", n)
        return (1, int(m.group(1)), n) if m else (0 if n != "output_norm.weight" else 2, 0, n)
    return sorted(names, key=key)


def write(src: Path, out: Path, name: str, log=print) -> dict:
    src, out = Path(src), Path(out)
    cfg = json.loads((src / "config.json").read_text(encoding="utf-8"))
    if cfg.get("model_type") != "qwen2":
        raise SystemExit(f"GGUF: model_type {cfg.get('model_type')!r} is not qwen2")
    ts = _tensors(src)
    n_vocab = ts["token_embd.weight"][1][1][0]
    tokens, types, merges, sp = vocab(src, n_vocab)
    a = "qwen2"
    kv = [("general.architecture", T_STR, a), ("general.type", T_STR, "model"), ("general.name", T_STR, name),
          (f"{a}.block_count", T_U32, cfg["num_hidden_layers"]),
          (f"{a}.context_length", T_U32, cfg["max_position_embeddings"]),
          (f"{a}.embedding_length", T_U32, cfg["hidden_size"]),
          (f"{a}.feed_forward_length", T_U32, cfg["intermediate_size"]),
          (f"{a}.attention.head_count", T_U32, cfg["num_attention_heads"]),
          (f"{a}.attention.head_count_kv", T_U32, cfg.get("num_key_value_heads", cfg["num_attention_heads"])),
          (f"{a}.rope.freq_base", T_F32, float(cfg.get("rope_theta", 10000.0))),
          (f"{a}.attention.layer_norm_rms_epsilon", T_F32, float(cfg["rms_norm_eps"])),
          ("general.file_type", T_U32, 1),
          ("tokenizer.ggml.model", T_STR, "gpt2"), ("tokenizer.ggml.pre", T_STR, "qwen2"),
          ("tokenizer.ggml.tokens", T_ARR, (T_STR, tokens)), ("tokenizer.ggml.token_type", T_ARR, (T_I32, types)),
          ("tokenizer.ggml.merges", T_ARR, (T_STR, merges))]
    for k, key in (("eos", "eos_token_id"), ("pad", "padding_token_id"), ("bos", "bos_token_id")):
        if k in sp:
            kv.append((f"tokenizer.ggml.{key}", T_U32, sp[k]))
    kv.append(("tokenizer.ggml.add_bos_token", T_BOOL, sp["add_bos"]))
    if sp["chat_template"]:
        kv.append(("tokenizer.chat_template", T_STR, sp["chat_template"]))
    kv.append(("general.quantization_version", T_U32, 2))

    names = _order(ts)
    plan, off = [], 0
    for n in names:
        shape = ts[n][1][1]
        t = W.GGUF_F16 if len(shape) == 2 else W.GGUF_F32
        size = int(np.prod(shape)) * (2 if t == W.GGUF_F16 else 4)
        plan.append((n, shape, t, off, size))
        off += -(-size // ALIGN) * ALIGN
    head = b"GGUF" + struct.pack("<IQQ", 3, len(plan), len(kv)) + b"".join(_kv(*x) for x in kv)
    for n, shape, t, o, _ in plan:
        head += _s(n) + struct.pack("<I", len(shape)) + struct.pack(f"<{len(shape)}Q", *reversed(shape)) + \
            struct.pack("<IQ", t, o)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".part")
    with open(tmp, "wb") as h:
        h.write(head + b"\0" * (-len(head) % ALIGN))
        for n, shape, t, o, size in plan:
            f, info = ts[n]
            x = W.st_tensor(f, info)
            b = x.astype(np.float16 if t == W.GGUF_F16 else np.float32).tobytes()
            assert len(b) == size, n
            h.write(b + b"\0" * (-size % ALIGN))
    tmp.replace(out)
    rep = {"tensors": len(plan), "vocab": len(tokens), "merges": len(merges), "special": {k: v for k, v in sp.items()
           if k != "chat_template"}, "bytes": out.stat().st_size}
    log(f"  GGUF F16 written: {out} ({rep['tensors']} tensors, vocab {rep['vocab']}, {rep['bytes'] / 2**30:.2f} GiB)")
    return rep


def check(src: Path, gguf: Path, log=print) -> dict:
    """Every checkpoint tensor equals the GGUF tensor (bf16 -> f16 for 2-D, f32 for 1-D); shapes match."""
    _, g = W.read_gguf(gguf)
    ts = _tensors(Path(src))
    rep = {"tensors": 0, "unequal": [], "missing": sorted(set(ts) - set(g)), "extra": sorted(set(g) - set(ts))}
    for n, (f, info) in ts.items():
        if n not in g:
            continue
        ref = W.st_tensor(f, info)
        want = ref.astype(np.float16).astype(np.float32) if g[n][1] == W.GGUF_F16 else ref
        got = W.gguf_tensor(gguf, g[n])
        if tuple(ref.shape) != g[n][0] or not np.array_equal(got, want):
            rep["unequal"].append(n)
        rep["tensors"] += 1
    rep["ok"] = rep["tensors"] > 0 and not rep["unequal"] and not rep["missing"] and not rep["extra"]
    log(f"  GGUF check: {rep['tensors']} tensors, unequal {len(rep['unequal'])}, missing {len(rep['missing'])}, "
        f"extra {len(rep['extra'])}, ok {rep['ok']}")
    return rep
