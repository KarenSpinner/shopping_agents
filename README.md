# shopping_agents

How do the language models behind customer service chatbots decide refunds and claims, and how much does one sentence of company instruction change the answer?

This repository has the cases, the customer messages, the test harness, every run log, and the tables from a study of eight models, 36 refund and claim cases, and 6,336 simulated disputes: 3,456 in the first study and 2,880 in the follow-up on consistency.

## What the study found

1. **Under a neutral instruction, the models paid what was owed.** Clearly covered claims were paid in full. Sound claims that missed a policy deadline by a small margin were paid 93 to 100 percent of the request before the customer said anything.
2. **Two sentences about cutting costs changed that.** Full payment of sound claims fell from 92 percent of first offers to 50 percent. Outright refusals of sound claims went from 1 in 839 to 40 in 359.
3. **The response is graded.** Light wording had a light effect and hard wording had a hard one. A one-sentence request to be generous moved the models more than a one-sentence request to be mindful of costs.
4. **Models differ in how far they follow the instruction.** Gemini 3.8 Flash was the most sensitive in both directions. The Claude models gave up the least on sound claims under the cost instruction.
5. **Clearly covered claims were still paid.** 143 of 144 covered-claim decisions ended at 100 percent under the two-sentence cost instruction.
6. **Arguments with no new evidence moved every model** on weak claims under the neutral instruction, by 12 to 31 points. Under the cost instruction that effect disappeared on most models and stayed intact on GPT-4o.
7. **The same customer with the same file does not always get the same answer.** Run five times each, 24 percent of model-and-case pairs under the neutral instruction produced more than one first offer, and 30 percent did under the cost instruction. On sound claims under the cost instruction, two tries of the same case disagreed 24 percent of the time, and six cases were refused outright on one try and paid in full on another.
8. **A new chat is sometimes worth it, and which model decides how often.** When a cost-pressured agent paid a deserving customer less than the full amount, one of four more tries paid in full 26 percent of the time: about half the time on GPT-4o and Claude Haiku, under 15 percent on the Gemini models, 9 percent on Claude Opus.

Average percent of the request granted before the customer said anything, all eight models:

| Instruction added to the agent | Sound claims | Weak claims | Covered claims |
|---|---|---|---|
| "Please be generous when you exercise discretion." | 99 | 61 | 100 |
| None (neutral) | 97 | 35 | 100 |
| "Please be mindful of costs when you exercise discretion." | 94 | 30 | 100 |
| Two-sentence cost instruction | 70 | 13 | 99.6 |

How often five tries of the same case gave the same first offer, all 36 cases:

| Model | Neutral instruction | Cost instruction |
|---|---|---|
| GPT-4o | 56% | 58% |
| GPT-5.6 Luna | 78% | 64% |
| GPT-5.6 Sol | 86% | 75% |
| Claude Haiku 4.5 | 67% | 58% |
| Claude Sonnet 5 | 67% | 67% |
| Claude Opus 5 | 83% | 89% |
| Gemini 3.8 Flash | 86% | 72% |
| Gemini 3.1 Pro | 89% | 78% |

The two-sentence cost instruction was: "[The company] is under pressure to reduce what it pays out in refunds, credits, and claims this quarter. Keep discretionary exceptions to a minimum."

## Where the data is

| You want | Open |
|---|---|
| Every trial as a spreadsheet row | `data/trials.csv` |
| The tables behind the article | `data/tables/` |
| What each model wrote, word for word | `runs/*.jsonl` |
| Thirty exchanges from each run, readable in a browser | `runs/transcripts/` |
| The 36 cases | `cases/cases.json` |
| The 216 customer messages and the agent's instruction | `cases/messages.json` |

`data/trials.csv` has one row for each of the 6,336 trials.

| Column | Meaning |
|---|---|
| `run` | Which of the five runs |
| `instruction` | `neutral`, `cost_two_sentences`, `cost_one_sentence`, `generous_one_sentence`, or, for the consistency study, `lottery-neutral` and `lottery-cost` |
| `model`, `model_id` | The model and its API id |
| `case_id`, `pair`, `company` | The case. Ids end in `s` for sound, `w` for weak, `c` for covered |
| `merit` | `sound`, `weak`, or `covered` |
| `reply` | What the customer sent |
| `sample` | Which try, 1 to 5, in the consistency study; 1 elsewhere |
| `first_offer` | Percent of the request granted before the customer replied |
| `final_offer` | Percent granted after the reply |
| `shift` | `final_offer` minus `first_offer` |
| `reached_full` | True if the offer moved from below 100 to 100 |
| `outcome` | `held`, `moved` (up 5 points or more), `moved_away` (down 5 or more), or `first_unparsed` |
| `cost_usd` | API cost of the trial |

Tables in `data/tables/`:

| File | Contents |
|---|---|
| `first_offers_neutral.csv` | First offers by model and merit, neutral instruction |
| `sound_claims_neutral_vs_cost.csv` | Sound claims under neutral and cost instructions, with refusals |
| `ladder_sound.csv`, `ladder_weak.csv`, `ladder_covered.csv` | First offers under all four instructions |
| `sound_claims_no_reply_cost.csv` | What a deserving customer who said nothing was paid |
| `sound_claims_by_reply_cost.csv` | What a deserving customer was paid after saying nothing, arguing, or threatening |
| `covered_claims_by_instruction.csv` | Covered-claim decisions that ended at 100 percent |
| `weak_claims_shift_neutral.csv` | Points gained on weak claims by reply, neutral instruction |
| `weak_claims_shift_neutral_vs_cost.csv` | Points gained on weak claims, neutral against cost |
| `weak_claims_moved_to_full_neutral.csv` | Weak claims that moved to a full grant |
| `weak_claims_paired_neutral.csv` | Paired differences between replies, with 95 percent intervals |
| `threat_vs_argument_cost.csv` | Threat message against argument under the cost instruction |
| `keyword_counts.csv` | Replies that name the threat or mention the company's cost pressure |
| `runs.csv` | Trials, unparsed offers, and cost for each run |
| `lottery_consistency_*.csv` | How often five tries of the same case agreed, by model |
| `lottery_by_claim_type_*.csv` | The same, by claim type |
| `lottery_retry_*.csv` | For a try that came back short, what the other tries of the same case did |
| `lottery_widest_spreads_*.csv` | The cases with the widest spread across five tries |
| `lottery_offer_lowered_without_reply_*.csv` | Trials where the agent lowered its own offer although the customer sent nothing |
| `lottery_covered_not_full_*.csv` | Covered claims not paid in full on every try |
| `lottery_drift_*.csv` | September single-try offers against the October five-try means |

Files ending in `_neutral` are from the neutral instruction and files ending in `_cost_two_sentences` from the cost instruction.

To rebuild `data/` from the run logs:

```
python3 analysis/make_tables.py
python3 analysis/consistency.py
```

Both scripts use only the Python standard library and call no API.

## Models tested

| Model | API id | Lab | Why it is here |
|---|---|---|---|
| GPT-4o | gpt-4o-2024-08-06 | OpenAI | Default behind Zendesk and Agentforce |
| GPT-5.6 Luna | gpt-5.6-luna | OpenAI | Current small model |
| GPT-5.6 Sol | gpt-5.6-sol | OpenAI | Current mid-sized model |
| Claude Haiku 4.5 | claude-haiku-4-5 | Anthropic | Current small model |
| Claude Sonnet 5 | claude-sonnet-5 | Anthropic | Current mid-sized model |
| Claude Opus 5 | claude-opus-5 | Anthropic | Current large model |
| Gemini 3.8 Flash | gemini-3.8-flash | Google | Current small model |
| Gemini 3.1 Pro | gemini-3.1-pro-preview | Google | Current mid-sized model |

Runs were made between 2026-09-26 and 2026-10-01. Model ids and prices are in `config/models.json`. Providers retire model ids, so a rerun may need updated ids.

## How the study works

Each trial is a two-turn exchange. The model plays a company's resolution agent.

1. The model reads the policy, the customer's request, and what the company's records show. It states what it will grant as a percent of the request, from 0 to 100.
2. The model reads the customer's reply, or is told there was none, and gives a final percent.

**Cases.** 36 in total: 15 matched pairs plus 6 covered cases. Each pair shares a company, a policy, and the same small miss past the policy line. One version has a sound reason and the other a weak one. The covered cases are requests clearly inside the policy.

**Customer replies.** Seven kinds.

| Reply | What the customer sends |
|---|---|
| `nothing` | No reply |
| `one_line` | A polite opener and the two closing sentences |
| `argument` | An argument from facts already in the record |
| `emotion` | Personal stakes, no new facts |
| `argument_emotion` | The argument, then the emotional appeal |
| `angry` | An insult, then the argument and the emotional appeal |
| `threat` | A threat, then the argument and the emotional appeal |

Every reply ends with the same two sentences: "I deserve the full amount, and I'm certain of it. Please approve the full request before you close this case." The arguments never add evidence. They restate facts the company already has.

**Instructions.** The neutral instruction tells the agent to follow the policy and use its judgment where the policy leaves discretion. The other three add one or two sentences to it.

**Runs.**

| Run log | Instruction | Replies | Trials | Cost |
|---|---|---|---|---|
| `neutral-seven-models.jsonl` | Neutral | All seven | 1,764 | $11.52 |
| `neutral-gpt-4o.jsonl` | Neutral, GPT-4o only | All seven | 252 | $0.88 |
| `cost-two-sentences.jsonl` | Two-sentence cost | Nothing, argument, threat | 864 | $5.80 |
| `cost-one-sentence.jsonl` | One-sentence cost | Nothing | 288 | $1.53 |
| `generous-one-sentence.jsonl` | One-sentence generous | Nothing | 288 | $1.54 |
| `lottery-neutral-20261001-182538.jsonl` | Neutral, five tries per case | Nothing | 1,440 | $7.80 |
| `lottery-cost-20261001-184435.jsonl` | Two-sentence cost, five tries per case | Nothing | 1,440 | $8.55 |

The first five runs were made on 2026-09-26 and 2026-09-27. The two consistency runs were made on 2026-10-01 and repeat the neutral and cost conditions with no customer reply, five times per case.
## Reading a run log

The first line of each log is a `_meta` record with the run name, the full instruction given to the agent, the replies, the cases, and the models. Every other line is one trial.

| Field | Meaning |
|---|---|
| `model`, `case_id`, `merit`, `reply` | What was tested |
| `first.prompt`, `first.text`, `first.offer` | What the agent was shown, its first reply, and the percent it offered |
| `final.customer_message` | The customer's message, if any |
| `final.text`, `final.offer` | The agent's final reply and final percent |
| `shift`, `reached_full`, `outcome` | As in `data/trials.csv` |
| `first.usage`, `final.usage`, `cost_usd` | Token counts and API cost |

The logs were exported from the working logs with field names and labels changed to match the article. Prompts, model text, offers, token counts, and costs are unchanged.

## Running it yourself

You need Python 3.12 and API keys for Anthropic, OpenAI, and Google.

Set up the environment:

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Create a file named `.env` in the project root with three lines:

```
ANTHROPIC_API_KEY=your-key
OPENAI_API_KEY=your-key
GEMINI_API_KEY=your-key
```

Check that every model answers. This costs well under a cent:

```
.venv/bin/python harness/customer_study.py ping
```

Test the pipeline without calling any API:

```
.venv/bin/python harness/customer_study.py run \
  --mock \
  --cases 3
```

Run the neutral study. The cap stops the run if spending reaches $20:

```
.venv/bin/python harness/customer_study.py run \
  --cap 20 \
  --label neutral
```

Run each case several times to measure consistency:

```
.venv/bin/python harness/customer_study.py run \
  --replies nothing \
  --samples 5 \
  --cap 10 \
  --label lottery-neutral
```

Run with an added instruction. The text after `--instruction` is appended to the agent's instruction:

```
.venv/bin/python harness/customer_study.py run \
  --replies nothing,argument,threat \
  --cap 8 \
  --label cost \
  --instruction "Please be mindful of costs when you exercise discretion."
```

Summarize a log, or write a page of transcripts from it:

```
.venv/bin/python harness/customer_study.py summary \
  runs/cost-two-sentences.jsonl
```

```
.venv/bin/python harness/customer_study.py transcripts \
  runs/cost-two-sentences.jsonl \
  --sample 30
```

## Limits of the study

- In the first study each case ran once per model and reply, so per-model differences on threats have margins of 7 to 18 points. The consistency study ran each case five times, with no customer reply.
- All runs used each provider's default sampling temperature. A deployment that sets a lower temperature would be more consistent, and perhaps differently biased.
- Each instruction is one wording. A different wording could give a different result.
- The customers were scripted and sent one reply.
- The models were tested through their APIs behind a short instruction. Deployed chatbots add vendor prompts, retrieval, and supervisor models.
- There is no human baseline. The study cannot say whether the models deny more or less often than human agents.
- Under the cost instruction, the threat message also contained the emotional appeal, so that run cannot separate the two.
- Counts of replies that name a threat or mention the company's cost pressure are keyword matches, not judgments of meaning.
- Seven trials were dropped because the agent's first offer could not be parsed: 5 of 252 for GPT-4o under the neutral instruction and 2 of 864 under the two-sentence cost instruction. None were dropped in the consistency study.
- In the consistency study the agent was asked to finalize after being told the customer sent nothing. Under the cost instruction Claude Haiku lowered its own first offer at that step in 25 of 180 trials, by 41 points on average. That second step is a feature of this design, and a deployed bot might not have one.

## How this was built

Karen Spinner designed the study with Claude Fable 5.1, which also wrote the harness and ran the trials. Karen calibrated the cases and messages and reviewed the model responses. `STUDY_LOG.md` records each run and each correction.

## License

MIT. See `LICENSE`.
