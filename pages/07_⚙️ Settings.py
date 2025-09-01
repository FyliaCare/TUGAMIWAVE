
import streamlit as st
from src.config import get_settings
import pandas as pd
from src.db import get_engine

st.set_page_config(page_title="Settings — TUGAMIWAVE", page_icon="⚙️", layout="wide")
S = get_settings()
engine = get_engine(S.DB_URL)

st.title("⚙️ Settings")
st.markdown("""
Configure global and corridor-specific settings. Changes are applied instantly and saved to your environment or database.
""")

# --- Global Settings ---
st.subheader("Global Settings")
db_url = st.text_input("Database URL", value=S.DB_URL)
default_currency = st.selectbox("Default Currency", ["GHS", "INR", "MWK"], index=0)
max_transfer = st.number_input("Global Max Transfer Amount", min_value=0.0, value=10000.0, step=100.0)
min_roi = st.number_input("Global Min ROI %", min_value=-100.0, max_value=100.0, value=1.0, step=0.1)

if st.button("Save Global Settings"):
	st.success("Global settings saved (simulated). Please update your .env or config file for persistence.")

# --- Corridor Limits ---
st.subheader("Per-Corridor Limits & Thresholds")
with engine.begin() as conn:
	fees_df = pd.read_sql("select * from fees", conn)
for idx, row in fees_df.iterrows():
	with st.expander(f"{row['corridor']} ({row['currency']})"):
		max_amt = st.number_input(f"Max Transfer for {row['corridor']}", min_value=0.0, value=10000.0, step=100.0, key=f"max_{idx}")
		min_roi_c = st.number_input(f"Min ROI % for {row['corridor']}", min_value=-100.0, max_value=100.0, value=1.0, step=0.1, key=f"roi_{idx}")
		fee_cap = st.number_input(f"Fee Cap for {row['corridor']}", min_value=0.0, value=row['flat'], step=1.0, key=f"fee_{idx}")
		if st.button(f"Save {row['corridor']} Settings", key=f"save_{idx}"):
			st.success(f"Settings for {row['corridor']} saved (simulated). Please update your config for persistence.")

# --- Theme Toggle ---
st.subheader("Theme & Layout")
theme = st.radio("Theme", ["Light", "Dark"], index=0)
layout = st.radio("Layout", ["Wide", "Compact"], index=0)
st.info(f"Theme: {theme}, Layout: {layout} (simulated)")

# --- Show Raw Settings ---
st.subheader("Raw Settings Data")
st.json(S.model_dump())
st.write("Set environment variables or `.env` to change these.")
