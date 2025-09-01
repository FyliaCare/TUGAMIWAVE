import streamlit as st, pandas as pd
from sqlalchemy import text
from src.config import get_settings
from src.db import get_engine

st.set_page_config(page_title="Fees — TUGAMIWAVE", page_icon="💸", layout="wide")
S = get_settings(); engine = get_engine(S.DB_URL)

st.title("💸 Fees & Charges")
with engine.begin() as conn:
    df = pd.read_sql("select * from fees", conn)
st.dataframe(df, use_container_width=True)

st.divider()
st.subheader("Edit / Add Fee")
corridor = st.selectbox("Corridor", df["corridor"].unique().tolist()+["Custom…"])
if corridor == "Custom…":
    corridor = st.text_input("Type corridor like GHS→INR")

pct = st.number_input("Percent fee (0.01 = 1%)", value=0.005, step=0.001, format="%.3f")
flat = st.number_input("Flat fee", value=5.0, step=1.0)
ccy = st.text_input("Fee currency", value="INR")

if st.button("Save/Upsert"):
    with engine.begin() as conn:
        conn.execute(text("""insert into fees(corridor,pct,flat,currency)
        values(:c,:p,:f,:k)
        on conflict do nothing"""), {"c":corridor,"p":pct,"f":flat,"k":ccy})
        conn.execute(text("""update fees set pct=:p, flat=:f, currency=:k where corridor=:c"""),
                     {"c":corridor,"p":pct,"f":flat,"k":ccy})
    st.success("Saved. Reload the page to see updates.")
