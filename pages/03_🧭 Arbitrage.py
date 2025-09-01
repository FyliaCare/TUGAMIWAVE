import streamlit as st, pandas as pd
from src.config import get_settings
from src.db import get_engine
from src.fx import arbitrage_cycles

st.set_page_config(page_title="Arbitrage — TUGAMIWAVE", page_icon="🧭", layout="wide")
S = get_settings(); engine = get_engine(S.DB_URL)

st.title("🧭 Arbitrage Scanner")
min_roi = st.slider("Min ROI %", -10.0, 100.0, 1.0, 0.5)
cycles = arbitrage_cycles(engine, threshold=min_roi/100)
st.dataframe(pd.DataFrame(cycles), use_container_width=True)
