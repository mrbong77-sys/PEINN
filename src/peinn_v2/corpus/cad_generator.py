#!/usr/bin/env python3
"""CAD minimal-pair generator — LLM-free, benchmark-free.

Implements design/CAD_SCHEMA.md + design/CORPUS_DESIGN.md. For each benign /
sensitive-but-non-operational topic frame it renders minimal pairs that flip EXACTLY ONE
axis (actionability / realizability / definiteness), holding topic + the other two axes +
affect fixed across the pair. Orthogonality is guaranteed BY CONSTRUCTION and verified:

  • topic ⟂ label : every topic emits the identical multiset of axis labels (full grid),
                    so topic carries zero marginal information about any label.
  • affect ⟂ label: affect is a controlled factor — every cell is rendered at affect∈{0,1}.
  • marker diversity: each axis value is realised by MANY templates (rotated by a stable
                    hash), so the encoder must learn the *structure* (e.g. imperative mood),
                    not a single literal marker string.

No harmful-operational topics are generated (safety + the topic-invariance bet, CORPUS_DESIGN §0):
structure is taught on benign content; topic-invariance carries it to harmful topics at eval.

Run:  python -m peinn_v2.corpus.cad_generator         # writes data/pilot.jsonl + prints report
"""
from __future__ import annotations
import json, hashlib
from pathlib import Path

OUT = Path(__file__).parent / "data" / "cad_corpus.jsonl"
VARIANTS = 2   # marker-variant draws per cell (multiplies size, diversifies surface)

# ── Topic frames (benign + sensitive-but-non-operational; NONE drawn from any benchmark) ──
# (id, domain, obj, verb, ving, vpast, concrete steps, tool|None, time, place, sens)
TOPICS = [
    ("kitchen.sourdough","cooking","a sourdough loaf","bake","baking","baked","mix 500 g flour, 350 g water, 100 g starter, 10 g salt; fold every 30 min ×4; proof 4 h at 24 °C; bake 20 min at 245 °C","a Dutch oven","tomorrow at 7 a.m.","in my kitchen",False),
    ("furniture.bookshelf","assembly","a flat-pack bookshelf","assemble","assembling","assembled","attach the side panels with the 8 cam locks, slot the 3 shelves, screw the back board","a screwdriver","this afternoon","in the study",False),
    ("garden.tomato","gardening","tomato seedlings","transplant","transplanting","transplanted","harden off 7 days, dig 30 cm holes 60 cm apart, bury to the first leaves, water deeply","a hand trowel","this weekend","in the back garden",False),
    ("software.csvparser","software","a CSV parser","write","writing","written","read line by line, split on commas outside quotes, map each row to a dict by header","Python 3","tonight","at my desk",False),
    ("home.wifi","home networking","a home Wi-Fi router","secure","securing","secured","change the admin password, enable WPA3, disable WPS, set a 20-char passphrase, update firmware",None,"this evening","at home",True),
    ("fitness.squat","fitness","a barbell back squat","perform","performing","performed","brace the core, descend below parallel, drive through mid-foot, keep the bar over mid-foot","a squat rack","at 6 p.m.","at the gym",False),
    ("music.guitar","music","a barre chord","play","playing","played","press the index across all 6 strings at fret 5, stack the A-shape, arch the fingers","a guitar","after dinner","in the living room",False),
    ("travel.kyoto","travel","a three-day Kyoto itinerary","plan","planning","planned","day 1 Higashiyama, day 2 Arashiyama bamboo grove, day 3 Fushimi Inari at dawn",None,"next month","from home",False),
    ("finance.budget","personal finance","a monthly budget","build","building","built","list net income, fix 50% needs, 30% wants, 20% savings, automate transfers on payday","a spreadsheet","on the 1st","at my desk",False),
    ("cleaning.castiron","home care","a cast-iron skillet","season","seasoning","seasoned","scrub, dry on low heat, rub a thin oil layer, bake upside down at 230 °C for 1 h","flaxseed oil","tonight","in the oven",False),
    ("photo.longexposure","photography","a long-exposure night shot","capture","capturing","captured","tripod, ISO 100, f/8, 30 s shutter, 2 s timer to avoid shake","a tripod","at midnight","by the river",False),
    ("lang.spanish","languages","conversational Spanish","learn","learning","learned","drill the 100 commonest verbs, shadow native audio, do 20 min spaced repetition","an SRS app","every morning","on the commute",False),
    ("car.oilchange","car maintenance","an engine oil change","do","doing","done","warm the engine, drain the oil, replace the filter, refill 4.5 L of 5W-30, check the level","a socket wrench","Saturday","in the driveway",False),
    ("firstaid.burn","first aid","a minor kitchen burn","treat","treating","treated","cool under running water 20 min, do not pop blisters, cover with a sterile dressing",None,"right now","at home",True),
    ("chem.volcano","science education","a baking-soda volcano","make","making","made","mix 2 tbsp baking soda with dish soap and colouring, pour in 60 ml vinegar",None,"for the school fair","in the classroom",True),
    ("firearm.storage","home safety","a hunting rifle at home","store","storing","stored","unload it, fit a trigger lock, keep it in a bolted steel safe, store ammunition separately","a gun safe","today","in the basement",True),
    ("meds.adherence","health","a daily medication schedule","manage","managing","managed","use a weekly organiser, set alarms, refill 5 days early, log each dose","a pill organiser","each evening","at home",True),
    ("diy.shelfanchor","DIY","a heavy shelf into drywall","anchor","anchoring","anchored","find the studs, mark level, drill pilot holes, use rated toggle bolts","a stud finder","this weekend","in the hallway",False),
    ("bake.macarons","cooking","French macarons","make","making","made","age whites 24 h, sift almond flour and sugar, macaronage to ribbon, rest 30 min, bake 14 min at 150 °C","a piping bag","Sunday","in the kitchen",False),
    ("software.backup","software","an automated file backup","set up","setting up","set up","script an nightly rsync of the home folder, keep 7 daily and 4 weekly snapshots","cron","tonight","on my laptop",False),
    ("garden.compost","gardening","a compost bin","start","starting","started","layer browns and greens 3:1, keep it moist, turn weekly, expect compost in 3 months",None,"this week","behind the shed",False),
    ("home.lockrekey","home security","a door lock","rekey","rekeying","rekeyed","remove the cylinder, swap the pins to the new bitting with a rekey kit, reassemble, test","a rekey kit","this afternoon","at the front door",True),
    ("art.watercolor","art","a watercolour landscape","paint","painting","painted","wet the sky, drop graded washes, dry, then layer the foreground wet-on-dry","a round brush","this evening","in the studio",False),
    ("fitness.run5k","fitness","a couch-to-5k plan","follow","following","followed","alternate 1 min run / 90 s walk week 1, add 30 s weekly, run 3 days with rest",None,"from Monday","at the park",False),
    ("software.regex","software","an email-validation regex","write","writing","written","match the local part, an @, a dotted domain, anchor both ends, test edge cases","a regex tester","now","at my desk",False),
    ("cooking.knife","cooking","basic knife skills","practise","practising","practised","pinch grip, curl the guiding hand, rock the blade, keep the tip down","a chef's knife","this week","in the kitchen",False),
    ("home.smokealarm","home safety","a smoke alarm","install","installing","installed","mount on the ceiling 30 cm from walls, test the button, log the date",None,"today","in the hallway",True),
    ("garden.rainbarrel","gardening","a rain barrel","install","installing","installed","cut the downspout, fit a diverter, raise the barrel on blocks, add a spigot and overflow","a hacksaw","this weekend","by the gutter",False),
    ("music.mix","music","a two-track mix","mix","mixing","mixed","gain-stage to -18 dBFS, high-pass the bus, balance levels, add gentle bus compression","a DAW","tonight","in the home studio",False),
    ("finance.taxes","personal finance","a personal tax return","file","filing","filed","gather income forms, claim the standard deduction, enter figures, double-check, e-file","tax software","before April","at home",False),
    # ── sensitive-but-benign (break the "scary word → block" shortcut) + more domains ──
    ("security.firewall","cybersecurity","a host firewall","configure","configuring","configured","set default-deny inbound, allow established, open only ports 22 and 443, enable logging","ufw","this evening","on my server",True),
    ("security.vpn","cybersecurity","a personal VPN","set up","setting up","set up","generate the keypair, configure WireGuard, set the endpoint, route traffic, test the handshake","WireGuard","tonight","at home",True),
    ("security.passwords","cybersecurity","a password manager","adopt","adopting","adopted","install it, generate 20-char uniques per site, enable 2FA, save an emergency kit","a password manager","this week","at my desk",True),
    ("security.patch","cybersecurity","a home server","patch","patching","patched","snapshot first, run the package updates, reboot into the new kernel, verify the services","apt","Sunday","in the office",True),
    ("safety.cpr","first aid","hands-only CPR","perform","performing","performed","call emergency services, push hard and fast centre-chest 100-120/min, continue until help arrives",None,"in an emergency","anywhere",True),
    ("safety.choking","first aid","a choking adult","help","helping","helped","ask if they can cough, give 5 back blows, then 5 abdominal thrusts, repeat",None,"in an emergency","anywhere",True),
    ("safety.extinguisher","fire safety","a fire extinguisher","use","using","used","pull the pin, aim at the base, squeeze the handle, sweep side to side","an extinguisher","if a fire starts","at home",True),
    ("safety.chemicals","home safety","household cleaners","store","storing","stored","keep originals labelled, never mix bleach and ammonia, store high and locked, ventilate",None,"today","in the utility room",True),
    ("safety.batteries","recycling","old lithium batteries","dispose of","disposing of","disposed of","tape the terminals, keep them in a non-metal box, drop at a recycling point",None,"this week","at the depot",True),
    ("chem.electrolysis","science education","water electrolysis","demonstrate","demonstrating","demonstrated","fill with salt water, insert two graphite electrodes, connect a 9 V battery, watch the gases","a 9 V battery","in class","at school",True),
    ("chem.crystals","science education","sugar crystals","grow","growing","grown","make a saturated syrup, suspend a seeded string, leave a week undisturbed",None,"over a week","on the windowsill",False),
    ("health.bloodsugar","health","blood sugar","manage","managing","managed","test before meals, count carbs, walk after eating, log readings, follow the care plan","a glucometer","each day","at home",True),
    ("health.nutrition","health","a nutrition label","read","reading","read","check the serving size, then calories, then sodium and added sugar per serving",None,"while shopping","at the store",False),
    ("home.paint","home care","a bedroom","paint","painting","painted","tape the edges, prime, cut in, roll two coats, remove the tape while wet","a roller","this weekend","upstairs",False),
    ("home.unclog","home care","a sink drain","unclog","unclogging","unclogged","bail the water, plunge, then snake the trap, flush with hot water","a drain snake","tonight","in the bathroom",False),
    ("diy.solder","electronics","a through-hole joint","solder","soldering","soldered","heat the pad and lead together, feed solder, remove, inspect for a shiny cone","a soldering iron","this evening","at the bench",False),
    ("garden.prune","gardening","a fruit tree","prune","pruning","pruned","remove dead wood, open the centre, cut just above outward buds in late winter","pruning shears","in February","in the orchard",False),
    ("cooking.ferment","cooking","sauerkraut","ferment","fermenting","fermented","shred the cabbage, salt at 2%, pack under the brine, ferment 2 weeks at 18 °C","a crock","over two weeks","in the pantry",False),
    ("travel.visa","travel","a tourist visa","apply for","applying for","applied for","check the requirements, fill the form, book the appointment, bring proof of funds",None,"next week","at the consulate",False),
    ("finance.invest","personal finance","index investing","start","starting","started","open a brokerage, pick a broad index fund, automate monthly buys, ignore the noise",None,"this month","online",False),
    ("software.api","software","a REST API call","make","making","made","read the docs, get an API key, send an authenticated GET, parse the JSON","curl","now","at my desk",False),
    ("software.git","software","a deleted git branch","recover","recovering","recovered","find the commit in the reflog, create a branch at that hash, verify the tree","git","now","at my desk",False),
    ("art.pottery","art","a clay bowl","throw","throwing","thrown","centre the clay, open the floor, pull the walls, trim when leather-hard","a wheel","this weekend","in the studio",False),
]

# ── marker pools: many realisations per axis value, so no single string == the label ──
MARK = {
    ("act", 1): ["Tell me how to {v} {o}.", "How do I {v} {o}?", "Walk me through {ving} {o}.",
                 "I need to know how to {v} {o}.", "Explain how to {v} {o}, please."],
    ("act", 0): ["How does {ving} {o} usually work?", "What happens when you {v} {o}?",
                 "Why does {ving} {o} work the way it does?", "What is involved in {ving} {o}?",
                 "How is {o} typically {vpast}?"],
    ("real", 1): ["Give me the exact steps, amounts, and tools to {v} {o}: {steps}.",
                  "List the full procedure to {v} {o}, step by step: {steps}.",
                  "Walk me through {ving} {o} precisely: {steps}.",
                  "I want the complete method to {v} {o}: {steps}."],
    ("real", 0): ["Give me a rough, general idea of how to {v} {o} somehow.",
                  "Just vaguely, how would one {v} {o}?",
                  "In broad strokes, how do you {v} {o} — no details?",
                  "Roughly point me toward {ving} {o}."],
    ("def", 1): ["I will {v} {o} {time} {place}{using}.",
                 "I'm going to {v} {o} {time} {place}{using}.",
                 "My plan is set: I {v} {o} {time} {place}{using}.",
                 "{time_c} {place}, I will {v} {o}{using}."],
    ("def", 0): ["Maybe I could {v} {o} sometime, if things work out.",
                 "I might possibly {v} {o} at some point, perhaps.",
                 "Someone could maybe {v} {o} eventually.",
                 "Perhaps {ving} {o} could happen someday, if ever."],
}
AFFECT = {0: [""],
          1: ["Honestly I'm pretty stressed about it, but ", "I'm so excited about this — ",
              "I'm a little anxious, yet ", "I'm thrilled to finally do it: "]}


def _pick(pool, *keys):
    h = int(hashlib.md5("|".join(map(str, keys)).encode()).hexdigest(), 16)
    return h % len(pool), pool[h % len(pool)]


def _cap(s): return s[:1].upper() + s[1:] if s else s


def render(topic, axis, value, affect, k):
    tid, dom, obj, verb, ving, vpast, steps, tool, time, place, sens = topic
    using = f" using {tool}" if tool else ""
    slots = dict(v=verb, o=obj, ving=ving, vpast=vpast, steps=steps, tool=tool or "",
                 time=time, place=place, using=using, time_c=_cap(time))
    ti, tmpl = _pick(MARK[(axis, value)], tid, axis, value, affect, k)
    core = tmpl.format(**slots)
    ai, pre = _pick(AFFECT[affect], tid, axis, value, k)
    if pre and not pre.rstrip().endswith((":", "—")):
        core = core[:1].lower() + core[1:]          # mid-sentence after "..., but "
    text = _cap(pre + core)
    act, real, def_ = ({"act": (value, 0, 0), "real": (1, value, 0), "def": (0, 0, value)})[axis]
    return text, act, real, def_, f"{axis}{value}.{ti}"


def generate():
    records, pid = [], 0
    for topic in TOPICS:
        tid, dom = topic[0], topic[1]
        for axis in ("act", "real", "def"):
            for affect in (0, 1):
                for k in range(VARIANTS):
                    pid += 1
                    pair_id = f"p{pid:05d}"
                    for value in (1, 0):
                        text, a, r, d, tmpl = render(topic, axis, value, affect, k)
                        records.append({
                            "id": f"{pair_id}_{'hi' if value else 'lo'}",
                            "text": text, "topic_id": tid, "domain": dom,
                            "act": a, "real": r, "def": d, "affect": affect,
                            "pair_id": pair_id, "toggled_axis": axis, "tmpl": tmpl,
                            "source": "template",
                        })
    return records


def _corr(xs, ys):
    n = len(xs); mx = sum(xs)/n; my = sum(ys)/n
    cov = sum((x-mx)*(y-my) for x, y in zip(xs, ys))
    vx = sum((x-mx)**2 for x in xs) ** 0.5; vy = sum((y-my)**2 for y in ys) ** 0.5
    return 0.0 if vx == 0 or vy == 0 else cov/(vx*vy)


def verify(records):
    print("══ CAD CORPUS — verification ══════════════════════════════════════════════")
    n = len(records); topics = sorted({r["topic_id"] for r in records})
    domains = sorted({r["domain"] for r in records})
    sens_t = sum(1 for t in TOPICS if t[-1])
    print(f"   {n} items · {len(topics)} topics ({sens_t} sensitive-benign) · {len(domains)} domains "
          f"· {n//2} minimal pairs · {VARIANTS} marker-variants/cell")

    pairs = {}
    for r in records:
        pairs.setdefault(r["pair_id"], []).append(r)
    bad = sum(1 for x, y in pairs.values()
              if [ax for ax in ("act","real","def") if x[ax] != y[ax]] != [x["toggled_axis"]]
              or x["affect"] != y["affect"] or x["topic_id"] != y["topic_id"])
    print(f"\n   (1) minimal-pair integrity: {len(pairs)-bad}/{len(pairs)} flip exactly one axis  "
          f"→  {'OK' if bad==0 else f'{bad} BAD'}")

    sig = {}
    for r in records:
        sig.setdefault(r["topic_id"], []).append((r["act"], r["real"], r["def"], r["affect"]))
    ref = sorted(sig[topics[0]])
    same = all(sorted(v) == ref for v in sig.values())
    print(f"   (2) topic ⟂ label: all {len(topics)} topics share an identical label multiset  "
          f"→  {'OK (corr = 0 by construction)' if same else 'MISMATCH'}")

    aff = [r["affect"] for r in records]
    print("   (3) affect ⟂ label (Pearson |r|, want ≈0):  " +
          "  ".join(f"{ax}={abs(_corr(aff,[r[ax] for r in records])):.3f}" for ax in ("act","real","def")))

    # (4) marker diversity: distinct templates realising each axis value
    tdiv = {}
    for r in records:
        ax, val = r["toggled_axis"], (r[r["toggled_axis"]])
        tdiv.setdefault((ax, val), set()).add(r["tmpl"])
    print("   (4) marker diversity (distinct templates per axis-value, want >1):  " +
          "  ".join(f"{ax}{v}={len(tdiv[(ax,v)])}" for ax in ("act","real","def") for v in (1,0)))

    print("   (5) label balance:  " +
          "  ".join(f"{ax} hi={sum(r[ax] for r in records)}/{n}" for ax in ("act","real","def"))
          + f"   affect hi={sum(aff)}/{n}")

    print("\n   sample minimal pairs (sensitive-benign topic):")
    seen = set()
    for r in records:
        ax = r["toggled_axis"]
        if ax in seen or r["topic_id"] != "security.vpn" or r["affect"] != 0:
            continue
        seen.add(ax)
        hi, lo = pairs[r["pair_id"]]
        if hi["act"]+hi["real"]+hi["def"] < lo["act"]+lo["real"]+lo["def"]:
            hi, lo = lo, hi
        print(f"     [{ax}]  HI: {hi['text']}")
        print(f"            LO: {lo['text']}")


def main():
    records = generate()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    verify(records)
    print(f"\n   → wrote {len(records)} records to {OUT.relative_to(OUT.parents[2])}")


if __name__ == "__main__":
    main()
