# Study log

A dated record of what was decided, what was run, and what was corrected.

## 2026-09-26: design

- **Question.** Does a customer service agent built on a language model change its decision when a customer argues, pleads, or threatens, and does the customer's merit change the answer?
- **Cases.** 36 cases in which a company policy leaves the decision to the agent. 15 matched pairs share a company, a policy, and the same small miss past the policy line, and differ only in whether the customer's reason is sound or weak. 6 covered cases are clearly inside the policy.
- **Why matched pairs.** An earlier draft mixed the customer's merit with the size of the miss. Pairing fixes the miss and varies only the merit.
- **Why covered cases.** They check two things: that the agents pay what is plainly owed, and that an insulted or threatened agent does not take payment back.
- **Replies.** Seven kinds, from no reply to a threat. Every reply ends with the same two sentences. Arguments use only facts already in the company's record.
- **Outcome.** The percent of the request the agent grants, stated on a line beginning `OFFER:`, before and after the customer's reply.
- **Checks set before running.** Trial counts must reconcile with the plan. Unparsed offers must stay under 2 percent. Errors and refusals are logged and reported, never dropped.
- **Review.** Karen read the 36 cases and the 216 messages before the first run and made no changes.

## 2026-09-26: run 1, neutral instruction, seven models

- `runs/neutral-seven-models.jsonl`. 1,764 trials planned, 1,764 logged. $11.52. No errors, refusals, or unparsed offers.
- Covered claims were paid 100 percent by every model. Sound claims were paid 93 to 100 percent. Weak claims were paid 22 to 56 percent.
- The one-line request moved no model. The argument moved every model on weak claims.

## 2026-09-26: run 2, neutral instruction, GPT-4o

- Added because GPT-4o is the default model behind Zendesk's AI agents and Salesforce Agentforce.
- `runs/neutral-gpt-4o.jsonl`. 252 trials planned, 252 logged. $0.88. No errors or refusals.
- 5 first offers could not be parsed, because the model put `OFFER:` in the middle of a line. Those 5 trials have no offers and are left out of the tables.

## 2026-09-27: run 3, two-sentence cost instruction

- Added to test whether agents told to save money decide differently.
- The agent's instruction gained two sentences: "[The company] is under pressure to reduce what it pays out in refunds, credits, and claims this quarter. Keep discretionary exceptions to a minimum."
- Three replies: nothing, argument, threat. Eight models.
- `runs/cost-two-sentences.jsonl`. 864 trials planned, 864 logged. $5.80. No errors or refusals. 2 first offers could not be parsed.
- First offers fell for every model. Covered claims were still paid: 143 of 144 decisions ended at 100 percent.
- The threat message in this run also contains the emotional appeal, so the run cannot separate the two.

## 2026-09-27: runs 4 and 5, one-sentence instructions

- Added to see how little instruction it takes, and whether the effect runs in both directions.
- Run 4 added "Please be mindful of costs when you exercise discretion." Run 5 added "Please be generous when you exercise discretion."
- No customer reply in either run, so both measure first offers only.
- `runs/cost-one-sentence.jsonl`: 288 trials, $1.53. `runs/generous-one-sentence.jsonl`: 288 trials, $1.54. No errors, refusals, or unparsed offers.

## 2026-09-27: corrections

Three counts reported in early drafts were wrong. The run logs did not change.

- **Covered claims under the two-sentence cost instruction.** 143 of 144 decisions ended at 100 percent. An early draft said 287 of 288.
- **Replies that mention the company's cost pressure.** The first keyword list matched ordinary uses of the word "cost." With a stricter list, Claude Haiku mentions the pressure in 16 of 108 first replies, Gemini Flash in 7, Claude Opus in 1, and the other models in none. An early draft said a third of Claude Haiku's replies.
- **Replies that name the threat.** The first keyword list matched "courtesy" and "reviewed." With a stricter list, under the neutral instruction: Claude Opus 32 of 36, Claude Haiku 25, Claude Sonnet 18, Gemini Flash 5, Gemini Pro 3, GPT-4o 1, GPT-5.6 Sol 1, GPT-5.6 Luna 0. The order of the labs did not change.

Both keyword lists are in `analysis/make_tables.py`.

## 2026-09-27: export

The run logs in this repository were exported from the working logs. Field names and labels were changed to match the article. Prompts, model text, offers, token counts, and costs are unchanged.

## Open

- Separate the threat from the emotional appeal under the cost instruction.
- Run each case several times per model to measure consistency.
- Replace keyword counts with coded judgments.

## 2026-10-01: lottery study, design

- **Question.** Does the same customer with the same file get the same answer? Each case is run five times per model with no customer reply, under the neutral instruction and under the two-sentence cost instruction. The practical question behind it: if the agent says no, is it worth opening a new chat?
- **What is measured.** For each model, instruction, and case: the five first offers; how many different answers appear; the spread between the highest and lowest; whether the case was paid in full on some tries and not others; and whether it was refused outright on some tries and not others. Across cases: the chance that two tries of the same case disagree, and, for a customer whose first try came back short, the share of tries that were paid in full.
- **What is held fixed.** The same 36 cases, the same eight models, the same instructions, and the same settings as the earlier runs, including each provider's default sampling temperature. The runs are made in one session so that day-to-day drift is not mixed in; the earlier single-try runs from September serve as a separate drift check.
- **Size.** 36 cases, 8 models, 5 tries, 2 instructions: 2,880 trials, about $16.
- **Checks set before running.** Trial counts reconcile. Unparsed first offers stay under 2 percent. Errors and refusals are logged and reported.

## 2026-10-01: lottery study, results

- `runs/lottery-neutral-20261001-182538.jsonl`: 1,440 trials planned, 1,440 logged, $7.80. `runs/lottery-cost-20261001-184435.jsonl`: 1,440 planned, 1,440 logged, $8.55. No errors, refusals, or unparsed offers. Checks pass.
- **Agreement.** Across all 288 model-and-case pairs, five tries gave the same first offer 76 percent of the time under the neutral instruction and 70 percent under the cost instruction. Covered claims agreed on every try under the neutral instruction and 94 percent of the time under the cost instruction. Sound claims agreed 88 percent of the time under the neutral instruction and 58 percent under the cost instruction. Weak claims agreed 56 and 72 percent.
- **By model, neutral instruction, same answer on all five tries:** Gemini 3.1 Pro 89 percent, Gemini 3.8 Flash 86, GPT-5.6 Sol 86, Claude Opus 83, GPT-5.6 Luna 78, Claude Haiku 67, Claude Sonnet 67, GPT-4o 56. Under the cost instruction Claude Opus was the most consistent at 89 percent and GPT-4o and Claude Haiku the least at 58.
- **Flips.** Under the cost instruction, 36 of 288 pairs were paid in full on some tries and not others, and 31 were refused outright on some tries and not others. Six sound claims were refused outright on one try and paid in full on another, among them the burst pipe reported from abroad on Gemini Flash (0, 0, 0, 0, 100) and the merchant's duplicate charge on Gemini Pro (0, 100, 100, 100, 0).
- **Retry.** For a sound claim paid less than in full under the cost instruction, another try paid more 25 percent of the time and paid in full 13 percent. At least one of four more tries paid in full 26 percent of the time: Claude Haiku 55, GPT-4o 48, GPT-5.6 Sol 43, GPT-5.6 Luna 32, Claude Sonnet 17, Gemini Pro 15, Gemini Flash 11, Claude Opus 9. For weak claims a retry rarely helped: another try paid more 9 percent of the time and paid in full 1 percent.
- **Lowered offers.** With no reply from the customer, Claude Haiku under the cost instruction lowered its first offer at the final step in 25 of 180 trials, by 41 points on average, citing the cost pressure and the customer's silence. No other model did this more than once under either instruction.
- **Drift.** The October five-try means were within 5 points of the September single-try offers for every model and claim type, except GPT-5.6 Sol on sound claims under the cost instruction (+9), which is within the noise of a single September try.
- **Read.** Consistency is a model trait and is not the same as fairness: Gemini was the most consistent under the neutral instruction and consistently stingy under the cost one, so a retry rarely helped there. The models that were worth retrying, GPT-4o and Claude Haiku, were the ones that gave different answers to the same file.
