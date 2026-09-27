# Test harness

`customer_study.py` runs the study. It sends each case to each model, records the first offer, sends the customer's reply, and records the final offer. Every reply is logged in full.

| Command | What it does |
|---|---|
| `ping` | Sends one short request to each model to confirm the keys and model ids work |
| `run` | Runs the cases and writes a log to `runs/` |
| `summary` | Prints the main tables for one log |
| `transcripts` | Writes a readable page of exchanges from one log |

Add `--mock` to `run` to test the pipeline without calling any API. The main README has full commands.
