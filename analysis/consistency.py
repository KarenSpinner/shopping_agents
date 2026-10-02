#!/usr/bin/env python3
"""The lottery study: does the same customer with the same file get the same answer?

Reads the lottery run logs (five tries per case, no customer reply) and writes
data/tables/lottery_*.csv. Uses only the Python standard library.

  python analysis/consistency.py
"""
import csv, glob, json, statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = ["GPT-4o", "GPT-5.6 Luna", "GPT-5.6 Sol", "Claude Haiku 4.5", "Claude Sonnet 5", "Claude Opus 5", "Gemini 3.8 Flash", "Gemini 3.1 Pro"]
LOTTERY = {"neutral": "lottery-neutral", "cost_two_sentences": "lottery-cost"}
SEPTEMBER = {"neutral": ["neutral-seven-models", "neutral-gpt-4o"], "cost_two_sentences": ["cost-two-sentences"]}


def load(prefix):
    rows = []
    for p in sorted((ROOT / "runs").glob(f"{prefix}*.jsonl")):
        if p.name.startswith("mock-"):
            continue
        for line in p.read_text().splitlines():
            d = json.loads(line)
            if "_meta" not in d and d.get("reply") == "nothing":
                rows.append(d)
    return rows


def offers_by_case(rows):
    """{(model, case_id, merit): [first offers across tries]}"""
    d = defaultdict(list)
    for r in rows:
        if r["first"] and r["first"]["offer"] is not None:
            d[(r["model"], r["case_id"], r["merit"])].append(r["first"]["offer"])
    return d


def disagree(v):
    """Chance that two tries drawn at random, without replacement, give different offers."""
    n = len(v)
    if n < 2:
        return 0.0
    same = sum(v.count(x) * (v.count(x) - 1) for x in set(v))
    return 1 - same / (n * (n - 1))


def fmt(x, pct=False, signed=False):
    if x is None:
        return ""
    if pct:
        return f"{100 * x:.0f}%"
    return f"{x:+.1f}" if signed else f"{x:.1f}"


def write(name, header, body, note):
    p = ROOT / "data/tables" / f"{name}.csv"; p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(body)
    print(f"\n== {name}: {note}")
    widths = [max(len(str(x)) for x in col) for col in zip(header, *body)] if body else [len(h) for h in header]
    for row in [header] + body:
        print("  " + "  ".join(str(x).ljust(w) for x, w in zip(row, widths)))


def main():
    for label, prefix in LOTTERY.items():
        rows = load(prefix)
        if not rows:
            print(f"no rows yet for {prefix}"); continue
        cells = offers_by_case(rows)
        tries = sorted({len(v) for v in cells.values()})
        print(f"\n######## {label}: {len(rows)} trials, {len(cells)} model-by-case cells, tries per cell {tries}, "
              f"${sum(r['cost_usd'] for r in rows):.2f}, outcomes {dict(sorted({o: sum(r['outcome'] == o for r in rows) for o in {r['outcome'] for r in rows}}.items()))}")

        # ---- A. how often the same case gets the same answer, by model
        body = []
        for m in MODELS:
            cv = [v for (mm, _, _), v in cells.items() if mm == m and len(v) >= 2]
            if not cv:
                continue
            body.append([m, len(cv),
                         fmt(sum(len(set(v)) == 1 for v in cv) / len(cv), pct=True),
                         fmt(st.mean(len(set(v)) for v in cv)),
                         fmt(st.mean(max(v) - min(v) for v in cv)),
                         fmt(sum(max(v) - min(v) >= 25 for v in cv) / len(cv), pct=True),
                         fmt(st.mean(disagree(v) for v in cv), pct=True),
                         fmt(sum(any(x == 100 for x in v) and any(x < 100 for x in v) for v in cv) / len(cv), pct=True),
                         fmt(sum(any(x == 0 for x in v) and any(x > 0 for x in v) for v in cv) / len(cv), pct=True)])
        write(f"lottery_consistency_{label}", ["model", "cases", "same_answer_every_try", "distinct_answers_per_case", "mean_spread_points",
                                              "cases_spread_25_or_more", "chance_two_tries_differ", "full_payment_flips", "refusal_flips"], body,
              f"{label} instruction, five tries per case with no customer reply")

        # ---- B. the same, by claim type (all models pooled)
        body = []
        for merit in ("sound", "weak", "covered"):
            cv = [v for (_, _, k), v in cells.items() if k == merit and len(v) >= 2]
            if not cv:
                continue
            body.append([merit, len(cv), fmt(sum(len(set(v)) == 1 for v in cv) / len(cv), pct=True), fmt(st.mean(max(v) - min(v) for v in cv)),
                         fmt(st.mean(disagree(v) for v in cv), pct=True),
                         fmt(sum(any(x == 100 for x in v) and any(x < 100 for x in v) for v in cv) / len(cv), pct=True),
                         fmt(sum(any(x == 0 for x in v) and any(x > 0 for x in v) for v in cv) / len(cv), pct=True)])
        write(f"lottery_by_claim_type_{label}", ["claim_type", "model_case_cells", "same_answer_every_try", "mean_spread_points", "chance_two_tries_differ",
                                                "full_payment_flips", "refusal_flips"], body, f"{label} instruction, all eight models pooled")

        # ---- C. is a retry worth it? For every try that came back short, how often were the other tries paid in full?
        body = []
        for merit in ("sound", "weak"):
            for m in MODELS + ["All eight"]:
                short, other_full, any_full, better = 0, 0, 0, 0
                for (mm, _, k), v in cells.items():
                    if k != merit or (m != "All eight" and mm != m) or len(v) < 2:
                        continue
                    for i, x in enumerate(v):
                        if x < 100:
                            others = v[:i] + v[i + 1:]
                            short += 1
                            other_full += sum(o == 100 for o in others) / len(others)
                            any_full += any(o == 100 for o in others)
                            better += sum(o > x for o in others) / len(others)
                if short:
                    body.append([merit, m, short, fmt(better / short, pct=True), fmt(other_full / short, pct=True), fmt(any_full / short, pct=True)])
        write(f"lottery_retry_{label}", ["claim_type", "model", "tries_that_came_back_short", "chance_another_try_pays_more", "chance_another_try_pays_in_full",
                                        "chance_one_of_four_more_tries_pays_in_full"], body,
              f"{label} instruction: for a customer whose try came back short of full payment, what the other tries of the same case did")

        # ---- D. the widest spreads
        body = sorted([[m, c, k, " ".join(f"{int(x) if x == int(x) else x}" for x in v), fmt(max(v) - min(v))] for (m, c, k), v in cells.items() if len(v) >= 2],
                      key=lambda r: -float(r[4]))[:25]
        write(f"lottery_widest_spreads_{label}", ["model", "case_id", "claim_type", "five_offers", "spread"], body, f"{label} instruction, the 25 model-by-case cells with the widest spread")

        # ---- E. drift against the September single try
        sept = offers_by_case([r for pfx in SEPTEMBER[label] for r in load(pfx)])
        body = []
        for m in MODELS:
            row = [m]
            for merit in ("sound", "weak"):
                s = [v[0] for (mm, _, k), v in sept.items() if mm == m and k == merit]
                o = [st.mean(v) for (mm, _, k), v in cells.items() if mm == m and k == merit]
                row += [fmt(st.mean(s)) if s else "", fmt(st.mean(o)) if o else "", fmt(st.mean(o) - st.mean(s), signed=True) if s and o else ""]
            body.append(row)
        write(f"lottery_drift_{label}", ["model", "sound_september", "sound_october_mean", "sound_change", "weak_september", "weak_october_mean", "weak_change"], body,
              f"{label} instruction: first offers in the September single-try run against the October five-try mean")


def extras():
    for label, prefix in LOTTERY.items():
        rows = load(prefix)
        drops = [r for r in rows if r["shift"] is not None and r["shift"] < 0]
        body = []
        for m in MODELS:
            d = [r for r in drops if r["model"] == m]
            n = sum(1 for r in rows if r["model"] == m and r["shift"] is not None)
            body.append([m, n, len(d), fmt(len(d) / n, pct=True) if n else "", fmt(st.mean(r["shift"] for r in d), signed=True) if d else "",
                         ", ".join(sorted({r["case_id"] for r in d}))])
        write(f"lottery_offer_lowered_without_reply_{label}", ["model", "trials", "offer_lowered", "share", "mean_change", "cases"], body,
              f"{label} instruction: trials where the agent's final offer was lower than its first offer although the customer sent nothing")
        cells = offers_by_case(rows)
        body = [[m, c, " ".join(f"{int(x) if x == int(x) else x}" for x in v)] for (m, c, k), v in sorted(cells.items()) if k == "covered" and any(x < 100 for x in v)]
        write(f"lottery_covered_not_full_{label}", ["model", "case_id", "five_offers"], body, f"{label} instruction: covered claims not paid in full on every try")


if __name__ == "__main__":
    extras()
    main()
