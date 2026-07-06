"""S3 training loop — CAD supervised + supervised-contrastive + IRM, split by topic.

Real run (GPU):
    python -m peinn_v2.train.train --backbone hf --model-name microsoft/deberta-v3-base \
        --epochs 8 --batch-pairs 16 --freeze-bottom 6 --out peinn_v2/encoder/ckpt.pt

CPU smoke (no transformers/download; validates the whole pipeline runs + learns):
    python -m peinn_v2.train.train --smoke
"""
from __future__ import annotations
import argparse

from peinn_v2.train import data as D
from peinn_v2.train.losses import total_loss


def auc(scores, labels):
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return float("nan")
    r = 0
    for p in pos:
        for n in neg:
            r += (p > n) + 0.5 * (p == n)
    return r / (len(pos) * len(neg))


def evaluate(model, tok, dev, device):
    import torch
    model.eval()
    probs = {a: [] for a in D.AXES}; labs = {a: [] for a in D.AXES}
    with torch.no_grad():
        for items in D.batches(dev, batch_size=32, shuffle=False):
            texts, labels, _ = D.to_tensors(items)
            ids, mask = tok(texts)
            p = model(ids.to(device), mask.to(device))["axis_probs"].cpu()
            for i, a in enumerate(D.AXES):
                probs[a] += p[:, i].tolist(); labs[a] += labels[:, i].tolist()
    return {a: auc(probs[a], labs[a]) for a in D.AXES}


def build(args):
    from peinn_v2.encoder.model import StructuredThreatEncoder, TinyBackbone, HFMeanPoolBackbone
    if args.backbone == "tiny":
        bb = TinyBackbone(vocab=512, hidden=32)
        tok = D.HashTokenizer(vocab=512, max_len=32)
    else:
        bb = HFMeanPoolBackbone(args.model_name)
        if args.freeze_bottom:
            bb.freeze_bottom_layers(args.freeze_bottom)
        tok = D.HFTokenizer(args.model_name, max_len=args.max_len)
    # D9 compositional: energy = gated AND-combiner over C∧A∧R (primary_axis=None), not one head.
    # --primary-axis N overrides (e.g. 0 ⇒ holistic harm-head energy, the legacy scheme).
    pa = args.primary_axis if args.primary_axis >= 0 else None
    return StructuredThreatEncoder(bb, axes=D.AXES, primary_axis=pa), tok


def run(args):
    import torch
    device = "cuda" if torch.cuda.is_available() and not args.cpu else "cpu"
    records = D.load(args.corpus) if args.corpus else D.load()
    train, devs, dev_topics = D.make_splits(records, dev_topic_frac=args.dev_frac, seed=args.seed)
    n_dom = len({r.get("domain", "") for r in records})
    print(f"[data] {len(records)} items · train {len(train)} · dev(topic-held-out) "
          f"{len(devs['topic'])} ({len(dev_topics)} topics held out) · env-key={args.env_key} "
          f"({n_dom} domains)")

    model, tok = build(args)
    model.to(device)
    rates = {k: sum(int(r.get(k, 0)) for r in train) / max(len(train), 1) for k in D.LABEL_KEYS}
    print("[label] axis positive-rate: " + " ".join(f"{k}{rates[k]:.2f}" for k in D.LABEL_KEYS)
          + ("   ⚠ an axis at 0.00 means that label is MISSING from the corpus"
             if min(rates.values()) == 0 else ""))
    pw = D.pos_weights(train).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.wd)

    step = 0
    for ep in range(args.epochs):
        model.train()
        # IRM warmup: ramp λ_irm from 0→target over warmup epochs (IRM is unstable cold)
        l_irm = args.lambda_irm * min(1.0, (ep + 1) / max(args.irm_warmup, 1))
        agg = {"bce": 0.0, "supcon": 0.0, "irm": 0.0, "total": 0.0}; nb = 0
        for items in D.batches(train, batch_size=args.batch_pairs, seed=args.seed + ep):
            texts, labels, envs = D.to_tensors(items, env_key=args.env_key)
            ids, mask = tok(texts)
            out = model(ids.to(device), mask.to(device))
            loss, parts = total_loss(out, labels.to(device), envs, pos_weight=pw,
                                     lambda_c=args.lambda_c, lambda_irm=l_irm, temp=args.temp)
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            for k in agg: agg[k] += parts[k]
            nb += 1; step += 1
        d = evaluate(model, tok, devs["topic"], device)
        print(f"[ep {ep+1}/{args.epochs}] loss {agg['total']/nb:.3f} "
              f"(bce {agg['bce']/nb:.3f} sc {agg['supcon']/nb:.3f} irm {agg['irm']/nb:.4f}, λirm {l_irm:.2f})"
              f"  dev-AUC(topic-held-out) " + " ".join(f"{a}{d[a]:.2f}" for a in D.AXES))

    if args.out:
        torch.save({"model": model.state_dict(), "axes": model.axes,
                    "primary_axis": model.primary_axis,
                    "backbone": args.backbone, "model_name": args.model_name}, args.out)
        print(f"[save] {args.out}")
    return model, tok, devs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backbone", choices=["tiny", "hf"], default="hf")
    ap.add_argument("--model-name", default="microsoft/deberta-v3-base")
    ap.add_argument("--corpus", default=None,
                    help="one path, or comma-separated paths to merge (each tagged as a domain, D13)")
    ap.add_argument("--env-key", choices=["topic", "domain"], default="topic",
                    help="IRM/invariance environment key (D13): 'domain' enforces cross-domain "
                         "invariance — the corpus→benchmark shift that topic-IRM could not see")
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--batch-pairs", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--wd", type=float, default=0.01)
    ap.add_argument("--lambda-c", type=float, default=0.5)
    ap.add_argument("--lambda-irm", type=float, default=1.0)
    ap.add_argument("--irm-warmup", type=int, default=2)
    ap.add_argument("--temp", type=float, default=0.1)
    ap.add_argument("--max-len", type=int, default=64)
    ap.add_argument("--freeze-bottom", type=int, default=6)
    ap.add_argument("--primary-axis", type=int, default=-1,
                    help="energy axis index; -1 (default) = gated C∧A∧R combiner (D9)")
    ap.add_argument("--dev-frac", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--smoke", action="store_true", help="tiny CPU pipeline check (no download)")
    args = ap.parse_args()
    if args.smoke:
        args.backbone = "tiny"; args.cpu = True
        args.epochs = max(args.epochs, 3); args.batch_pairs = 8; args.lr = 1e-2; args.irm_warmup = 1
        print("[smoke] TinyBackbone + HashTokenizer, CPU — validating the pipeline")
        _, _, _ = run(args)
        print("SMOKE TRAIN PASSED")
    else:
        run(args)


if __name__ == "__main__":
    main()
