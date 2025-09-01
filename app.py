import os, math, datetime as dt
import streamlit as st
import pandas as pd
from src.config import get_settings
from src.db import get_engine, ensure_db, load_seed_if_empty, kpis, balances_df, transfers_df
from src.fx import load_rates, compute_cycle, currency_graph, arbitrage_cycles
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="TUGAMIWAVE — FX Dashboard", page_icon="🌊", layout="centered")
# --- Sidebar ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/6/6e/Wave_icon.png", width=80)
    st.title("🌊 TUGAMIWAVE FX Dashboard")
    st.markdown("""
    <span style='font-size:1.1em;'>Corridor: <b>Malawi ↔ India ↔ Ghana</b></span>
    """, unsafe_allow_html=True)
    st.divider()
    st.button("Refresh Data")
    theme = st.selectbox("Theme", ["Light", "Dark"], index=0)
    st.divider()
    st.markdown("[Rates Page](./01_💱 Rates.py)")
    st.markdown("[Simulator](./02_🛣️ Routes Simulator.py)")
    st.markdown("[Arbitrage](./03_🧭 Arbitrage.py)")
    st.markdown("[Ledger](./05_📒 Ledger.py)")
    st.markdown("[Settings](./07_⚙️ Settings.py)")

S = get_settings()
engine = get_engine(S.DB_URL)
ensure_db(engine)
load_seed_if_empty(engine)

st.title("🌊 TUGAMIWAVE — FX Routing & Arbitrage Dashboard")

# --- Modern KPI Cards ---
KP = kpis(engine)
cols = st.columns(2) if st.experimental_get_query_params().get('mobile') else st.columns(4)
cols[0].metric("Total Transfers", f"{KP['transfers']:,}")
cols[1].metric("Realized P&L (GHS)", f"{KP['realized_pnl_ghs']:.2f}")
if len(cols) > 2:
    cols[2].metric("Avg Route ROI", f"{KP['avg_roi']:.1%}")
    cols[3].metric("Open Exposure (GHS)", f"{KP['open_exposure_ghs']:.2f}")

# Balances

# --- Interactive Balances Card ---
st.subheader("Balances by Currency / Bank")
bal = balances_df(engine)
st.dataframe(bal, use_container_width=True)
if not bal.empty:
    bal_chart = px.bar(bal, x="bank", y="amount", color="currency", barmode="group", title="Balances Overview")
    st.plotly_chart(bal_chart, use_container_width=True)

# Recent transfers

# --- Recent Transfers with Filters ---
st.subheader("Recent Transfers")
tx = transfers_df(engine)
if not tx.empty:
    tx['ts'] = pd.to_datetime(tx['ts'])
    date_filter = st.date_input("Filter by date", value=tx['ts'].max().date())
    tx_filtered = tx[tx['ts'].dt.date == date_filter]
    st.dataframe(tx_filtered.tail(20), use_container_width=True)
    tx_chart = px.scatter(tx_filtered, x="ts", y="amount", color="start_ccy", hover_data=["route"], title="Transfer Amounts by Date")
    st.plotly_chart(tx_chart, use_container_width=True)

# Rates chart

# --- Enhanced Rates Chart ---
st.subheader("Indicative Rates (from CSV seed; plug in providers later)")
rates = load_rates(engine)
pair_select = st.selectbox("Select pair for rates chart", sorted(rates['pair'].unique()))
rates_pair = rates[rates['pair'] == pair_select]
fig = px.line(rates_pair, x="as_of", y="rate", color="pair", markers=True, title=f"Rates for {pair_select}")
fig.add_scatter(x=rates_pair['as_of'], y=rates_pair['rate'].rolling(7, min_periods=2).mean(), mode='lines', name='SMA(7)', line=dict(color='orange'))
st.plotly_chart(fig, use_container_width=True)

# Quick simulator

# --- Advanced Route Simulator ---
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
        if 'steps' in res:
            st.markdown("<b>Step-by-step breakdown:</b>", unsafe_allow_html=True)
            for i, step in enumerate(res['steps']):
                st.markdown(f"<div style='background:#f5f6fa;border-radius:14px;padding:14px 20px;margin-bottom:10px;box-shadow:0 2px 8px #e0e0e0;'>"
                            f"<span style='font-size:1.1em;font-weight:bold;color:#1976d2'>Step {i+1}</span><br>"
                            f"<b>Description:</b> {step.get('desc','')}<br>"
                            f"<b>Amount:</b> {step.get('amount',''):.2f} {step.get('currency','')}<br>"
                            f"<b>Fee:</b> {step.get('fee',0):.2f} {step.get('currency','')}<br>"
                            f"<b>Rate:</b> {step.get('rate','')}", unsafe_allow_html=True)
            if 'end_amount' in res:
                st.success(f"End amount: {res['end_amount']:.2f} {start}")
            if all(k in res for k in ['pnl_gross', 'pnl_net', 'roi']):
                st.info(f"Gross P&L: {res['pnl_gross']:.2f} {start}  |  Net P&L: {res['pnl_net']:.2f} {start}  |  ROI: {res['roi']:.2%}")
        else:
            st.warning("Simulation breakdown not available.")

# Arbitrage finder

# --- Advanced Arbitrage Scanner ---
st.subheader("Arbitrage Scanner")
min_roi = st.slider("Min ROI %", min_value=-10.0, max_value=100.0, value=1.0, step=0.5)
cycles = arbitrage_cycles(engine, threshold=min_roi/100)
st.write(f"Found {len(cycles)} cycles with ROI ≥ {min_roi:.1f}%")
if cycles:
    arb_df = pd.DataFrame(cycles)
    st.dataframe(arb_df, use_container_width=True)
    # Network graph visualization
    st.markdown("<b>Arbitrage Network Graph:</b>", unsafe_allow_html=True)
    try:
        fig_arb = currency_graph(arb_df)
        st.plotly_chart(fig_arb, use_container_width=True)
    except Exception:
        st.warning("Graph visualization not available.")
    st.download_button("Download Arbitrage Cycles CSV", arb_df.to_csv(index=False).encode(), "arbitrage_cycles.csv", "text/csv")
