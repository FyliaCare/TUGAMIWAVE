import streamlit as st
import pandas as pd
from sqlalchemy import text
from src.config import get_settings
from src.db import get_engine
import plotly.graph_objects as go

# Flag mapping for currencies
flag_map = {
    "GHS": "🇬🇭",
    "INR": "🇮🇳",
    "MWK": "🇲🇼",
}

st.set_page_config(page_title="Fees — TUGAMIWAVE", page_icon="💸", layout="wide")
S = get_settings()
engine = get_engine(S.DB_URL)

st.title("💸 Fees & Charges")
st.markdown("Manage and visualize transaction fees for each corridor. All values are live from your database.")

with engine.begin() as conn:
    df = pd.read_sql("select * from fees", conn)

# --- Responsive Fee Cards Grid ---
st.subheader("Corridor Fees Overview")
n_cols = 4
rows = [df.iloc[i:i+n_cols] for i in range(0, len(df), n_cols)]
for row in rows:
    cols = st.columns(len(row))
    for idx, card in enumerate(row.itertuples()):
        corridor = card.corridor
        parts = corridor.split('→')
        flags = " ".join([flag_map.get(p, "") for p in parts])
        color = "#f0f8ff" if idx % 2 == 0 else "#fffbe6"
        with cols[idx]:
            st.markdown(
                f"""
                <div style='border:1px solid #d0d0d0; border-radius:10px; padding:12px; background:{color}; text-align:center;'>
                    <span style='font-size:1.7em;'>{flags}</span><br>
                    <b style='font-size:1.1em;'>{corridor}</b><br>
                    <span style='color:#888;'>Percent Fee:</span> <b style='color:#0077b6;'>{card.pct*100:.2f}%</b><br>
                    <span style='color:#888;'>Flat Fee:</span> <b style='color:#d97706;'>{card.flat:.2f} {card.currency} {flag_map.get(card.currency, '')}</b>
                </div>
                """,
                unsafe_allow_html=True
            )

st.markdown("---")

# --- Modern Fee Trends Graph ---
st.subheader("Fee Trends Across Corridors")
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df['corridor'], y=df['pct']*100, mode='lines+markers',
    name='Percent Fee (%)', line=dict(color='#0077b6', width=3), marker=dict(size=8)
))
fig.add_trace(go.Scatter(
    x=df['corridor'], y=df['flat'], mode='lines+markers',
    name='Flat Fee', line=dict(color='#d97706', width=3), marker=dict(size=8)
))
fig.update_layout(
    xaxis_title='Corridor',
    yaxis_title='Fee Value',
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    height=400,
    template='plotly_white',
    margin=dict(l=20, r=20, t=40, b=20),
    font=dict(family='Segoe UI, Arial', size=14)
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("""
</div>
<hr>
""", unsafe_allow_html=True)

# --- Section: Filters ---

st.divider()
st.subheader("Edit / Add Fee")
st.markdown("""
**Edit / Add Fee:**
- Select a corridor and currency, then set the percent and flat fee to update or add a new fee.
- Changes are saved instantly and reflected in the table above.
""")
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
