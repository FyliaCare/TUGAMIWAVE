import pandas as pd
from sqlalchemy import text
import itertools
from datetime import datetime
from math import prod

# Supported pairs in seeds: GHS/INR, INR/MWK, MWK/GHS (direct & inverse)
def load_rates(engine):
    q = "select pair, rate, as_of from rates order by as_of"
    return pd.read_sql(q, engine)

def latest_rate_dict(engine):
    # return dict like {('GHS','INR'): 8, ('INR','MWK'):53, ('MWK','GHS'):1/155.5, ...}
    with engine.begin() as conn:
        df = pd.read_sql("select pair, rate, max(as_of) as as_of from rates group by pair", conn)
    rmap = {}
    for _, row in df.iterrows():
        a,b = row["pair"].split("/")
        rmap[(a,b)] = float(row["rate"])
        rmap[(b,a)] = 1.0/float(row["rate"])
    return rmap

def fee_for(engine, corridor: str):
    with engine.begin() as conn:
        f = pd.read_sql("select pct, flat, currency from fees where corridor = :c", conn, params={"c":corridor})
    if f.empty:
        return {"pct":0.0,"flat":0.0,"currency":corridor.split('→')[-1]}
    row = f.iloc[0]
    return {"pct": float(row["pct"]), "flat": float(row["flat"]), "currency": row["currency"]}

def apply_fee(amount: float, fee):
    net = amount * (1 - fee["pct"]) - fee["flat"]
    return max(net, 0.0)

def compute_cycle(engine, amount: float, start_ccy: str, path: str, include_fees: bool=True):
    # path like "GHS→INR→MWK→GHS"
    legs = path.split("→")
    assert legs[0]==start_ccy
    rates = latest_rate_dict(engine)
    amt = amount
    pnl_fees = 0.0
    steps = []
    for i in range(len(legs)-1):
        a,b = legs[i], legs[i+1]
        r = rates[(a,b)]
        prev_amt = amt
        amt = amt * r
        step = {
            "desc": f"Convert {prev_amt:.2f} {a} to {amt:.2f} {b} at rate {r:.4f}",
            "amount": amt,
            "currency": b
        }
        if include_fees:
            corridor = f"{a}→{b}"
            fee = fee_for(engine, corridor)
            gross = amt
            net_amt = apply_fee(amt, fee)
            fee_amt = gross - net_amt
            pnl_fees += fee_amt
            step["fee"] = fee_amt
            step["desc"] += f" (fee: {fee_amt:.2f} {b})"
            amt = net_amt
            step["amount"] = amt
        steps.append(step)
    end_amt = amt
    roi = (end_amt - amount)/amount
    res = {
        "start": start_ccy,
        "end": legs[-1],
        "path": path,
        "final_amount": end_amt,
        "final_currency": legs[-1],
        "total_fees": pnl_fees,
        "profit": end_amt-amount,
        "steps": steps
    }
    return res

def currency_graph(engine):
    R = latest_rate_dict(engine)
    edges = [{"from":a, "to":b, "rate":r} for (a,b),r in R.items() if a in ("GHS","INR","MWK") and b in ("GHS","INR","MWK")]
    return edges

def arbitrage_cycles(engine, threshold: float=0.01):
    CCY = ["GHS","INR","MWK"]
    rates = latest_rate_dict(engine)
    cycles = []
    for start in CCY:
        for path in itertools.permutations([c for c in CCY if c!=start], 2):
            legs = [start, *path, start]
            label = "→".join(legs)
            amt = 1.0
            fees_total = 0.0
            for i in range(len(legs)-1):
                a,b = legs[i], legs[i+1]
                r = rates[(a,b)]
                amt *= r
                fee = fee_for(engine, f"{a}→{b}")
                before = amt
                amt = apply_fee(amt, fee)
                fees_total += (before-amt)
            roi = amt - 1.0
            if roi >= threshold:
                cycles.append({"cycle": label, "roi": roi, "net_multiplier": amt, "fees": fees_total})
    cycles.sort(key=lambda x: x["roi"], reverse=True)
    return cycles
