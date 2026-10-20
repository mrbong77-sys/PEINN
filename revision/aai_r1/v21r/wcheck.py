"""Weights check for H02: the F16 GGUF Ollama serves against the canonical bf16 safetensors.

Reads both formats directly (no torch, no gguf package): every tensor of the checkpoint must be in the GGUF with the
same shape, and its values must equal the bf16 weights cast to float16 (llama.cpp's converter permutes attn_q and
attn_k rows for the llama layout; the same permutation is applied before comparing).
"""
from __future__ import annotations

import json
import re
import struct
from pathlib import Path

import numpy as np

GGUF_F32, GGUF_F16, GGUF_BF16 = 0, 1, 30
_SCALAR = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}


def _str(h) -> str:
    (n,) = struct.unpack("<Q", h.read(8))
    return h.read(n).decode("utf-8", errors="replace")


def _val(h, t: int):
    if t == 8:
        return _str(h)
    if t == 9:
        (et,) = struct.unpack("<I", h.read(4))
        (n,) = struct.unpack("<Q", h.read(8))
        return [_val(h, et) for _ in range(n)]
    fmt = _SCALAR[t]
    return struct.unpack(fmt, h.read(struct.calcsize(fmt)))[0]


def read_gguf(path: Path) -> tuple[dict, dict]:
    """(metadata, {name: (numpy shape, ggml type, absolute offset)}) of a GGUF v2/v3 file."""
    with open(path, "rb") as h:
        if h.read(4) != b"GGUF":
            raise ValueError(f"{path} is not a GGUF file")
        version, n_t, n_kv = struct.unpack("<IQQ", h.read(20))
        meta = {}
        for _ in range(n_kv):
            k = _str(h)
            (t,) = struct.unpack("<I", h.read(4))
            v = _val(h, t)
            if not isinstance(v, list) or len(v) < 64:                 # skip the vocabulary arrays
                meta[k] = v
        infos = {}
        for _ in range(n_t):
            name = _str(h)
            (nd,) = struct.unpack("<I", h.read(4))
            dims = struct.unpack(f"<{nd}Q", h.read(8 * nd))
            t, off = struct.unpack("<IQ", h.read(12))
            infos[name] = (tuple(reversed(dims)), t, off)
        align = int(meta.get("general.alignment", 32))
        start = -(-h.tell() // align) * align
    meta["_version"] = version
    return meta, {k: (s, t, start + o) for k, (s, t, o) in infos.items()}


def gguf_tensor(path: Path, info) -> np.ndarray:
    shape, t, off = info
    dt = {GGUF_F32: np.float32, GGUF_F16: np.float16, GGUF_BF16: np.uint16}[t]
    a = np.memmap(path, dtype=dt, mode="r", offset=off, shape=shape)
    return _bf16(a) if t == GGUF_BF16 else np.asarray(a, dtype=np.float32)


def _bf16(u16: np.ndarray) -> np.ndarray:
    return (np.asarray(u16, dtype=np.uint32) << 16).view(np.float32)


def read_safetensors(path: Path) -> dict:
    """{name: (dtype, shape, absolute offset, nbytes)} of one safetensors file."""
    with open(path, "rb") as h:
        (n,) = struct.unpack("<Q", h.read(8))
        head = json.loads(h.read(n))
    return {k: (v["dtype"], tuple(v["shape"]), 8 + n + v["data_offsets"][0], v["data_offsets"][1] - v["data_offsets"][0])
            for k, v in head.items() if k != "__metadata__"}


def st_tensor(path: Path, info) -> np.ndarray:
    dtype, shape, off, _ = info
    dt = {"BF16": np.uint16, "F16": np.float16, "F32": np.float32}[dtype]
    a = np.memmap(path, dtype=dt, mode="r", offset=off, shape=shape)
    return _bf16(a) if dtype == "BF16" else np.asarray(a, dtype=np.float32)


_MAP = [(r"model\.embed_tokens\.weight", "token_embd.weight"), (r"model\.norm\.weight", "output_norm.weight"),
        (r"lm_head\.weight", "output.weight")]
_LAYER = {"self_attn.q_proj": "attn_q", "self_attn.k_proj": "attn_k", "self_attn.v_proj": "attn_v",
          "self_attn.o_proj": "attn_output", "mlp.gate_proj": "ffn_gate", "mlp.up_proj": "ffn_up",
          "mlp.down_proj": "ffn_down", "input_layernorm": "attn_norm", "post_attention_layernorm": "ffn_norm"}


def gguf_name(hf: str) -> str | None:
    for pat, g in _MAP:
        if re.fullmatch(pat, hf):
            return g
    m = re.fullmatch(r"model\.layers\.(\d+)\.(.+)\.weight", hf)
    if m and m.group(2) in _LAYER:
        return f"blk.{m.group(1)}.{_LAYER[m.group(2)]}.weight"
    return None


def permute(w: np.ndarray, n_head: int) -> np.ndarray:
    """Llama.cpp convert_hf_to_gguf LlamaModel.permute (rotary halves interleaved)."""
    return w.reshape(n_head, 2, w.shape[0] // n_head // 2, *w.shape[1:]).swapaxes(1, 2).reshape(w.shape)


def compare(st_dir: Path, gguf: Path, log=print) -> dict:
    """Every checkpoint tensor against the GGUF: shape, and values equal to the bf16 weights cast to float16."""
    cfg = json.loads((Path(st_dir) / "config.json").read_text(encoding="utf-8"))
    nh, nkv = cfg["num_attention_heads"], cfg.get("num_key_value_heads", cfg["num_attention_heads"])
    meta, g = read_gguf(gguf)
    rep = {"gguf_file_type": meta.get("general.file_type"), "gguf_version": meta["_version"], "tensors": 0,
           "elements": 0, "unequal_elements": 0, "max_abs_diff": 0.0, "missing": [], "shape_mismatch": [],
           "unequal_tensors": [], "gguf_types": {}}
    seen = set()
    for f in sorted(Path(st_dir).glob("*.safetensors")):
        for name, info in read_safetensors(f).items():
            gn = gguf_name(name)
            if gn is None or gn not in g:
                rep["missing"].append(name)
                continue
            seen.add(gn)
            ref = st_tensor(f, info)
            if gn.endswith("attn_q.weight"):
                ref = permute(ref, nh)
            elif gn.endswith("attn_k.weight"):
                ref = permute(ref, nkv)
            if tuple(ref.shape) != g[gn][0]:
                rep["shape_mismatch"].append([name, list(ref.shape), list(g[gn][0])])
                continue
            got = gguf_tensor(gguf, g[gn])
            want = ref if g[gn][1] == GGUF_F32 else ref.astype(np.float16).astype(np.float32)
            neq = int(np.count_nonzero(got != want))
            rep["tensors"] += 1
            rep["elements"] += int(ref.size)
            rep["unequal_elements"] += neq
            rep["max_abs_diff"] = max(rep["max_abs_diff"], float(np.max(np.abs(got - ref))))
            rep["gguf_types"][str(g[gn][1])] = rep["gguf_types"].get(str(g[gn][1]), 0) + 1
            if neq:
                rep["unequal_tensors"].append([name, neq])
    rep["gguf_only"] = sorted(set(g) - seen)
    rep["ok"] = (rep["tensors"] > 0 and not rep["missing"] and not rep["shape_mismatch"] and not rep["unequal_tensors"]
                 and not rep["gguf_only"])
    log(f"  weights check: {rep['tensors']} tensors, {rep['elements']:,} values, unequal {rep['unequal_elements']}, "
        f"max |gguf - bf16| {rep['max_abs_diff']:.3g}, missing {len(rep['missing'])}, ok {rep['ok']}")
    return rep
