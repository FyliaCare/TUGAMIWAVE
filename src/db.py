from sqlalchemy import create_engine, text
import pandas as pd
from pathlib import Path

def get_engine(url: str):
    return create_engine(url, future=True)

SCHEMA_SQL = """
create table if not exists balances(
    id integer primary key autoincrement,
    bank text not null,
    currency text not null,
    amount real not null default 0
);
create table if not exists rates(
    id integer primary key autoincrement,
    pair text not null,
    rate real not null,
    as_of text not null
);
create table if not exists fees(
    id integer primary key autoincrement,
    corridor text not null,
    pct real not null default 0,
    flat real not null default 0,
    currency text not null
);
create table if not exists transfers(
    id integer primary key autoincrement,
    ts text not null,
    route text not null,
    start_ccy text not null,
    amount real not null,
    end_ccy text not null,
    end_amount real not null,
    roi real not null,
    pnl real not null,
    notes text
);
"""

def ensure_db(engine):
    with engine.begin() as conn:
        for stmt in SCHEMA_SQL.strip().split(";"):
            if stmt.strip():
                conn.execute(text(stmt))

def load_seed_if_empty(engine):
    with engine.begin() as conn:
        n = conn.execute(text("select count(*) from rates")).scalar()
        if n == 0:
            import pandas as pd, datetime as dt
            from pathlib import Path
            seed_rates = pd.read_csv(Path("data/seed_rates.csv"))
            seed_rates.to_sql("rates", conn, if_exists="append", index=False)
        n = conn.execute(text("select count(*) from fees")).scalar()
        if n == 0:
            pd.read_csv(Path("data/seed_fees.csv")).to_sql("fees", conn, if_exists="append", index=False)
        n = conn.execute(text("select count(*) from balances")).scalar()
        if n == 0:
            pd.read_csv(Path("data/seed_balances.csv")).to_sql("balances", conn, if_exists="append", index=False)
        n = conn.execute(text("select count(*) from transfers")).scalar()
        if n == 0:
            pd.read_csv(Path("data/seed_transfers.csv")).to_sql("transfers", conn, if_exists="append", index=False)

def kpis(engine):
    with engine.begin() as conn:
        transfers = conn.execute(text("select count(*) from transfers")).scalar()
        realized = conn.execute(text("select coalesce(sum(pnl),0) from transfers where end_ccy = start_ccy")).scalar()
        avg_roi = conn.execute(text("select coalesce(avg(roi),0) from transfers")).scalar()
        exposure = conn.execute(text("select coalesce(sum(case when currency='GHS' then amount else 0 end),0) from balances")).scalar()
        return {"transfers": transfers, "realized_pnl_ghs": realized, "avg_roi": avg_roi, "open_exposure_ghs": exposure}

def balances_df(engine):
    return pd.read_sql("select bank, currency, amount from balances order by bank, currency", engine)

def transfers_df(engine):
    return pd.read_sql("select * from transfers order by ts", engine)
