
import streamlit as st
import pandas as pd
from src.config import get_settings
from src.db import get_engine, transfers_df
import plotly.express as px

st.set_page_config(page_title="Risk — TUGAMIWAVE", page_icon="🛡️", layout="wide")
S = get_settings()
engine = get_engine(S.DB_URL)

st.title("🛡️ Risk & Compliance")
st.markdown("""
Monitor risk and compliance across all transfers. Automated flagging, visualizations, and checklists help you stay compliant and spot suspicious activity.
""")

# --- Load Data ---
df = transfers_df(engine)

# --- Automated Flagging ---
def flag_transaction(row):
	flags = []
	if row['amount'] > 10000:
		flags.append('Large Amount')
	if row['roi'] < 0:
		flags.append('Negative ROI')
	if row['route'] in ['GHS→INR→MWK', 'MWK→INR→GHS']:
		flags.append('Unusual Corridor')
	return ', '.join(flags) if flags else 'Normal'
df['risk_flag'] = df.apply(flag_transaction, axis=1)

# --- Summary Cards ---
col1, col2, col3 = st.columns(3)
flagged_count = (df['risk_flag'] != 'Normal').sum()
normal_count = (df['risk_flag'] == 'Normal').sum()
avg_risk = flagged_count / len(df) if len(df) else 0
col1.metric("Flagged Transactions", flagged_count)
col2.metric("Normal Transactions", normal_count)
col3.metric("% Flagged", f"{avg_risk*100:.1f}%")

# --- Filters ---
st.subheader("Filter Flagged Transactions")
colf1, colf2 = st.columns(2)
with colf1:
	risk_filter = st.selectbox("Risk Level", ["All", "Flagged", "Normal"])
with colf2:
	corridor_filter = st.selectbox("Corridor", ["All"] + sorted(df['route'].unique()))

filtered_df = df.copy()
if risk_filter == "Flagged":
	filtered_df = filtered_df[filtered_df['risk_flag'] != 'Normal']
elif risk_filter == "Normal":
	filtered_df = filtered_df[filtered_df['risk_flag'] == 'Normal']
if corridor_filter != "All":
	filtered_df = filtered_df[filtered_df['route'] == corridor_filter]

# --- Visualizations ---
st.subheader("Risk Distribution")
fig = px.pie(df, names='risk_flag', title="Risk Flag Distribution")
st.plotly_chart(fig, use_container_width=True)

# --- Flagged Transaction List ---
st.subheader("Flagged Transactions Details")
if not filtered_df.empty:
	for idx, row in filtered_df.head(30).iterrows():
		with st.expander(f"{row['ts']} | {row['route']} | {row['amount']} | {row['risk_flag']}"):
			st.write(row)
else:
	st.info("No transactions found for selected filters.")

# --- Compliance Checklist ---
st.subheader("Compliance Checklist")
st.markdown("""
- [ ] KYC completed for all counterparties
- [ ] AML screening for flagged transactions
- [ ] Per-corridor limits enforced
- [ ] Counterparty ratings reviewed
- [ ] Alert thresholds for ROI drops and fee spikes set
""")

# --- Export Flagged Data ---
st.download_button("Download flagged transactions CSV", filtered_df.to_csv(index=False).encode(), "flagged_transactions.csv", "text/csv")
