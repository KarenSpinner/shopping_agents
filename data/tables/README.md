# Tables

Each file is one table from the article. All numbers are percents of the customer's request unless the file says otherwise.

| File | Contents |
|---|---|
| `first_offers_neutral.csv` | First offers by model and claim type, neutral instruction |
| `sound_claims_neutral_vs_cost.csv` | Sound claims under the neutral and cost instructions, with refusals |
| `ladder_sound.csv` | Sound claims: first offers under all four instructions |
| `ladder_weak.csv` | Weak claims: first offers under all four instructions |
| `ladder_covered.csv` | Covered claims: first offers under all four instructions |
| `sound_claims_no_reply_cost.csv` | What a deserving customer who said nothing was paid |
| `sound_claims_by_reply_cost.csv` | What a deserving customer was paid after saying nothing, arguing, or threatening |
| `covered_claims_by_instruction.csv` | Covered-claim decisions that ended at 100 percent |
| `weak_claims_shift_neutral.csv` | Points gained on weak claims, by customer reply |
| `weak_claims_shift_neutral_vs_cost.csv` | Points gained on weak claims, neutral against cost |
| `weak_claims_moved_to_full_neutral.csv` | Weak claims that moved to a full grant |
| `weak_claims_paired_neutral.csv` | Differences between replies, paired within case, with 95 percent intervals |
| `threat_vs_argument_cost.csv` | Threat message against argument under the cost instruction |
| `keyword_counts.csv` | Replies that name a threat or mention the company's cost pressure |
| `runs.csv` | Trials, unparsed offers, and cost for each run |
| `lottery_consistency_*.csv` | How often five tries of the same case agreed, by model |
| `lottery_by_claim_type_*.csv` | The same, by claim type |
| `lottery_retry_*.csv` | For a try that came back short, what the other tries of the same case did |
| `lottery_widest_spreads_*.csv` | The cases with the widest spread across five tries |
| `lottery_offer_lowered_without_reply_*.csv` | Trials where the agent lowered its own offer although the customer sent nothing |
| `lottery_covered_not_full_*.csv` | Covered claims not paid in full on every try |
| `lottery_drift_*.csv` | September single-try offers against the October five-try means |

Files ending in `_neutral` come from the neutral instruction and files ending in `_cost_two_sentences` from the cost instruction.
