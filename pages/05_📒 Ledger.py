import streamlit as st, pandas as pd
from sqlalchemy import text
from src.config import get_settings
from src.db import get_engine

st.set_page_config(page_title="Ledger — TUGAMIWAVE", page_icon="📒", layout="wide")
S = get_settings(); engine = get_engine(S.DB_URL)

st.title("📒 Ledger & Transfers")
with engine.begin() as conn:
    df = pd.read_sql("select * from transfers order by ts desc", conn)
st.dataframe(df, use_container_width=True)

st.download_button("Download ledger CSV", df.to_csv(index=False).encode(), "ledger.csv", "text/csv")
