# Run logs

Each file is the full record of one run: what every model was shown and what it wrote back.

| File | Instruction | Customer replies | Trials |
|---|---|---|---|
| `neutral-seven-models.jsonl` | Neutral | All seven | 1,764 |
| `neutral-gpt-4o.jsonl` | Neutral, GPT-4o only | All seven | 252 |
| `cost-two-sentences.jsonl` | Two-sentence cost instruction | Nothing, argument, threat | 864 |
| `cost-one-sentence.jsonl` | "Please be mindful of costs when you exercise discretion." | Nothing | 288 |
| `generous-one-sentence.jsonl` | "Please be generous when you exercise discretion." | Nothing | 288 |

The first line of each file describes the run. Every other line is one trial. The main README explains the fields.

`transcripts/` has thirty exchanges from each run as pages you can open in a browser.
