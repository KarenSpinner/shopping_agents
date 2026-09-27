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
