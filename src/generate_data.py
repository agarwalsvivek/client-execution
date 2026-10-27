"""
STEP 1 - Generate fake market data.

Run:  python generate_data.py

Creates two CSV files in ./data:
  quotes_<date>.csv  -> NBBO snapshots (best bid / best ask across all exchanges)
  fills_<date>.csv   -> client order executions (some rows are deliberately bad)

JS analogy: this is like a seed script you'd run with `node seed.js`.
"""
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# Starting mid prices. Plain dict literal, same as a JS object literal.
SYMBOLS = {"AAPL": 190.00, "MSFT": 410.00, "TSLA": 250.00}
CLIENTS = ["BRK-ALPHA", "BRK-BETA", "BRK-GAMMA"]  # broker-dealers routing retail orders


def generate_quotes(trade_date: str, rng: random.Random) -> dict[str, list[dict]]:
    """Random-walk an NBBO for each symbol, one snapshot every 5 seconds."""
    start = datetime.fromisoformat(f"{trade_date}T09:30:00")
    quotes: dict[str, list[dict]] = {}

    for symbol, mid in SYMBOLS.items():  # .items() ~ Object.entries()
        rows = []
        for i in range(0, 6 * 60 * 60, 5):  # 6 hours in 5-second steps
            mid += rng.gauss(0, 0.02)
            spread = rng.choice([0.01, 0.02, 0.03, 0.05])
            rows.append({
                "symbol": symbol,
                "quote_ts": (start + timedelta(seconds=i)).isoformat(),
                "bid": round(mid - spread / 2, 4),
                "ask": round(mid + spread / 2, 4),
            })
        quotes[symbol] = rows
    return quotes


def generate_fills(quotes: dict[str, list[dict]], n_fills: int, rng: random.Random) -> list[dict]:
    fills = []
    for n in range(n_fills):
        symbol = rng.choice(list(SYMBOLS))
        q = rng.choice(quotes[symbol])                 # the quote in force at execution
        exec_ts = datetime.fromisoformat(q["quote_ts"]) + timedelta(seconds=rng.uniform(0, 4.9))
        side = rng.choice(["BUY", "SELL"])
        spread = q["ask"] - q["bid"]

        # Market maker gives "price improvement": better than the NBBO.
        # 80% of fills get some improvement, the rest fill exactly at the quote.
        improvement = rng.uniform(0, spread / 2) if rng.random() < 0.8 else 0.0
        price = q["ask"] - improvement if side == "BUY" else q["bid"] + improvement

        fills.append({
            "fill_id": f"F{n:06d}",                    # f-string ~ JS template literal
            "client_id": rng.choice(CLIENTS),
            "symbol": symbol,
            "side": side,
            "qty": rng.choice([1, 5, 10, 25, 50, 100, 200]),
            "price": round(price, 4),
            "exec_ts": exec_ts.isoformat(timespec="milliseconds"),
        })
    return fills


def inject_bad_rows(fills: list[dict], rng: random.Random) -> None:
    """Real feeds are dirty. Mutates the list in place (like Array.prototype.push)."""
    fills[3]["qty"] = "-10"          # negative quantity
    fills[7]["symbol"] = ""          # missing symbol
    fills[11]["price"] = "N/A"       # not a number
    fills[13]["price"] = "nan"       # sneaky: float("nan") parses fine!
    fills[17]["side"] = "BUYY"       # typo from upstream
    fills.append(dict(fills[20]))    # duplicate fill_id (upstream re-sent a message)
    rng.shuffle(fills)


def write_csv(path: Path, rows: list[dict]) -> None:
    # `with` = context manager: the file is closed automatically, even on error.
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def generate(trade_date: str = "2026-10-26", n_fills: int = 5_000, seed: int = 42) -> None:
    rng = random.Random(seed)  # seeded -> same data every run (reproducible)
    DATA_DIR.mkdir(exist_ok=True)

    quotes = generate_quotes(trade_date, rng)
    fills = generate_fills(quotes, n_fills, rng)
    inject_bad_rows(fills, rng)

    all_quotes = [row for rows in quotes.values() for row in rows]  # nested comprehension = flatMap
    write_csv(DATA_DIR / f"quotes_{trade_date}.csv", all_quotes)
    write_csv(DATA_DIR / f"fills_{trade_date}.csv", fills)
    print(f"Wrote {len(all_quotes):,} quotes and {len(fills):,} fills to {DATA_DIR}/")


# Only runs when executed directly, not when imported.
# JS analogy: `if (require.main === module) { ... }`
if __name__ == "__main__":
    generate()
