# Analysis

`make_tables.py` reads the logs in `runs/` and rebuilds `data/trials.csv` and the first-study tables in `data/tables/`. `consistency.py` reads the two five-try runs and writes the `lottery_*` tables. Both use only the Python standard library and call no API.

```
python3 analysis/make_tables.py
python3 analysis/consistency.py
```

The two keyword lists used to count replies that name a threat or mention cost pressure are at the top of the script.
