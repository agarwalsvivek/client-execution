1. Setup (one time)
   python3 -m venv .venv
   source .venv/bin/activate
   pip install pandas numpy pytest
   python generate_data.py

• NumPy is a Python library for high-speed, multi-dimensional array and matrix math.
• Pandas is a data analysis library built on NumPy that uses labeled spreadsheets (DataFrames) to clean and manipulate tabular data.
• Pytest is a Python testing framework that makes writing and running simple function-based unit tests eas

# Client Execution-Quality Pipeline: a hands-on Python tutorial

**Scenario (illustrative):** a market maker receives retail orders from broker-dealer clients.
Each day, its client platform shows every broker how much **price improvement** their customers
got compared with the NBBO (the best bid and best ask across all exchanges). Regulators also require
execution-quality disclosure (SEC Rule 605; worth verifying current details if it comes up).

> This is a realistic example of the domain, **not** a description of any real firm's internal systems.

```
fills.csv ─┐
           ├─► EXTRACT ─► TRANSFORM ─► QUALITY GATE ─► ENRICH (async) ─► LOAD (upsert) ─► warehouse.db
quotes.csv ┘   validate   as-of join     fail = don't    client tiers      idempotent
               dead-letter  aggregate       publish
```

## Setup (5 min)

```bash
python3 -m venv .venv            # like a project-local node_modules
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install pandas numpy pytest  # like npm install
```

**How to learn with this:** for each step, _type_ the file yourself (don't copy-paste), run it, then do the
"Break it" exercise. Use the provided file to check your work.

---

## Step 1 · `generate_data.py`: fake market data (20 min)

`python generate_data.py`

Learn: dicts and lists, f-strings, comprehensions, `with` for files, `if __name__ == "__main__"`.

**Break it:** change `seed=42` to `seed=7` and rerun. Then change it back. Why do pipelines want reproducible test data?

## Step 2 · `extract.py`: stream, validate, dead-letter (40 min)

`python extract.py` → 4,995 valid, 6 rejected, each with a reason.

Learn: **generators** (`yield`), `@dataclass`, custom exceptions, `raise ... from e`, sets for de-duplication.

**Break it:**

1. Delete the `math.isfinite` check and rerun. The `"nan"` row now gets through silently. This is a classic data bug.
2. In a REPL: `rows = read_rows(Path("data/fills_2026-10-26.csv"))`, then `next(rows)` a few times. Nothing reads the file until you ask, which is laziness in action.

## Step 3 · `transform.py`: pandas (60 min, the most important step)

`python transform.py` → 9 rows: one per client and symbol.

Learn: DataFrames, **vectorized** math with `np.where`, `merge_asof` (the as-of join on time that finance uses everywhere), `groupby().agg()`.

**Break it:**

1. Remove `.sort_values(...)` in `attach_nbbo`. Read the traceback **bottom-up**: the last line is the actual error.
2. Change `tolerance` to `"1s"`. Now some fills have no fresh quote. Look at the `unmatched` count.
3. Rewrite `compute_price_improvement` with a `for _, row in df.iterrows()` loop and time both versions. The difference explains why vectorizing matters so much.

## Step 4 · `quality.py`: the gate (20 min)

`python quality.py` → `PASS`

Learn: checks run _between_ transform and load. Bad data never reaches clients.

**Break it:** lower the reject-rate threshold to `0.0001` and run `python run_pipeline.py`. It exits with code `2`, logs the reason, and loads nothing.

## Step 5 · `load.py`: idempotent upsert (30 min)

Run `python load.py` **twice**. You'll get 9 rows both times.

Learn: `INSERT ... ON CONFLICT DO UPDATE`, parameterized SQL, transactions with `with conn:`, and the gotcha that it doesn't close the connection (use `closing()` for that).

**Break it:** replace the `UPSERT` with a plain `INSERT` and drop the `PRIMARY KEY`. Run twice: you get 18 rows. That's the "pipeline ran twice and duplicated data" interview question.

Inspect it: `sqlite3 data/warehouse.db "SELECT * FROM pipeline_runs;"`

## Step 6 · `enrich.py`: asyncio vs Node (30 min)

`python enrich.py`

```
gather (Promise.all)             0.50s
blocking call in async (BUG)     1.50s   ← time.sleep froze the event loop
asyncio.to_thread fix            0.50s
```

Learn: `async`/`await`, `asyncio.gather`, why one sync call inside `async def` serializes everything, and `asyncio.to_thread` as the escape hatch.

## Step 7 · `run_pipeline.py`: orchestrate (20 min)

`python run_pipeline.py --date 2026-10-26`

Learn: `argparse` (CLI args), `logging`, exit codes for orchestrators, recording each run in a table.

**Profile it:** `python -m cProfile -s cumtime run_pipeline.py | head -30`. Find where the time goes.

## Step 8 · `tests/test_pipeline.py`: pytest (20 min)

`python -m pytest -v` → 11 passed

Learn: plain `assert`, fixtures injected by name (`tmp_path`), `@pytest.mark.parametrize` (like Jest's `test.each`), and `pytest.approx` for floats.

---

## Interview talking points this project gives you

- **Idempotency:** "Loads are upserts keyed on the business key, so retries and backfills are safe."
- **Dead-lettering:** "Bad rows are quarantined with a reason, never silently dropped."
- **Quality gate:** "We'd rather publish late than wrong."
- **As-of joins:** "Each fill is matched to the quote in force at execution time, with a staleness tolerance."
- **Performance:** "Stream with generators, vectorize in pandas, and never block the event loop."
- **Money:** "In production I'd use `Decimal` or integer ticks, not floats."

## Where this would go in production (talk about it, don't build it)

Airflow or Dagster would schedule `run_pipeline.py` per date. CSVs would be Parquet in S3 or GCS. SQLite would be
Postgres, Snowflake, or a similar warehouse. Fills would arrive via Kafka for intraday views. These are generic
examples: the job description didn't name a stack, so ask the interviewer what they use.
