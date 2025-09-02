import streamlit as st
import pandas as pd
from src.db import get_engine
from src.config import get_settings
from src.fx import load_rates
import plotly.express as px
import plotly.graph_objects as go

# Flag mapping for currency pairs
flag_map = {
	"GHS": "🇬🇭",
	"INR": "🇮🇳",
	"MWK": "🇲🇼",
}

st.set_page_config(page_title="Rates — TUGAMIWAVE", page_icon="💱", layout="wide")
S = get_settings()
engine = get_engine(S.DB_URL)

st.title("💱 Corridor FX Rates Dashboard")
st.markdown(
    """
    Monitor, compare, and analyze corridor FX rates (GHS ⇄ INR ⇄ MWK). 
    Use filters, charts, volatility and correlation views, and download options for decision‑ready insight.
    """
)

# ---------------------------------------------------------------------------------
# Load & prep
# ---------------------------------------------------------------------------------
df = load_rates(engine).copy()
df['as_of'] = pd.to_datetime(df['as_of'])
# normalize ordering inside each pair for consistent grouping (no change to the stored pair)
df.sort_values(['pair', 'as_of'], inplace=True)

# ---------------------------------------------------------------------------------
# KPI BAR — latest snapshot for selected pair
# ---------------------------------------------------------------------------------
latest_by_pair = df.groupby('pair').tail(1).set_index('pair')
all_pairs = sorted(df['pair'].unique())
sel_pair = st.selectbox("Primary pair for KPIs", all_pairs)

if sel_pair in latest_by_pair.index:
    latest_rate = latest_by_pair.loc[sel_pair, 'rate']
    # compute last change if at least 2 observations exist
    last_points = df[df['pair'] == sel_pair].sort_values('as_of').tail(2)['rate'].tolist()
    delta = last_points[-1] - last_points[0] if len(last_points) == 2 else 0.0
    # 7‑day realized volatility (if enough points)
    psel = df[df['pair'] == sel_pair].set_index('as_of').sort_index()
    psel['ret'] = psel['rate'].pct_change()
    vol7 = psel['ret'].rolling(7, min_periods=2).std().dropna()
    vol7_val = vol7.iloc[-1] if not vol7.empty else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Latest rate", f"{latest_rate:,.5f}")
    c2.metric("Δ since last", f"{delta:+.5f}")
    c3.metric("7‑day vol", f"{vol7_val:.2%}")
    c4.metric("Observations", f"{len(df[df['pair']==sel_pair]):,}")

st.divider()
# ---------------------------------------------------------------------------------
# Comprehensive Rate Comparison & Calculator for Simulator
# ---------------------------------------------------------------------------------
st.subheader("Comprehensive Rate Comparison & Calculator")
st.markdown("""
Compare all relevant rates for a selected currency pair: Bank Rate, Market Buying Rate, Binance USDT Rate, and more. Use the calculator to see conversion results for each rate type. These rates are used in the Route Simulator for real profit calculations.
""")

# Select pair and input rates

comp_pair = st.selectbox("Select pair for comprehensive comparison", all_pairs, index=all_pairs.index(sel_pair) if sel_pair in all_pairs else 0)
# Manual entry for bank rate
use_bank_rate = st.checkbox("Use Bank Rate", value=True)
bank_rate = None
if use_bank_rate:
    bank_rate_input = st.text_input("Bank Rate", value=str(latest_by_pair.loc[comp_pair, 'rate']) if comp_pair in latest_by_pair.index else "", help="Enter the current bank rate for this pair")
    bank_rate = float(bank_rate_input) if bank_rate_input.strip() else None
market_rate = st.number_input("Market Buying Rate", value=bank_rate if bank_rate is not None else 1.0, step=0.0001, format="%.5f", help="Current market buying rate for this pair")
use_binance_rate = st.checkbox("Use Binance USDT Rate", value=False)
binance_rate = None
if use_binance_rate:
    binance_rate_input = st.text_input("Binance USDT Rate", value="", help="Current Binance USDT rate for this pair")
    binance_rate = float(binance_rate_input) if binance_rate_input.strip() else None
 

# Show all rates side-by-side
rate_df = pd.DataFrame({
    "Rate Type": ["Bank Rate", "Market Buying Rate", "Binance USDT Rate"],
    "Rate": [bank_rate if use_bank_rate and bank_rate is not None else "(not used)", market_rate, binance_rate if use_binance_rate and binance_rate is not None else "(not used)"]
})
st.dataframe(rate_df, use_container_width=True)

# Conversion calculator for all rates
st.markdown("**Conversion Calculator (for selected pair and rates):**")
calc_amount = st.number_input("Amount to convert", value=1000.0, step=100.0)
a, b = comp_pair.split('/')
calc_results = {
    "Bank Rate": calc_amount * bank_rate if use_bank_rate and bank_rate is not None else "(not used)",
    "Market Buying Rate": calc_amount * (market_rate if market_rate is not None else 1.0),
    "Binance USDT Rate": calc_amount * binance_rate if use_binance_rate and binance_rate is not None else "(not used)"
}
calc_df = pd.DataFrame({
    "Rate Type": list(calc_results.keys()),
    f"{calc_amount:,.2f} {a} in {b}": [f"{v:,.2f}" if isinstance(v, (int, float)) else str(v) for v in calc_results.values()]
})
st.dataframe(calc_df, use_container_width=True)

# Make these rates available for simulator integration (e.g., via session state)

# --- Save Rates Button & Logic ---
def save_custom_rate(pair, bank_rate, market_rate, binance_rate, engine):
    import sqlalchemy as sa
    from datetime import datetime
    meta = sa.MetaData()
    rates_table = sa.Table('rates', meta, autoload_with=engine)
    # Insert or update the custom rate for the selected pair
    with engine.begin() as conn:
        # Remove any previous custom rate for this pair with today's date
        today = datetime.now().date()
        conn.execute(rates_table.delete().where(
            (rates_table.c.pair == pair) & (rates_table.c.as_of == today)
        ))
        # Insert new rates
        if bank_rate is not None:
            conn.execute(rates_table.insert().values(pair=pair, rate=bank_rate, as_of=today, source='custom_bank'))
        if market_rate is not None:
            conn.execute(rates_table.insert().values(pair=pair, rate=market_rate, as_of=today, source='custom_market'))
        if binance_rate is not None:
            conn.execute(rates_table.insert().values(pair=pair, rate=binance_rate, as_of=today, source='custom_binance'))

if st.button("Save Rates"):
    save_custom_rate(comp_pair, bank_rate, market_rate, binance_rate, engine)
    st.success("Rates saved for simulation and future use.")

# Store rates in session for simulator integration
st.session_state['simulator_rates'] = {
    'pair': comp_pair,
    'bank_rate': bank_rate,
    'market_rate': market_rate,
    'binance_rate': binance_rate
}

# ---------------------------------------------------------------------------------
# Live Rates Table (with flags & search)
# ---------------------------------------------------------------------------------
st.subheader("Live Rates Table")
search_pair = st.text_input("Search currency pair", "", help="Type like GHS/INR or MWK/GHS; leave empty to show all")
if search_pair:
    filtered_df = df[df['pair'].str.contains(search_pair.upper(), na=False)].copy()
else:
    filtered_df = df.copy()

def pair_flags(pair: str) -> str:
    a, b = pair.split('/')
    return f"{flag_map.get(a, a)} {a} / {flag_map.get(b, b)} {b}"

filtered_df = filtered_df.assign(pair_display=filtered_df['pair'].apply(pair_flags))

st.dataframe(
    filtered_df[['pair_display', 'rate', 'as_of']].rename(columns={'pair_display': 'pair'}),
    use_container_width=True,
)

# Download filtered
st.download_button(
    "Download filtered CSV",
    filtered_df.to_csv(index=False).encode(),
    "rates_filtered.csv",
    "text/csv",
)

# ---------------------------------------------------------------------------------
# Rate Change Alerts (configurable threshold)
# ---------------------------------------------------------------------------------
st.subheader("Rate Change Alerts")
threshold = st.slider("Spike threshold (absolute change)", 0.00, 1.00, 0.10, 0.01)
rate_diff = filtered_df.groupby('pair')['rate'].diff()
spikes = filtered_df[rate_diff.abs() > threshold]
if not spikes.empty:
    st.warning("Rate spikes/drops detected for: " + ", ".join(sorted(spikes['pair'].unique())))
    st.dataframe(spikes[['pair', 'rate', 'as_of']], use_container_width=True)
else:
    st.success("No significant rate spikes detected at the chosen threshold.")

st.divider()

# ---------------------------------------------------------------------------------
# Historical Rates — Candlestick, plus Moving Average overlay
# ---------------------------------------------------------------------------------
st.subheader("Historical Rates Chart")
pair_select = st.selectbox("Select currency pair", all_pairs, index=all_pairs.index(sel_pair) if sel_pair in all_pairs else 0)
date_min = st.date_input("From Date", value=df['as_of'].min().date())
date_max = st.date_input("To Date", value=df['as_of'].max().date())
mask = (df['pair'] == pair_select) & (df['as_of'] >= pd.to_datetime(date_min)) & (df['as_of'] <= pd.to_datetime(date_max))
hist_df = df[mask]

if not hist_df.empty:
    ohlc = hist_df.copy()
    ohlc['date'] = ohlc['as_of'].dt.date
    ohlc_daily = (
        ohlc.groupby('date')
        .agg(open=('rate', 'first'), high=('rate', 'max'), low=('rate', 'min'), close=('rate', 'last'))
        .reset_index()
    )
    fig = go.Figure(data=[go.Candlestick(
        x=ohlc_daily['date'],
        open=ohlc_daily['open'],
        high=ohlc_daily['high'],
        low=ohlc_daily['low'],
        close=ohlc_daily['close'],
        name=f"{pair_flags(pair_select)}",
    )])
    # add simple moving average (7‑period)
    if len(ohlc_daily) >= 2:
        ohlc_daily['sma7'] = ohlc_daily['close'].rolling(7, min_periods=2).mean()
        fig.add_trace(go.Scatter(x=ohlc_daily['date'], y=ohlc_daily['sma7'], mode='lines', name='SMA(7)'))
    fig.update_layout(title=f"{pair_flags(pair_select)} Daily Candlestick", xaxis_title="Date", yaxis_title="Rate", height=420)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data for selected pair and date range.")

st.divider()

# ---------------------------------------------------------------------------------
# Pair Comparison — multi-line + normalized index and correlation heatmap
# ---------------------------------------------------------------------------------
st.subheader("Compare Currency Pairs")
compare_pairs = st.multiselect("Select pairs to compare", all_pairs, default=all_pairs[:2])
comp_df = df[df['pair'].isin(compare_pairs)].copy()
if not comp_df.empty:
    # raw rate comparison
    fig2 = px.line(comp_df, x='as_of', y='rate', color='pair', title="Currency Pair Comparison")
    st.plotly_chart(fig2, use_container_width=True)

    # normalized to 100 at start for relative performance
    st.caption("Indexed to 100 from first available point for each pair (relative performance)")
    idx_df = comp_df.copy()
    idx_df['base'] = idx_df.groupby('pair')['rate'].transform(lambda s: s.iloc[0])
    idx_df['index_100'] = 100 * idx_df['rate'] / idx_df['base']
    fig3 = px.line(idx_df, x='as_of', y='index_100', color='pair', title="Indexed Performance (=100 at start)")
    st.plotly_chart(fig3, use_container_width=True)

    # correlation matrix (daily closes)
    st.caption("Correlation of daily closes between selected pairs")
    comp_daily = comp_df.copy()
    comp_daily['date'] = comp_daily['as_of'].dt.date
    pivot = comp_daily.pivot_table(index='date', columns='pair', values='rate', aggfunc='last')
    corr = pivot.corr().round(3)
    st.dataframe(corr, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------------
# Quick What‑If Calculator (using latest quote)
# ---------------------------------------------------------------------------------
st.subheader("What‑If Conversion Calculator")
colA, colB, colC = st.columns([1,1,1])
with colA:
    amount = st.number_input("Amount", value=1000.0, step=100.0)
with colB:
    pair_calc = st.selectbox("Pair", all_pairs, index=all_pairs.index(sel_pair) if sel_pair in all_pairs else 0)
with colC:
    show_inverse = st.checkbox("Show inverse as well", value=True)

latest_rate_calc = latest_by_pair.loc[pair_calc, 'rate'] if pair_calc in latest_by_pair.index else None
if latest_rate_calc is not None:
    a, b = pair_calc.split('/')
    out = amount * latest_rate_calc
    st.success(f"{pair_flags(pair_calc)}  →  {amount:,.2f} {a} = {out:,.2f} {b} @ {latest_rate_calc}")
    if show_inverse and latest_rate_calc != 0:
        inv = 1.0 / latest_rate_calc
        st.info(f"Inverse {flag_map.get(b,'')} {b} / {flag_map.get(a,'')} {a}  →  1 {b} = {inv:.6f} {a}")
else:
    st.error("No latest rate available for that pair.")

# ---------------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------------
st.download_button("Download full rates CSV", df.to_csv(index=False).encode(), "rates_export.csv", "text/csv")
