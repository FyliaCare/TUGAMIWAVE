import streamlit as st
from src.config import get_settings
st.set_page_config(page_title="Settings — TUGAMIWAVE", page_icon="⚙️", layout="wide")
S = get_settings()
st.title("⚙️ Settings")
st.json(S.model_dump())
st.write("Set environment variables or `.env` to change these.")
