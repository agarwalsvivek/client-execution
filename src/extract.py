import csv
import math 
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

@dataclass(frozen=True)
class Fill:
    fill_is:str
    client_id:str
    symbol:str
    side:str
    qty:int
    price:float
    exec_ts:datetime

class ValidationError(Exception):
    pass

def read_rows(path):
    with path.open(newline="") as f:
        yield from csv.DictReader(f)

def parse_fill(row):
    good = []
    dead = []
    seen_ids = set()

    try:
        qty = int(row["qty"])
        price = float(row["price"])
        exec_ts = datetime.fromisoformat(row["exec_ts"])
    except (KeyError, ValueError) as e:
        raise ValidationError(f"unparsable field: {e}") from e

    if not row["symbol"]:
        raise ValidationError("missing symbol")
    if row["side"] not in {"BUY", "SELL"}:
        raise ValidationError(f" bad side {row["side"]!r}")
    if qty <= 0:
        raise ValidationError(f"non positive qty {qty}")
    if not math.isfinite(price) or price <= 0:
        raise ValidationError(f"bad price {row["price"]}")

    return Fill(row["fill_id"], row["client_id"], row["symbol"], row["side"], qty, price, exec_ts)



if __name__ == "__main__":
    # good = {"fill_id": "F1", "client_id": "BRK-ALPHA", "symbol": "AAPL", "side": "BUY",
    #         "qty": "100", "price": "190.01", "exec_ts": "2026-10-26T10:00:00.000"}
    # print(parse_fill(good))

    # for bad in [{**good, "qty": "-5"}, {**good, "price": "nan"}, {**good, "side": "HOLD"}, {**good, "symbol": ""}]:
    #     try:
    #         parse_fill(bad)
    #     except ValidationError as e:
    #         print("rejected:", e)

    
    rows = read_rows(Path("data/fills_2026-10-26.csv"))
    print(type(rows))
    print(next(rows))
    print(next(rows))