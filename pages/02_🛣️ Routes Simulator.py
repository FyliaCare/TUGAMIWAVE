import streamlit as st
import pandas as pd
from src.config import get_settings
from src.db import get_engine
from src.fx import compute_cycle, latest_rate_dict, fee_for
import plotly.graph_objects as go

# ------------------------------------------------------------
# Flag mapping for currencies
# ------------------------------------------------------------
flag_map = {
    "GHS": "🇬🇭",
    "INR": "🇮🇳",
    "MWK": "🇲🇼",
}

st.set_page_config(page_title="Routes Simulator — TUGAMIWAVE", page_icon="🛣️", layout="wide")
S = get_settings()
engine = get_engine(S.DB_URL)

st.title("🛣️ Visual Route Simulator")
st.markdown(
    """
    <div style='font-size:1.1em;'>
    <b>Build and simulate FX routes visually. Watch the cash move step‑by‑step across Ghana ⇄ India ⇄ Malawi with fees, net amounts, and ROI. Optimized for clarity—cards, Sankey flow, and a progression chart.</b>
    </div>
    <br>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _apply_fee(amount: float, pct: float, flat: float) -> float:
    """Apply fee to an amount (same logic as backend)."""
    net = amount * (1 - float(pct)) - float(flat)
    return max(net, 0.0)


def build_steps(engine, route_ccy: list[str], start_amount: float, include_fees: bool = True):
    """Return a detailed list of steps for visualization.

    Each item contains: idx, from, to, rate, gross_out, fee_pct, fee_flat, fee_value, net_out, cum_amount
    """
    rates = latest_rate_dict(engine)  # e.g. {('GHS','INR'): 8, ...}

    steps = []
    amt = float(start_amount)
    for i in range(len(route_ccy) - 1):
        a, b = route_ccy[i], route_ccy[i + 1]
        rate = float(rates[(a, b)])
        gross = amt * rate

        pct = flat = 0.0
        fee_val = 0.0
        if include_fees:
            f = fee_for(engine, f"{a}→{b}")
            pct, flat = float(f["pct"]), float(f["flat"])  # fee currency is b; visual uses values only
            net = _apply_fee(gross, pct, flat)
            fee_val = gross - net
        else:
            net = gross

        steps.append(
            {
                "idx": i + 1,
                "from": a,
                "to": b,
                "rate": rate,
                "gross_out": gross,
                "fee_pct": pct,
                "fee_flat": flat,
                "fee_value": fee_val,
                "net_out": net,
                "cum_amount": net,
            }
        )
        amt = net

    return steps, amt


# ------------------------------------------------------------
# Interactive Route Builder
# ------------------------------------------------------------
amt = st.number_input("Start amount", value=10000.0, step=100.0)
start = st.selectbox("Start currency", ["GHS", "INR", "MWK"], index=0)
currencies = ["GHS", "INR", "MWK"]
route_builder = st.multiselect("Select route (in order)", currencies, default=[start], help="Pick the intermediate currencies in the exact order you intend to traverse.")

# Normalize: always begin with the chosen start currency
if route_builder and route_builder[0] != start:
    route_builder = [start] + [c for c in route_builder if c != start]

# Require at least two distinct currencies to form a valid path
route_str = ""
route_ccy = []
if len(route_builder) >= 2:
    # Close the loop back to the start (circular plan)
    route_ccy = route_builder + [start]
    route_str = "→".join(route_ccy)

fees = st.checkbox("Include fees", value=True)

# ------------------------------------------------------------
# Simulate Route
# ------------------------------------------------------------
if st.button("Simulate Route"):
    if not route_str or len(route_ccy) < 2:
        st.error("Please select at least two currencies to build a valid route.")
    else:
        try:
            # Summary using core engine (keeps the base business logic)
            res = compute_cycle(engine, amt, start, route_str, include_fees=fees)

            # Build rich step detail for visuals (no change to core compute logic)
            steps, final_amt = build_steps(engine, route_ccy, amt, include_fees=fees)

            total_fees = sum(s["fee_value"] for s in steps)
            pnl = final_amt - amt
            roi = (final_amt - amt) / amt if amt else 0.0

            # ------------------------------------------------------------
            # SUMMARY CARDS
            # ------------------------------------------------------------
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Start", f"{amt:,.2f} {start}")
            c2.metric("End", f"{final_amt:,.2f} {start if route_ccy[-1]==start else route_ccy[-1]}")
            c3.metric("Total Fees", f"{total_fees:,.2f}")
            c4.metric("ROI", f"{roi:.2%}")

            st.markdown(
                f"""
                <div style='background:#e0f7fa;border-radius:18px;padding:18px 22px;margin:18px 0;box-shadow:0 4px 16px #b2ebf2;'>
                    <span style='font-size:1.4em;font-weight:700;color:#1976d2'>Net Profit:</span>
                    <span style='font-size:1.4em;font-weight:700;color:#00796b'> {pnl:,.2f} {start}</span>
                    <span style='margin-left:10px;color:#6b7280'>(route: {route_str})</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # ------------------------------------------------------------
            # STEP CARDS (BUY/SELL/FEES)
            # ------------------------------------------------------------
            st.subheader("Step‑by‑Step Breakdown")
            for s in steps:
                a, b = s["from"], s["to"]
                st.markdown(
                    f"""
                    <div style='background:#f8fafc;border-radius:16px;padding:16px 20px;margin-bottom:12px;box-shadow:0 2px 8px rgba(0,0,0,.06)'>
                        <div style='display:flex;align-items:center;gap:8px'>
                            <div style='font-size:1.8em'>{flag_map.get(a,'')} ➜ {flag_map.get(b,'')}</div>
                            <div style='font-weight:700;font-size:1.1em'>Step {s['idx']}: {a} → {b}</div>
                        </div>
                        <div style='margin-top:8px;color:#111'>Rate: <b>{s['rate']}</b></div>
                        <div style='margin-top:4px;color:#111'>Gross out: <b>{s['gross_out']:,.2f} {b}</b></div>
                        <div style='margin-top:4px;color:#7c3aed'>Fee: <b>{s['fee_value']:,.2f}</b> (pct {s['fee_pct']:.3f}, flat {s['fee_flat']:,.2f})</div>
                        <div style='margin-top:4px;color:#065f46'>Net out: <b>{s['net_out']:,.2f} {b}</b></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # ------------------------------------------------------------
            # FLOW (SANKEY) DIAGRAM
            # ------------------------------------------------------------
            st.subheader("Money Flow Diagram")
            labels = []
            for c in route_ccy:
                if c not in labels:
                    labels.append(f"{flag_map.get(c,'')} {c}")

            # Build links from step to step
            node_index = {lbl.split()[-1]: i for i, lbl in enumerate(labels)}  # map currency to node index
            sources, targets, values, link_labels = [], [], [], []
            prev_ccy = route_ccy[0]
            for s in steps:
                a, b = s["from"], s["to"]
                sources.append(node_index[a])
                targets.append(node_index[b])
                values.append(max(s["net_out"], 0.0))
                link_labels.append(f"{a}→{b} | net {s['net_out']:,.2f}")
                prev_ccy = b

            sankey = go.Sankey(
                node=dict(
                    pad=18,
                    thickness=16,
                    line=dict(width=0.5),
                    label=labels,
                ),
                link=dict(
                    source=sources,
                    target=targets,
                    value=values,
                    label=link_labels,
                ),
            )
            fig = go.Figure(data=[sankey])
            fig.update_layout(margin=dict(l=6, r=6, t=6, b=6), height=400)
            st.plotly_chart(fig, use_container_width=True)

            # ------------------------------------------------------------
            # AMOUNT PROGRESSION CHART
            # ------------------------------------------------------------
            st.subheader("Amount Progression")
            prog = pd.DataFrame(
                {
                    "Step": [f"{i+1}: {s['from']}→{s['to']}" for i, s in enumerate(steps)],
                    "Amount": [s["cum_amount"] for s in steps],
                }
            )
            line_fig = go.Figure()
            line_fig.add_trace(go.Scatter(x=prog["Step"], y=prog["Amount"], mode="lines+markers"))
            line_fig.update_layout(margin=dict(l=6, r=6, t=6, b=6), height=360, yaxis_title="Amount (end currency per step)")
            st.plotly_chart(line_fig, use_container_width=True)

            # ------------------------------------------------------------
            # DOWNLOADS
            # ------------------------------------------------------------
            export = pd.DataFrame(steps)
            export["route"] = route_str
            export["start_amount"] = amt
            export["final_amount"] = final_amt
            export["total_fees"] = total_fees
            export["roi"] = roi
            st.download_button(
                "Download simulation CSV",
                export.to_csv(index=False).encode(),
                "route_simulation.csv",
                "text/csv",
            )

        except Exception as e:
            st.error(f"Simulation failed: {e}")
