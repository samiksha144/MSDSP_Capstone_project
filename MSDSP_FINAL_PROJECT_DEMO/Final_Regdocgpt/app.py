# app.py
import streamlit as st
st.set_page_config(page_title="Auth", page_icon="🔐", layout="wide")
st.session_state.setdefault("account", None)

target = "pages/registration.py" if st.query_params.get("register") == "1" else "pages/login.py"

try:
    st.switch_page(target)
except Exception:
    st.title("Auth")
    st.page_link("pages/login.py", label="🔐 Login")
    st.page_link("pages/registration.py", label="📝 Registration")
