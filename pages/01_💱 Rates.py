import streamlit as st, pandas as pd
from src.db import get_engine
from src.config import get_settings
from src.fx import load_rates

st.set_page_config(page_title="Rates — TUGAMIWAVE", page_icon="💱", layout="wide")
S = get_settings()
engine = get_engine(S.DB_URL)

st.title("💱 Rates")
st.caption("Manage corridor rates; plug real feeds later")

df = load_rates(engine)
st.dataframe(df, use_container_width=True)
st.download_button("Download rates CSV", df.to_csv(index=False).encode(), "rates_export.csv", "text/csv")
