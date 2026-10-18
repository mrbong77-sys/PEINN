"""DESIGN.md 10 (A8): LoRA on the protected model with the same supervision, merged into the weights.

    python a8_train.py --data DIR/targets.jsonl --out DIR/merged --report DIR/train.json --model Qwen/Qwen2.5-7B-Instruct

targets.jsonl rows: {"sha", "split" (train | val), "cls", "text", "target"}. The loss is on the answer tokens only; the
prompt is the bare request in the model's own chat template (as the Vanilla arm sends it). LoRA (rank 16, alpha 32,
dropout 0.05) on every attention and MLP projection, AdamW 1e-4, one epoch, batch 4 x 4 accumulation, cosine with 3%
warm-up, max 1,024 tokens, seed 42. The adapters are merged into the base weights and the merged model is saved
(safetensors) for Ollama; the adapters alone go to adapter.safetensors. Hand-written LoRA (no peft dependency).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import time
from pathlib import Path

import torch
from torch import nn

SEED = 42
HP = dict(r=16, alpha=32, dropout=0.05, lr=1e-4, epochs=1, batch=4, accum=4, warmup=0.03, max_len=1024)
CUT = 512   # a8.GEN_OPTS num_predict: a target of this many tokens was cut by the cap and has no end of its own
TARGETS = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")


class LoRALinear(nn.Module):
    """y = W x + (alpha / r) B A dropout(x); A, B in float32, W frozen."""

    def __init__(self, base: nn.Linear, r: int, alpha: float, dropout: float):
        super().__init__()
        self.base = base
        self.scale = alpha / r
        dev = base.weight.device
        self.A = nn.Parameter(torch.empty(r, base.in_features, device=dev, dtype=torch.float32))
        self.B = nn.Parameter(torch.zeros(base.out_features, r, device=dev, dtype=torch.float32))
        nn.init.kaiming_uniform_(self.A, a=math.sqrt(5))
        self.drop = nn.Dropout(dropout)

    def forward(self, x):
        y = self.base(x)
        z = (self.drop(x).to(torch.float32) @ self.A.t()) @ self.B.t()
        return y + (z * self.scale).to(y.dtype)

    def merged(self) -> nn.Linear:
        with torch.no_grad():
            w = self.base.weight
            w += (self.B @ self.A * self.scale).to(w.dtype)
        return self.base


def wrap(model: nn.Module, r: int, alpha: float, dropout: float) -> list[str]:
    """Replace every target projection with a LoRA layer; freeze everything else. Returns the wrapped names."""
    for p in model.parameters():
        p.requires_grad_(False)
    names = [n for n, m in model.named_modules() if isinstance(m, nn.Linear) and n.split(".")[-1] in TARGETS]
    for n in names:
        parent, leaf = model.get_submodule(n.rsplit(".", 1)[0]) if "." in n else model, n.split(".")[-1]
        setattr(parent, leaf, LoRALinear(getattr(parent, leaf), r, alpha, dropout))
    return names


def merge(model: nn.Module, names: list[str]) -> dict:
    """Fold every adapter into its base weight; return the adapters (for adapter.safetensors)."""
    ad = {}
    for n in names:
        parent, leaf = model.get_submodule(n.rsplit(".", 1)[0]) if "." in n else model, n.split(".")[-1]
        m = getattr(parent, leaf)
        ad[f"{n}.lora_A"], ad[f"{n}.lora_B"] = m.A.detach().cpu().contiguous(), m.B.detach().cpu().contiguous()
        setattr(parent, leaf, m.merged())
    return ad


def suffix_len(tok) -> int:
    """Tokens the chat template puts after the answer (Qwen: <|im_end|> and a newline)."""
    msgs = [{"role": "user", "content": "q"}]
    p = _ids(tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True))
    full = _ids(tok.apply_chat_template(msgs + [{"role": "assistant", "content": "x"}], tokenize=True))
    return len(full) - len(p) - len(tok.encode("x", add_special_tokens=False))


def _ids(x) -> list[int]:
    return list(x["input_ids"] if isinstance(x, dict) or hasattr(x, "keys") else x)


def encode(tok, text: str, target: str, max_len: int, cut: bool = False, tail: int = 0) -> tuple[list[int], list[int]]:
    """Token ids of prompt + answer in the chat template; labels -100 on the prompt (and nothing past max_len).
    cut (DESIGN.md 10.7): the answer was stopped by the generation cap, so the template's end-of-turn tokens after it
    (`tail` of them) carry no loss: the model learns the answer text, not to stop mid-sentence."""
    msgs = [{"role": "user", "content": text}]
    p = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True)
    full = tok.apply_chat_template(msgs + [{"role": "assistant", "content": target}], tokenize=True)
    p = list(p["input_ids"] if isinstance(p, dict) or hasattr(p, "keys") else p)
    full = list(full["input_ids"] if isinstance(full, dict) or hasattr(full, "keys") else full)
    if full[:len(p)] != p:                                      # the template must extend the prompt
        raise ValueError("chat template: the answer does not extend the prompt tokens")
    labels = [-100] * len(p) + full[len(p):]
    if cut and tail:
        labels[-tail:] = [-100] * tail
    return full[:max_len], labels[:max_len]


def batches(rows: list, size: int, pad: int):
    for i in range(0, len(rows), size):
        b = rows[i:i + size]
        n = max(len(x[0]) for x in b)
        ids = torch.tensor([x[0] + [pad] * (n - len(x[0])) for x in b])
        lab = torch.tensor([x[1] + [-100] * (n - len(x[1])) for x in b])
        att = torch.tensor([[1] * len(x[0]) + [0] * (n - len(x[0])) for x in b])
        yield ids, lab, att


def mean_loss(model, rows: list, size: int, pad: int, dev) -> float | None:
    if not rows:
        return None
    model.eval()
    tot, n = 0.0, 0
    with torch.no_grad():
        for ids, lab, att in batches(rows, size, pad):
            out = model(input_ids=ids.to(dev), attention_mask=att.to(dev), labels=lab.to(dev))
            k = int((lab[:, 1:] != -100).sum())
            tot, n = tot + float(out.loss) * k, n + k
    model.train()
    return tot / max(n, 1)


def seed_all(s: int = SEED) -> None:
    random.seed(s)
    torch.manual_seed(s)
    torch.cuda.manual_seed_all(s)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def train(model, tok, data: list[dict], hp: dict, dev, log=print) -> dict:
    seed_all()
    tail = suffix_len(tok)
    if not 0 < tail <= 8:
        raise ValueError(f"chat template: {tail} tokens after the answer (expected a short end-of-turn)")
    cut = lambda d: (d.get("tokens") or 0) >= CUT                     # noqa: E731
    tr = [encode(tok, d["text"], d["target"], hp["max_len"], cut(d), tail) for d in data if d["split"] == "train"]
    va = [encode(tok, d["text"], d["target"], hp["max_len"], cut(d), tail) for d in data if d["split"] == "val"]
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    names = wrap(model, hp["r"], hp["alpha"], hp["dropout"])
    params = [p for p in model.parameters() if p.requires_grad]
    rep = {"hp": hp, "wrapped": len(names), "trainable": sum(p.numel() for p in params),
           "n": {"train": len(tr), "val": len(va)}, "cut_no_end_loss": sum(map(cut, data)), "template_tail": tail,
           "val_loss_before": mean_loss(model, va, hp["batch"], pad, dev)}
    opt = torch.optim.AdamW(params, lr=hp["lr"], weight_decay=0.0)
    steps = math.ceil(len(tr) / hp["batch"] / hp["accum"]) * hp["epochs"]
    warm = max(1, int(round(steps * hp["warmup"])))
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: (s + 1) / warm if s < warm else 0.5 * (1 + math.cos(math.pi * (s - warm) / max(1, steps - warm))))
    model.train()
    curve, t0, k = [], time.time(), 0
    for ep in range(hp["epochs"]):
        order = list(range(len(tr)))
        random.Random(SEED + ep).shuffle(order)
        rows = [tr[i] for i in order]
        run = 0.0
        for i, (ids, lab, att) in enumerate(batches(rows, hp["batch"], pad)):
            out = model(input_ids=ids.to(dev), attention_mask=att.to(dev), labels=lab.to(dev))
            (out.loss / hp["accum"]).backward()
            run += float(out.loss.detach()) / hp["accum"]
            if (i + 1) % hp["accum"] == 0 or (i + 1) * hp["batch"] >= len(rows):
                torch.nn.utils.clip_grad_norm_(params, 1.0)
                opt.step()
                sched.step()
                opt.zero_grad(set_to_none=True)
                k += 1
                curve.append(round(run, 4))
                run = 0.0
                if k % 20 == 0 or k == steps:
                    log(f"step {k}/{steps} loss {curve[-1]} ({time.time() - t0:.0f} s)")
    rep.update(steps=k, loss_curve=curve, train_sec=round(time.time() - t0, 1),
               val_loss_after=mean_loss(model, va, hp["batch"], pad, dev))
    rep["adapters"] = merge(model, names)
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--hp", default="{}", help="JSON overrides of HP (the check run)")
    a = ap.parse_args(argv)
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    from huggingface_hub import snapshot_download
    from safetensors.torch import save_file
    from transformers import AutoModelForCausalLM, AutoTokenizer
    hp = dict(HP, **json.loads(a.hp))
    src = snapshot_download(a.model, allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "merges.txt"])
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(src)
    model = AutoModelForCausalLM.from_pretrained(src, torch_dtype=torch.bfloat16).to(dev)
    model.config.use_cache = False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    data = [json.loads(x) for x in a.data.read_text(encoding="utf-8").split("\n") if x.strip()]
    rep = train(model, tok, data, hp, dev)
    ad = rep.pop("adapters")
    a.out.mkdir(parents=True, exist_ok=True)
    model.config.use_cache = True
    model.save_pretrained(a.out, safe_serialization=True)
    tok.save_pretrained(a.out)
    save_file(ad, str(a.out.parent / "adapter.safetensors"))
    rep.update(model=a.model, snapshot=Path(src).name, device=str(dev),
               counts={c: sum(1 for d in data if d["cls"] == c and d["split"] == "train") for c in ("harm", "dilemma", "safe")})
    a.report.write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: rep[k] for k in ("n", "steps", "val_loss_before", "val_loss_after", "train_sec")}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
