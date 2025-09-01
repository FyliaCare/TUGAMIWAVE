
import streamlit as st
import pandas as pd
from sqlalchemy import text
from src.config import get_settings
from src.db import get_engine
import plotly.express as px

st.set_page_config(page_title="Ledger — TUGAMIWAVE", page_icon="📒", layout="wide")
S = get_settings()
engine = get_engine(S.DB_URL)

st.title("📒 Ledger & Transfers")
st.markdown("""
Track all transfers and ledger entries. Use filters, summary cards, and visualizations to analyze your transaction history.
""")

with engine.begin() as conn:
    df = pd.read_sql("select * from transfers order by ts desc", conn)

# --- Summary Cards ---
col1, col2, col3, col4 = st.columns(4)
total_credits = df[df['type']=='credit']['amount'].sum() if 'type' in df and 'amount' in df else 0
total_debits = df[df['type']=='debit']['amount'].sum() if 'type' in df and 'amount' in df else 0
balance = total_credits - total_debits
txn_count = len(df)
col1.metric("Total Credits", f"{total_credits:,.2f}")
col2.metric("Total Debits", f"{total_debits:,.2f}")
col3.metric("Balance", f"{balance:,.2f}")
col4.metric("Transactions", f"{txn_count}")

# --- Filters ---
st.subheader("Filter Transactions")
colf1, colf2, colf3 = st.columns(3)
with colf1:
    date_min = st.date_input("From Date", value=pd.to_datetime(df['ts']).min() if 'ts' in df else pd.Timestamp.today())
    date_max = st.date_input("To Date", value=pd.to_datetime(df['ts']).max() if 'ts' in df else pd.Timestamp.today())
with colf2:
    currency = st.selectbox("Currency", ["All"] + sorted(df['currency'].unique())) if 'currency' in df else "All"
with colf3:
    txn_type = st.selectbox("Type", ["All"] + sorted(df['type'].unique())) if 'type' in df else "All"

filtered_df = df.copy()
if 'ts' in df:
    filtered_df = filtered_df[(pd.to_datetime(filtered_df['ts']) >= pd.to_datetime(date_min)) & (pd.to_datetime(filtered_df['ts']) <= pd.to_datetime(date_max))]
if currency != "All" and 'currency' in df:
    filtered_df = filtered_df[filtered_df['currency'] == currency]
if txn_type != "All" and 'type' in df:
    filtered_df = filtered_df[filtered_df['type'] == txn_type]

# --- Trend Chart ---
if not filtered_df.empty and 'ts' in filtered_df and 'amount' in filtered_df:
    st.subheader("Transaction Trends")
    fig = px.line(filtered_df, x='ts', y='amount', color='type', title="Credits & Debits Over Time")
    st.plotly_chart(fig, use_container_width=True)

# --- Expandable Transaction Details ---
st.subheader("Ledger Entries")
if not filtered_df.empty:
    for idx, row in filtered_df.head(30).iterrows():
        with st.expander(f"{row['ts']} | {row['type'].capitalize()} | {row['amount']} {row['currency']}"):
            st.write(row)
else:
    st.info("No transactions found for selected filters.")

# --- CSV Download ---
st.download_button("Download filtered ledger CSV", filtered_df.to_csv(index=False).encode(), "ledger.csv", "text/csv")
