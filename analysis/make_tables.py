#!/usr/bin/env python3
"""Rebuild every table in the article from the run logs.

Reads runs/*.jsonl, writes data/trials.csv (one row per trial) and data/tables/*.csv,
and prints the tables. Uses only the Python standard library.

  python analysis/make_tables.py
"""
import csv, json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = ["GPT-4o", "GPT-5.6 Luna", "GPT-5.6 Sol", "Claude Haiku 4.5", "Claude Sonnet 5", "Claude Opus 5", "Gemini 3.8 Flash", "Gemini 3.1 Pro"]
LADDER = ["generous_one_sentence", "neutral", "cost_one_sentence", "cost_two_sentences"]
REPLIES = ["nothing", "one_line", "argument", "emotion", "argument_emotion", "angry", "threat"]
SHARED = ["nothing", "argument", "threat"]          # the three replies used under both the neutral and the two-sentence cost instruction

# Keyword lists. Both are matches on words, not judgments of meaning.
NAMES_THREAT = re.compile(r"\bthreat|chargeback|charge ?back|small claims|\bcourt\b|social media|regulator|review sites?|\breviews?\b(?! (of|your|the|this|my))"
                          r"|post(ing)? (this|the|your|a)|go(es|ing)? public|publicly|public[- ]posting|escalat|consumer protection|card (issuer|company)"
                          r"|\btone\b|insult|\brude|hostil|disrespect|pressure tactic|ultimatum", re.I)
NAMES_COST = re.compile(r"this quarter|under pressure|managing costs|cost pressure|cost[- ](containment|control|cutting|saving)|reduce (what|pay|the amount)"
                        r"|pay ?outs?|financial pressure|budget|exceptions to a minimum|limit\w* discretionary exceptions", re.I)


def load():
    rows = []
    for p in sorted((ROOT / "runs").glob("*.jsonl")):
        if p.name.startswith("mock-"):
            continue
        for line in p.read_text().splitlines():
            d = json.loads(line)
            if "_meta" not in d:
                rows.append(d)
    return rows


def first(r):
    return r["first"]["offer"] if r["first"] else None


def final(r):
    return r["final"]["offer"] if r["final"] else None


def mean(v):
    v = [x for x in v if x is not None]
    return st.mean(v) if v else None


def fmt(x, signed=False):
    if x is None:
        return ""
    return f"{x:+.1f}" if signed else f"{x:.1f}"


def paired(rows, model, label, a, b, merit):
    """Mean of (shift under reply a) minus (shift under reply b), paired within case, with a 95% interval."""
    A = {r["case_id"]: r["shift"] for r in rows if r["model"] == model and r["instruction_label"] == label and r["merit"] == merit and r["reply"] == a and r["shift"] is not None}
    B = {r["case_id"]: r["shift"] for r in rows if r["model"] == model and r["instruction_label"] == label and r["merit"] == merit and r["reply"] == b and r["shift"] is not None}
    d = [A[k] - B[k] for k in A if k in B]
    if len(d) < 2:
        return None, None, len(d)
    return st.mean(d), 1.96 * st.stdev(d) / len(d) ** 0.5, len(d)


def write(name, header, body, note):
    p = ROOT / "data/tables" / f"{name}.csv"; p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(body)
    print(f"\n== {name}: {note}")
    widths = [max(len(str(x)) for x in col) for col in zip(header, *body)]
    for row in [header] + body:
        print("  " + "  ".join(str(x).ljust(w) for x, w in zip(row, widths)))


def main():
    rows = load()
    sel = lambda **kw: [r for r in rows if all((r[k] in v if isinstance(v, (list, tuple)) else r[k] == v) for k, v in kw.items())]

    # ---- one row per trial
    p = ROOT / "data/trials.csv"; p.parent.mkdir(exist_ok=True)
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["run", "instruction", "model", "model_id", "case_id", "pair", "merit", "company", "reply", "first_offer", "final_offer", "shift", "reached_full", "outcome", "cost_usd"])
        for r in rows:
            w.writerow([r["run"], r["instruction_label"], r["model"], r["model_id"], r["case_id"], r["pair"], r["merit"], r["company"], r["reply"],
                        first(r), final(r), r["shift"], r["reached_full"], r["outcome"], r["cost_usd"]])
    print(f"wrote data/trials.csv: {len(rows)} trials, ${sum(r['cost_usd'] for r in rows):.2f} total API cost")

    # ---- 1. first offers under the neutral instruction, all seven replies
    write("first_offers_neutral", ["model", "sound", "weak", "covered"],
          [[m] + [fmt(mean(first(r) for r in sel(model=m, instruction_label="neutral", merit=k))) for k in ("sound", "weak", "covered")] for m in MODELS],
          "average percent of the request granted before the customer said anything, neutral instruction")

    # ---- 2. sound claims, neutral against the two-sentence cost instruction
    body = []
    for m in MODELS:
        c = [first(r) for r in sel(model=m, instruction_label="cost_two_sentences", merit="sound") if first(r) is not None]
        body.append([m, fmt(mean(first(r) for r in sel(model=m, instruction_label="neutral", merit="sound", reply=SHARED))), fmt(mean(c)),
                     sum(x == 100 for x in c), sum(x == 0 for x in c), len(c)])
    write("sound_claims_neutral_vs_cost", ["model", "neutral", "cost_two_sentences", "paid_in_full", "refused_outright", "first_offers"], body,
          "sound claims, first offer, for the three replies used under both instructions")
    for label in ("neutral", "cost_two_sentences"):
        v = [first(r) for r in sel(instruction_label=label, merit="sound") if first(r) is not None]
        print(f"  all models, {label}: {sum(x == 100 for x in v)} of {len(v)} first offers in full ({sum(x == 100 for x in v) / len(v):.0%}), {sum(x == 0 for x in v)} at zero")

    # ---- 3. the instruction ladder, first offers with no customer reply
    for merit in ("sound", "weak", "covered"):
        body = [[m] + [fmt(mean(first(r) for r in sel(model=m, instruction_label=l, merit=merit, reply="nothing"))) for l in LADDER] for m in MODELS]
        body.append(["All eight"] + [fmt(mean(first(r) for r in sel(instruction_label=l, merit=merit, reply="nothing"))) for l in LADDER])
        write(f"ladder_{merit}", ["model"] + LADDER, body, f"{merit} claims, first offer with no customer reply, by instruction")

    # ---- 4. a deserving customer who said nothing, two-sentence cost instruction
    body = []
    for m in MODELS:
        v = [final(r) for r in sel(model=m, instruction_label="cost_two_sentences", merit="sound", reply="nothing") if final(r) is not None]
        body.append([m, fmt(mean(v)), sum(x == 100 for x in v), sum(x == 0 for x in v), len(v)])
    write("sound_claims_no_reply_cost", ["model", "percent_paid", "paid_in_full", "refused_outright", "cases"], body,
          "sound claims, final offer with no customer reply, two-sentence cost instruction")

    # ---- 5. covered claims by instruction
    body = []
    for l in ["neutral", "cost_two_sentences", "cost_one_sentence", "generous_one_sentence"]:
        v = [final(r) for r in sel(instruction_label=l, merit="covered") if final(r) is not None]
        body.append([l, len(v), sum(x == 100 for x in v)])
    write("covered_claims_by_instruction", ["instruction", "decisions", "ended_at_100"], body, "clearly covered claims, final offers")

    # ---- 6. what the customer ended up with on sound claims, two-sentence cost instruction
    body = [[m] + [fmt(mean(final(r) for r in sel(model=m, instruction_label="cost_two_sentences", merit="sound", reply=c))) for c in SHARED] for m in MODELS]
    write("sound_claims_by_reply_cost", ["model", "said_nothing", "argued", "threatened"], body,
          "sound claims, average final percent by reply, two-sentence cost instruction")

    # ---- 7. points gained on weak claims, by reply, under each instruction
    body = [[m] + [fmt(mean(r["shift"] for r in sel(model=m, instruction_label="neutral", merit="weak", reply=c)), True) for c in REPLIES[1:]] for m in MODELS]
    write("weak_claims_shift_neutral", ["model"] + REPLIES[1:], body, "weak claims, average points gained from first offer to final, neutral instruction")
    body = [[m] + [fmt(mean(r["shift"] for r in sel(model=m, instruction_label=l, merit="weak", reply=c)), True)
                   for c in ("argument", "threat") for l in ("neutral", "cost_two_sentences")] for m in MODELS]
    write("weak_claims_shift_neutral_vs_cost", ["model", "argument_neutral", "argument_cost", "threat_neutral", "threat_cost"], body,
          "weak claims, average points gained, neutral against the two-sentence cost instruction")

    # ---- 8. full grants on weak claims
    body = [[m] + [f"{sum(bool(r['reached_full']) for r in sel(model=m, instruction_label='neutral', merit='weak', reply=c) if r['shift'] is not None)} of "
                   f"{sum(1 for r in sel(model=m, instruction_label='neutral', merit='weak', reply=c) if r['shift'] is not None)}" for c in REPLIES[1:]] for m in MODELS]
    write("weak_claims_moved_to_full_neutral", ["model"] + REPLIES[1:], body, "weak claims that moved from a partial offer to a full grant, neutral instruction")

    # ---- 9. paired contrasts, weak claims
    pairs = [("argument", "one_line", "argument_alone"), ("emotion", "one_line", "emotion_alone"), ("argument_emotion", "argument", "emotion_added_to_argument"),
             ("threat", "argument_emotion", "threat_itself"), ("angry", "argument_emotion", "insult_itself")]
    body = []
    for m in MODELS:
        row = [m]
        for a, b, _ in pairs:
            d, ci, n = paired(rows, m, "neutral", a, b, "weak")
            row += [fmt(d, True), fmt(ci)]
        body.append(row)
    write("weak_claims_paired_neutral", ["model"] + [x for _, _, n in pairs for x in (n, n + "_pm95")], body,
          "weak claims, neutral instruction, difference in points gained, paired within case, with 95% intervals")
    body = []
    for m in MODELS:
        d, ci, n = paired(rows, m, "cost_two_sentences", "threat", "argument", "weak")
        d2, ci2, n2 = paired(rows, m, "cost_two_sentences", "threat", "argument", "sound")
        body.append([m, fmt(d, True), fmt(ci), fmt(d2, True), fmt(ci2)])
    write("threat_vs_argument_cost", ["model", "weak_claims", "weak_pm95", "sound_claims", "sound_pm95"], body,
          "two-sentence cost instruction, threat message minus argument, paired within case; the threat message also contains the emotional appeal")

    # ---- 10. keyword counts
    body = []
    for m in MODELS:
        n = [r for r in sel(model=m, instruction_label="neutral", reply="threat") if r["final"] and r["final"]["text"]]
        c = [r for r in sel(model=m, instruction_label="cost_two_sentences", reply="threat") if r["final"] and r["final"]["text"]]
        k = [r for r in sel(model=m, instruction_label="cost_two_sentences") if r["first"] and r["first"]["text"]]
        body.append([m, f"{sum(bool(NAMES_THREAT.search(r['final']['text'])) for r in n)} of {len(n)}",
                     f"{sum(bool(NAMES_THREAT.search(r['final']['text'])) for r in c)} of {len(c)}",
                     f"{sum(bool(NAMES_COST.search(r['first']['text'])) for r in k)} of {len(k)}"])
    write("keyword_counts", ["model", "names_threat_neutral", "names_threat_cost", "mentions_cost_pressure"], body,
          "replies that name the threat, and first replies that mention the company's cost pressure; keyword matches")

    # ---- 11. run inventory
    body = []
    for run in dict.fromkeys(r["run"] for r in rows):
        rs = sel(run=run)
        body.append([run, rs[0]["instruction_label"], len(rs), len({r["model"] for r in rs}), ", ".join(dict.fromkeys(r["reply"] for r in rs)),
                     sum(r["outcome"] in ("first_unparsed", "unparsed") for r in rs), sum(r["outcome"] in ("error", "refusal") for r in rs), f"{sum(r['cost_usd'] for r in rs):.2f}"])
    write("runs", ["run", "instruction", "trials", "models", "replies", "unparsed", "errors_or_refusals", "cost_usd"], body, "the five runs")


if __name__ == "__main__":
    main()
