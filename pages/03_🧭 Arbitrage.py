
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.config import get_settings
from src.db import get_engine
from src.fx import arbitrage_cycles, currency_graph, compute_cycle

st.set_page_config(page_title="Arbitrage — TUGAMIWAVE", page_icon="🧭", layout="wide")
S = get_settings()
engine = get_engine(S.DB_URL)

st.title("🧭 Arbitrage Scanner")
st.markdown("""
**Arbitrage Scanner** helps you find profitable currency conversion cycles across GHS, INR, and MWK. Use the filters below to customize your search and explore opportunities.
""")

# Advanced filters
st.markdown("""
**Filters:**
- **Min/Max ROI %**: Set the minimum and maximum Return on Investment for cycles to display.
- **Start Currency**: Choose which currency to start the cycle from, or select 'All' for every currency.
- **Include Fees & Spreads**: Toggle to include transaction fees and spreads in calculations.
""")
col1, col2, col3 = st.columns(3)
with col1:
	min_roi = st.slider("Min ROI %", -10.0, 100.0, 1.0, 0.5)
	max_roi = st.slider("Max ROI %", min_value=min_roi, max_value=100.0, value=100.0, step=0.5)
with col2:
	currency = st.selectbox("Start Currency", ["GHS", "INR", "MWK", "All"], index=3)
with col3:
	include_fees = st.checkbox("Include Fees & Spreads", value=True)

# Get cycles
cycles_raw = arbitrage_cycles(engine, threshold=min_roi/100)
cycles = [c for c in cycles_raw if c["roi"] <= max_roi/100]
if currency != "All":
	cycles = [c for c in cycles if c["cycle"].startswith(currency)]

df_cycles = pd.DataFrame(cycles)

if df_cycles.empty:
	st.markdown("""
	**Arbitrage Cycles Table:**
	- Each row shows a possible arbitrage cycle, its ROI, net multiplier, and total fees.
	- Click on a cycle to expand and see a step-by-step breakdown of currency conversions and fees.
	""")
	st.warning("No arbitrage cycles found for the selected filters.")
else:
	st.write(f"Found {len(df_cycles)} cycles with ROI between {min_roi:.1f}% and {max_roi:.1f}%.")
	# Interactive table with expandable details
	for idx, row in df_cycles.iterrows():
		with st.expander(f"{row['cycle']} | ROI: {row['roi']*100:.2f}% | Net Multiplier: {row['net_multiplier']:.4f}"):
			st.write(f"Total Fees: {row['fees']:.4f}")
			# Step-by-step breakdown
			sim = compute_cycle(engine, 1.0, row['cycle'].split('→')[0], row['cycle'], include_fees=include_fees)
			steps_df = pd.DataFrame(sim['steps'])
			st.dataframe(steps_df, use_container_width=True)

	# Download results
	st.markdown("""
	**Download Results:**
	- Click the button below to download the displayed arbitrage cycles as a CSV file for further analysis.
	""")
	csv = df_cycles.to_csv(index=False).encode('utf-8')
	st.download_button("Download cycles as CSV", data=csv, file_name="arbitrage_cycles.csv", mime="text/csv")

	# Network graph visualization
	st.markdown("""
	**Network Graph:**
	- Visualizes the relationships and conversion rates between currencies.
	- Each line represents a possible conversion, with the rate shown in the legend.
	""")
	st.subheader("Arbitrage Network Graph")
	edges = currency_graph(engine)
	fig = go.Figure()
	nodes = set()
	for e in edges:
		fig.add_trace(go.Scatter(x=[0,1], y=[e['from'],e['to']], mode='lines+markers',
								 line=dict(width=2), name=f"{e['from']}→{e['to']} ({e['rate']:.4f})"))
		nodes.add(e['from'])
		nodes.add(e['to'])
	fig.update_layout(height=400, showlegend=True, title="Currency Conversion Network")
	st.plotly_chart(fig, use_container_width=True)

# Simulation tool
st.markdown("""
**Simulation Tool:**
- Enter a custom cycle path and amount to simulate a hypothetical arbitrage scenario.
- The tool will show the final amount, total fees, profit, ROI, and a step-by-step breakdown.
""")
st.subheader("Simulate Arbitrage Cycle")
sim_col1, sim_col2 = st.columns(2)
with sim_col1:
	sim_start = st.selectbox("Start Currency", ["GHS", "INR", "MWK"])
	sim_path = st.text_input("Cycle Path (e.g. GHS→INR→MWK→GHS)", value=f"{sim_start}→INR→MWK→{sim_start}")
with sim_col2:
	sim_amt = st.number_input("Amount to Simulate", min_value=1.0, value=1000.0, step=1.0)
	sim_fees = st.checkbox("Include Fees", value=True)
if st.button("Run Arbitrage Simulation"):
	try:
		sim_res = compute_cycle(engine, sim_amt, sim_start, sim_path, include_fees=sim_fees)
		st.success(f"Final Amount: {sim_res['final_amount']:.2f} {sim_res['final_currency']}")
		st.write(f"Total Fees: {sim_res['total_fees']:.2f}")
		st.write(f"Profit: {sim_res['profit']:.2f}")
		st.write(f"ROI: {(sim_res['final_amount']-sim_amt)/sim_amt:.2%}")
		st.dataframe(pd.DataFrame(sim_res['steps']), use_container_width=True)
	except Exception as e:
		st.error(f"Simulation error: {e}")
