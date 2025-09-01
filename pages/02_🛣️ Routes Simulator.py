import streamlit as st, pandas as pd
from src.config import get_settings
from src.db import get_engine
from src.fx import compute_cycle

st.set_page_config(page_title="Routes Simulator — TUGAMIWAVE", page_icon="🛣️", layout="wide")
S = get_settings(); engine = get_engine(S.DB_URL)

st.title("🛣️ Routes Simulator")
amt = st.number_input("Start amount", value=10000.0, step=100.0)
start = st.selectbox("Start currency", ["GHS","INR","MWK"])
route = st.selectbox("Route", ["GHS→INR→MWK→GHS","MWK→INR→GHS→MWK","INR→MWK→GHS→INR"])
fees = st.checkbox("Include fees", value=True)
if st.button("Simulate"):
    res = compute_cycle(engine, amt, start, route, include_fees=fees)
    # Expect res to be a dict with steps, amounts, fees, etc.
    if isinstance(res, dict) and "steps" in res:
        st.subheader("Simulation Breakdown")
        for i, step in enumerate(res["steps"]):
            st.markdown(f"**Step {i+1}:** {step['desc']}")
            st.write(f"Amount: {step['amount']:.2f} {step['currency']}")
            if 'fee' in step:
                st.write(f"Fee: {step['fee']:.2f} {step['currency']}")
            st.markdown("---")

        st.subheader(":star: Summary")
        st.write(f"**Final Amount:** {res.get('final_amount', 'N/A'):.2f} {res.get('final_currency', '')}")
        st.write(f"**Total Fees:** {res.get('total_fees', 'N/A'):.2f}")
        if 'profit' in res:
            st.write(f"**Profit/Loss:** {res['profit']:.2f}")

        # Line chart for amount progression
        st.subheader("Amount Progression")
        chart_data = pd.DataFrame({
            'Step': [f"{i+1}" for i in range(len(res["steps"]))],
            'Amount': [step['amount'] for step in res["steps"]]
        })
        st.line_chart(chart_data.set_index('Step'))
    else:
        st.warning("Simulation result format not recognized. Showing raw output:")
        st.json(res)
