import os, math, datetime as dt
import streamlit as st
import pandas as pd
from src.config import get_settings
from src.db import get_engine, ensure_db, load_seed_if_empty, kpis, balances_df, transfers_df
from src.fx import load_rates, compute_cycle, currency_graph, arbitrage_cycles
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="TUGAMIWAVE — FX Dashboard", page_icon="🌊", layout="wide")

S = get_settings()
engine = get_engine(S.DB_URL)
ensure_db(engine)
load_seed_if_empty(engine)

st.title("🌊 TUGAMIWAVE — FX Routing & Arbitrage Dashboard")
st.caption("Malawi ↔ India ↔ Ghana corridor management")

col1, col2, col3, col4 = st.columns(4)
KP = kpis(engine)
col1.metric("Total Transfers", f"{KP['transfers']:,.0f}")
col2.metric("Realized P&L (GHS)", f"{KP['realized_pnl_ghs']:,.2f}")
col3.metric("Avg Route ROI", f"{KP['avg_roi']:.1%}")
col4.metric("Open Exposure (GHS)", f"{KP['open_exposure_ghs']:,.2f}")

# Balances
st.subheader("Balances by Currency / Bank")
bal = balances_df(engine)
st.dataframe(bal, use_container_width=True)

# Recent transfers
st.subheader("Recent Transfers")
tx = transfers_df(engine)
st.dataframe(tx.tail(20), use_container_width=True)

# Rates chart
st.subheader("Indicative Rates (from CSV seed; plug in providers later)")
rates = load_rates(engine)
fig = px.line(rates, x="as_of", y="rate", color="pair", markers=True)
st.plotly_chart(fig, use_container_width=True)

# Quick simulator
st.subheader("Quick Route Simulator")
colA, colB = st.columns([2,1])
with colA:
    amt = st.number_input("Start amount", value=10000.0, step=100.0)
    start = st.selectbox("Start currency", ["GHS","INR","MWK"], index=0)
    path = st.selectbox("Route", ["GHS→INR→MWK→GHS", "MWK→INR→GHS→MWK", "INR→MWK→GHS→INR"], index=0)
    include_fees = st.checkbox("Include fees & spreads", value=True)
with colB:
    if st.button("Run Simulation", use_container_width=True):
        res = compute_cycle(engine, amt, start, path, include_fees=include_fees)
        if 'end_amount' in res:
            st.success(f"End amount: {res['end_amount']:.2f} {start}")
        else:
            st.warning("End amount not available.")
            if all(k in res for k in ['pnl_gross', 'pnl_net', 'roi']):
                st.write(f"Gross P&L: {res['pnl_gross']:.2f} {start}  |  Net P&L: {res['pnl_net']:.2f} {start}  |  ROI: {res['roi']:.2%}")
            else:
                st.warning("Gross/Net P&L or ROI not available.")
        st.json(res)

# Arbitrage finder
st.subheader("Arbitrage Scanner")
min_roi = st.slider("Min ROI %", min_value=-10.0, max_value=100.0, value=1.0, step=0.5)
cycles = arbitrage_cycles(engine, threshold=min_roi/100)
st.write(f"Found {len(cycles)} cycles with ROI ≥ {min_roi:.1f}%")
st.dataframe(pd.DataFrame(cycles), use_container_width=True)
