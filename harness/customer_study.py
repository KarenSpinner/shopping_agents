#!/usr/bin/env python3
"""Customer service study harness.

A model plays a company's resolution agent. It reads a policy, a request, and the company's
records, and states what percent of the request it will grant. It then reads the customer's
reply, or is told there was none, and gives a final percent.

Commands
  ping         one tiny call per model: confirms keys and model ids
  run          run cases x replies x models under an instruction, logging every trial
  summary      print the main tables for one run log
  transcripts  write a readable HTML page for a run log, optionally a random sample

Every model call is logged in full. Errors and refusals are recorded, never dropped.
"""
import argparse, concurrent.futures as cf, datetime as dt, hashlib, html, json, os, random, re, statistics, sys, threading, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPLIES = ["nothing", "one_line", "argument", "emotion", "argument_emotion", "angry", "threat"]
MERITS = ["sound", "weak", "covered"]
KEY_ENV = {"anthropic": ["ANTHROPIC_API_KEY"], "openai": ["OPENAI_API_KEY"], "google": ["GEMINI_API_KEY", "GOOGLE_API_KEY"], "mock": []}
OFFER_RE = re.compile(r"(?im)^\W*(?:final(?:ized)?\s+)?OFFER\W*:\s*(\d{1,3}(?:\.\d+)?)\s*%?")


# ----------------------------------------------------------------------------- utilities
def load_env():
    """Read KEY=VALUE lines from .env at the project root. Never overrides, never prints."""
    p = ROOT / ".env"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def jload(rel):
    return json.loads((ROOT / rel).read_text())


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def has_key(provider):
    return provider == "mock" or any(os.environ.get(k) for k in KEY_ENV[provider])


def parse_offer(text):
    """The last line of the form 'OFFER: <0-100>' in a reply, or None."""
    m = OFFER_RE.findall(text or "")
    if not m:
        return None
    v = float(m[-1])
    return v if 0 <= v <= 100 else None


class Budget:
    """Spend guard. A run stops starting new trials once spending reaches the cap."""
    def __init__(self, cap):
        self.cap, self.spent, self.lock = cap, 0.0, threading.Lock()

    def add(self, usd):
        with self.lock:
            self.spent += usd

    def exhausted(self):
        with self.lock:
            return self.spent >= self.cap


def cost_of(cfg, usage):
    return (usage.get("in", 0) * cfg["price_in"] + usage.get("out", 0) * cfg["price_out"]) / 1e6


# ----------------------------------------------------------------------------- providers
_clients = {}
_client_lock = threading.Lock()


def client(provider):
    with _client_lock:
        if provider not in _clients:
            if provider == "anthropic":
                import anthropic
                _clients[provider] = anthropic.Anthropic(max_retries=3)
            elif provider == "openai":
                import openai
                _clients[provider] = openai.OpenAI(max_retries=3)
            elif provider == "google":
                from google import genai
                _clients[provider] = genai.Client()
        return _clients[provider]


def call_model(cfg, system, turns, max_out):
    """turns: list of {"role": "user"|"assistant", "text": str, "replay": provider content or None}."""
    t0 = time.time()
    try:
        out = {"anthropic": _anthropic, "openai": _openai, "google": _google, "mock": _mock}[cfg["provider"]](cfg, system, turns, max_out)
    except Exception as e:
        status = getattr(e, "status_code", None) or getattr(e, "code", None)
        retryable = type(e).__name__ in ("RateLimitError", "APIConnectionError", "APITimeoutError", "ServerError", "InternalServerError") or (
            isinstance(status, int) and (status == 429 or status >= 500))
        out = {"text": "", "usage": {"in": 0, "out": 0, "reasoning": 0}, "stop": None, "refusal": None, "replay": None,
               "error": {"type": type(e).__name__, "status": getattr(e, "status_code", None), "message": str(e)[:500], "retryable": retryable}}
    out["latency_s"] = round(time.time() - t0, 2)
    return out


def _anthropic(cfg, system, turns, max_out):
    msgs = [{"role": t["role"], "content": t.get("replay") or t["text"]} for t in turns]
    r = client("anthropic").messages.create(model=cfg["id"], max_tokens=max_out, system=system, messages=msgs, **cfg.get("params", {}))
    text = "".join(b.text for b in r.content if b.type == "text")
    replay = [b.model_dump(mode="json", exclude_none=True) for b in r.content]
    refusal = None
    if r.stop_reason == "refusal":
        sd = getattr(r, "stop_details", None)
        refusal = {"category": getattr(sd, "category", None), "explanation": getattr(sd, "explanation", None)}
    return {"text": text, "usage": {"in": r.usage.input_tokens, "out": r.usage.output_tokens, "reasoning": None},
            "stop": r.stop_reason, "refusal": refusal, "replay": replay, "error": None}


def _openai(cfg, system, turns, max_out):
    msgs = [{"role": "system", "content": system}] + [{"role": t["role"], "content": t["text"]} for t in turns]
    r = client("openai").chat.completions.create(model=cfg["id"], messages=msgs, max_completion_tokens=max_out, **cfg.get("params", {}))
    ch = r.choices[0]
    det = getattr(r.usage, "completion_tokens_details", None)
    refusal = getattr(ch.message, "refusal", None)
    return {"text": ch.message.content or "", "usage": {"in": r.usage.prompt_tokens, "out": r.usage.completion_tokens,
                                                        "reasoning": getattr(det, "reasoning_tokens", None)},
            "stop": ch.finish_reason, "refusal": {"explanation": refusal} if refusal else None, "replay": None, "error": None}


def _google(cfg, system, turns, max_out):
    from google.genai import types
    params = dict(cfg.get("params", {}))
    if "thinking_config" in params:
        params["thinking_config"] = types.ThinkingConfig(**params["thinking_config"])
    contents = [types.Content(role="user" if t["role"] == "user" else "model", parts=[types.Part(text=t["text"])]) for t in turns]
    r = client("google").models.generate_content(model=cfg["id"], contents=contents,
                                                 config=types.GenerateContentConfig(system_instruction=system, max_output_tokens=max_out, **params))
    um = r.usage_metadata
    thoughts = getattr(um, "thoughts_token_count", None) or 0
    finish = str(r.candidates[0].finish_reason) if r.candidates else None
    blocked = getattr(getattr(r, "prompt_feedback", None), "block_reason", None)
    refusal = {"explanation": str(blocked or finish)} if (blocked or (finish and "SAFETY" in finish)) else None
    return {"text": r.text or "", "usage": {"in": um.prompt_token_count or 0, "out": (um.candidates_token_count or 0) + thoughts, "reasoning": thoughts},
            "stop": finish, "refusal": refusal, "replay": None, "error": None}


def _mock(cfg, system, turns, max_out):
    """Offline stand-in for testing the pipeline. Deterministic per prompt. Makes no API call."""
    last = turns[-1]["text"]
    rng = random.Random(hashlib.md5((cfg["id"] + last).encode()).hexdigest())
    before = parse_offer(turns[-2]["text"]) if len(turns) >= 3 else None
    if before is None:
        text = f"Here is my decision.\nOFFER: {rng.choice([20, 40, 50, 60, 80, 100])}"
    else:
        bump = rng.choice([0, 0, 10, 20]) if "Reply from the customer" in last else 0
        text = f"Finalizing.\nOFFER: {min(100, int(before) + bump)}"
    toks = lambda s: max(1, len(s) // 4)
    return {"text": text, "usage": {"in": toks(system) + sum(toks(t["text"]) for t in turns), "out": toks(text), "reasoning": 0},
            "stop": "end_turn", "refusal": None, "replay": None, "error": None}


# ----------------------------------------------------------------------------- one trial
def turn_record(prompt, r, offer, customer_message=None, final=False):
    d = {"prompt": prompt}
    if final:
        d["customer_message"] = customer_message
    d.update(text=r["text"], offer=offer, usage=r["usage"], stop=r["stop"], refusal=r["refusal"], error=r["error"], latency_s=r["latency_s"])
    return d


def run_trial(spec, T, instruction, budget, max_out):
    cfg, case = spec["cfg"], spec["case"]
    rec = {"run": spec["run"], "instruction_label": spec["label"], "trial_id": spec["trial_id"], "model": cfg["name"], "model_id": cfg["id"],
           "provider": cfg["provider"], "params": cfg.get("params", {}), "case_id": case["id"], "pair": case["pair"], "merit": case["merit"],
           "company": case["company"], "reply": spec["reply"], "opener_variant": spec["variant"], "timestamp": now(),
           "first": None, "final": None, "shift": None, "reached_full": None, "outcome": None, "cost_usd": 0.0}
    if budget.exhausted():
        rec["outcome"] = "not_run_budget"; return rec
    system = instruction.replace("{COMPANY}", case["company"])
    u1 = T["first_turn"].format(N=spec["number"], POLICY=case["policy"], REQUEST=case["request"], RECORD=case["record"])
    turns = [{"role": "user", "text": u1}]
    r1 = call_model(cfg, system, turns, max_out)
    c1 = cost_of(cfg, r1["usage"]); budget.add(c1); o1 = parse_offer(r1["text"])
    rec["first"] = turn_record(u1, r1, o1); rec["cost_usd"] = round(c1, 6)
    if r1["error"]:
        rec["outcome"] = "error"; return rec
    if o1 is None:
        rec["outcome"] = "first_unparsed"; return rec
    msg = spec["message"]
    u2 = T["final_turn_no_reply"] if msg is None else T["final_turn_with_reply"].replace("{MSG}", msg)
    turns += [{"role": "assistant", "text": r1["text"], "replay": r1["replay"]}, {"role": "user", "text": u2}]
    if budget.exhausted():
        rec["outcome"] = "not_run_budget"; return rec
    r2 = call_model(cfg, system, turns, max_out)
    c2 = cost_of(cfg, r2["usage"]); budget.add(c2); o2 = parse_offer(r2["text"])
    rec["final"] = turn_record(u2, r2, o2, msg, final=True); rec["cost_usd"] = round(c1 + c2, 6)
    if r2["error"]:
        rec["outcome"] = "error"; return rec
    if r2["refusal"]:
        rec["outcome"] = "refusal"; return rec
    if o2 is None:
        rec["outcome"] = "unparsed"; return rec
    rec["shift"] = o2 - o1; rec["reached_full"] = bool(o2 >= 100 and o1 < 100)
    rec["outcome"] = "moved" if rec["shift"] >= 5 else "moved_away" if rec["shift"] <= -5 else "held"
    return rec


# ----------------------------------------------------------------------------- commands
def pick_models(a, M):
    models = M["models"]
    if a.mock:
        return [dict(m, provider="mock", price_in=0, price_out=0) for m in models]
    if a.models:
        want = [w.strip().lower() for w in a.models.split(",")]
        models = [m for m in models if m["id"].lower() in want or m["name"].lower() in want]
    ok = [m for m in models if has_key(m["provider"])]
    for m in models:
        if m not in ok:
            print(f"  skipping {m['name']}: no API key for {m['provider']} ({' or '.join(KEY_ENV[m['provider']])})")
    return ok


def cmd_ping(a):
    load_env(); models = pick_models(a, jload("config/models.json"))
    for m in models:
        r = call_model(m, "Reply with the single word OK.", [{"role": "user", "text": "Reply with the single word OK."}], 300)
        status = f"ERROR {r['error']['type']}: {r['error']['message'][:160]}" if r["error"] else f"ok  text={r['text'][:20]!r}"
        print(f"  {m['name']:18s} {m['id']:24s} {status}")
    if not models:
        print("  no models have keys. Add keys to .env at the project root.")


def cmd_run(a):
    load_env(); M = jload("config/models.json"); T = jload("cases/messages.json"); cases = jload("cases/cases.json")["cases"]
    if a.cases:
        cases = cases[:a.cases]
    models = pick_models(a, M)
    if not models:
        print("No models to run."); return 1
    replies = [r.strip() for r in a.replies.split(",")] if a.replies else REPLIES
    bad = [r for r in replies if r not in REPLIES]
    if bad:
        print(f"unknown reply type(s) {bad}; choose from {REPLIES}"); return 1
    instruction = T["instruction"] + (" " + a.instruction.strip() if a.instruction else "")
    run = ("mock-" if a.mock else "") + dt.datetime.now().strftime(f"{a.label}-%Y%m%d-%H%M%S")
    specs = []
    for cfg in models:
        for i, case in enumerate(cases):
            block = T["cases"][case["id"]]
            for reply in replies:
                specs.append({"run": run, "label": a.label, "trial_id": f"{run}|{cfg['id']}|{case['id']}|{reply}", "cfg": cfg, "case": case,
                              "reply": reply, "variant": None if reply == "nothing" else block["opener_variant"],
                              "message": None if reply == "nothing" else block["messages"][reply], "number": i + 1})
    meta = {"run": run, "instruction_label": a.label, "run_id": run, "started": now(), "instruction": instruction, "added_instruction": a.instruction,
            "replies": replies, "cases": [c["id"] for c in cases], "models": [m["id"] for m in models],
            "max_output_tokens": M["max_output_tokens"], "cap_usd": a.cap, "n_trials": len(specs)}
    out = ROOT / "runs"; out.mkdir(exist_ok=True); log = out / f"{run}.jsonl"; budget = Budget(a.cap)
    print(f"run {run}: {len(specs)} trials, {len(models)} models, {len(cases)} cases, cap ${a.cap:.2f}")
    with open(log, "w") as f:
        f.write(json.dumps({"_meta": meta}, ensure_ascii=False) + "\n")
        with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
            for i, rec in enumerate(ex.map(lambda s: run_trial(s, T, instruction, budget, M["max_output_tokens"]), specs), 1):
                f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
                if i % 50 == 0:
                    print(f"  {i}/{len(specs)} trials, ${budget.spent:.3f} spent")
    print("wrote", log.relative_to(ROOT))
    summarize(log)
    return 0


def read_log(path):
    meta, recs = None, []
    for line in Path(path).read_text().splitlines():
        d = json.loads(line)
        if "_meta" in d:
            meta = d["_meta"]
        else:
            recs.append(d)
    return meta, recs


def summarize(path):
    meta, recs = read_log(path)
    ok = "counts reconcile" if meta["n_trials"] == len(recs) else "COUNT MISMATCH"
    print(f"\nSUMMARY {meta['run']}  planned {meta['n_trials']}  logged {len(recs)}  {ok}")
    print(f"  instruction added: {meta['added_instruction'] or 'none (neutral)'}")
    print(f"  spend ${sum(r['cost_usd'] for r in recs):.2f} of cap ${meta['cap_usd']:.2f}")
    oc = {}
    for r in recs:
        oc[r["outcome"]] = oc.get(r["outcome"], 0) + 1
    print("  outcomes:", dict(sorted(oc.items())))
    names = list(dict.fromkeys(r["model"] for r in recs))
    print("\n  first offer, percent of the request granted before any reply: mean by model and merit")
    print(f"  {'model':20s}" + "".join(f"{m:>10s}" for m in MERITS))
    for n in names:
        row = f"  {n:20s}"
        for m in MERITS:
            v = [r["first"]["offer"] for r in recs if r["model"] == n and r["merit"] == m and r["first"] and r["first"]["offer"] is not None]
            row += f"{statistics.mean(v):10.1f}" if v else f"{'-':>10s}"
        print(row)
    for m in MERITS:
        print(f"\n  {m} cases: mean points gained from first offer to final, by reply")
        print(f"  {'model':20s}" + "".join(f"{c:>18s}" for c in meta["replies"]))
        for n in names:
            row = f"  {n:20s}"
            for c in meta["replies"]:
                v = [r["shift"] for r in recs if r["model"] == n and r["merit"] == m and r["reply"] == c and r["shift"] is not None]
                row += f"{statistics.mean(v):+18.1f}" if v else f"{'-':>18s}"
            print(row)


def cmd_summary(a):
    summarize(a.log)


def cmd_transcripts(a):
    meta, recs = read_log(a.log); esc = html.escape
    cases = {c["id"]: c for c in jload("cases/cases.json")["cases"]}
    if a.sample:
        recs = random.Random(a.seed).sample(recs, min(a.sample, len(recs)))
        recs.sort(key=lambda r: (r["model"], r["case_id"], REPLIES.index(r["reply"])))
    title = f"Transcripts: {meta['run']}"
    parts = [f"<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>{esc(title)}</title>"
             "<style>body{font:16px/1.5 system-ui,sans-serif;max-width:860px;margin:0 auto;padding:24px 16px;background:#f6f7f9;color:#151a21}"
             "h1{font-size:26px}h2{margin-top:40px;border-bottom:2px solid #151a21}.t{background:#fff;border:1px solid #d8dee6;padding:14px 16px;margin:12px 0}"
             ".m{font:12px ui-monospace,monospace;color:#5c6572;text-transform:uppercase;letter-spacing:.05em}.c{font-size:14.5px;color:#5c6572;background:#edf0f5;padding:10px;margin:6px 0}"
             ".msg{border-left:4px solid #d9652b;padding-left:10px;margin:8px 0}pre{white-space:pre-wrap;font:14px/1.45 ui-monospace,monospace;background:#edf0f5;padding:10px;margin:6px 0}"
             ".moved{color:#b8262b;font-weight:700}.held{color:#2a8c6a;font-weight:700}.moved_away{color:#1f4fb8;font-weight:700}</style>",
             f"<h1>{esc(title)}</h1><p>{len(recs)} trials{' (random sample)' if a.sample else ''}. Instruction added to the agent: "
             f"{esc(meta['added_instruction'] or 'none (neutral)')}. Each card shows the case, the agent's first reply, the customer's message, and the agent's final reply. "
             "Offers are the percent of the request granted.</p>"]
    for name in dict.fromkeys(r["model"] for r in recs):
        parts.append(f"<h2>{esc(name)}</h2>")
        for r in [x for x in recs if x["model"] == name]:
            c = cases.get(r["case_id"]); cls = r["outcome"] if r["outcome"] in ("moved", "held", "moved_away") else ""
            o1 = r["first"]["offer"] if r["first"] else None; o2 = r["final"]["offer"] if r["final"] else None
            parts.append(f"<div class='t'><div class='m'>{esc(r['case_id'])} · {esc(r['company'])} · {esc(c['title'] if c else '')} · {esc(r['merit'])} claim · reply: {esc(r['reply'])} · "
                         f"offer {o1} → {o2} · <span class='{cls}'>{esc(r['outcome'])}</span></div>")
            if c:
                parts.append(f"<div class='c'>Policy: {esc(c['policy'])} Request: {esc(c['request'])}. Records: {esc(c['record'])}</div>")
            if r["first"]:
                parts.append(f"<div class='m'>agent, first reply</div><pre>{esc(r['first']['text'] or str(r['first']['error']))}</pre>")
            if r["final"]:
                parts.append(f"<div class='msg'>{esc(r['final']['customer_message'] or 'No reply was received from the customer.')}</div>")
                parts.append(f"<div class='m'>agent, final reply</div><pre>{esc(r['final']['text'] or str(r['final']['error']))}</pre>")
            parts.append("</div>")
    out = ROOT / "runs/transcripts"; out.mkdir(parents=True, exist_ok=True)
    p = out / (Path(a.log).stem + (".sample.html" if a.sample else ".html")); p.write_text("\n".join(parts)); print("wrote", p.relative_to(ROOT))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("ping"); s.add_argument("--models"); s.add_argument("--mock", action="store_true"); s.set_defaults(fn=cmd_ping)
    s = sub.add_parser("run")
    s.add_argument("--replies", help="comma list from: " + ",".join(REPLIES) + " (default: all seven)")
    s.add_argument("--instruction", help="sentence(s) added to the agent's instruction; {COMPANY} is replaced by the company name")
    s.add_argument("--label", default="run", help="name for this run; the log is written to runs/<label>-<timestamp>.jsonl")
    s.add_argument("--cap", type=float, default=5.00, help="stop starting new trials when spending reaches this many dollars")
    s.add_argument("--models", help="comma list of model names or ids (default: all in config/models.json)")
    s.add_argument("--cases", type=int, default=0, help="use only the first N cases")
    s.add_argument("--workers", type=int, default=6); s.add_argument("--mock", action="store_true", help="test the pipeline without calling any API")
    s.set_defaults(fn=cmd_run)
    s = sub.add_parser("summary"); s.add_argument("log"); s.set_defaults(fn=cmd_summary)
    s = sub.add_parser("transcripts"); s.add_argument("log"); s.add_argument("--sample", type=int, default=0); s.add_argument("--seed", type=int, default=30)
    s.set_defaults(fn=cmd_transcripts)
    a = p.parse_args(); sys.exit(a.fn(a) or 0)


if __name__ == "__main__":
    main()
