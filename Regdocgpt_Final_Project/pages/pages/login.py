# pages/login.py
import base64
from pathlib import Path
import streamlit as st
from db_conn import sql_conn

st.set_page_config(page_title="Login", page_icon="🔐", layout="wide")

# --- tiny router
goto = st.query_params.get("goto")
if isinstance(goto, list):
    goto = goto[0] if goto else None
if goto == "register":
    st.switch_page("pages/registration.py")

# ====== Background + left card ======
def set_full_bg_and_left_card(candidates: tuple[str, ...]):
    img_b64 = None
    for p in candidates:
        fp = Path(p)
        if fp.exists():
            img_b64 = base64.b64encode(fp.read_bytes()).decode()
            break
    if not img_b64:
        return
    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"],
        [data-testid="stHeader"] {{
            background-image: url("data:image/png;base64,{img_b64}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        [data-testid="stHeader"] {{ background-color: transparent; }}
        .block-container {{
            max-width: 500px;
            margin: 3.5rem auto 3rem 2rem;
            background: rgba(255,255,255,0.96);
            border-radius: 24px;
            padding: 2.0rem 1.5rem 1.25rem;
            box-shadow: 0 24px 60px rgba(0,0,0,0.15);
        }}
        .register-cta {{ margin-top: .75rem; font-size: 0.95rem; }}
        .register-cta a {{ text-decoration: none; font-weight: 700; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

set_full_bg_and_left_card((
    "images/pharma.png",
    "/mnt/data/f59cf081-297e-4696-88b2-40d6373f2dd8.png",
))

# ====== SQL auth helpers ======
def login_user(identifier: str, password: str):
    ident = (identifier or "").strip().lower()
    if not ident or not password:
        return None
    q = """
    SELECT TOP 1 user_id, username, email
      FROM dbo.users
     WHERE (LOWER(username)=? OR LOWER(email)=?)
       AND is_active = 1
       AND password_hash = dbo.ufn_hash_password(?, password_salt)
    """
    with sql_conn() as c, c.cursor() as cur:
        cur.execute(q, ident, ident, password)
        row = cur.fetchone()
        if not row:
            return None
        cur.execute("UPDATE dbo.users SET last_login = SYSUTCDATETIME() WHERE user_id = ?", row[0])
        c.commit()
        return {"id": row[0], "username": row[1], "email": row[2], "role": "user"}

def login_admin(identifier: str, password: str):
    ident = (identifier or "").strip().lower()
    if not ident or not password:
        return None
    q = """
    SELECT TOP 1 admin_id, username, email, org
      FROM dbo.admins
     WHERE (LOWER(username)=? OR LOWER(email)=?)
       AND is_active = 1
       AND password_hash = dbo.ufn_hash_password(?, password_salt)
    """
    with sql_conn() as c, c.cursor() as cur:
        cur.execute(q, ident, ident, password)
        row = cur.fetchone()
        if not row:
            return None
        cur.execute("UPDATE dbo.admins SET last_login = SYSUTCDATETIME() WHERE admin_id = ?", row[0])
        c.commit()
        return {"id": row[0], "username": row[1], "email": row[2], "org": row[3], "role": "admin"}

# ====== UI ======
st.title("🔐 Login")
tabs = st.tabs(["👤 User", "🛡️ Admin"])

# --- USER -> redirect to 1.py on success ---
with tabs[0]:
    st.subheader("Login as User")
    with st.form("user_login", clear_on_submit=False):
        lu_identifier = st.text_input("Username or Email", placeholder="jdoe or user@example.com")
        lu_pw = st.text_input("Password", type="password")
        lu_submit = st.form_submit_button("Log in as User", use_container_width=True)
    if lu_submit:
        try:
            acct = login_user(lu_identifier, lu_pw)
            if acct:
                st.session_state["account"] = acct
                st.switch_page("pages/user_dashboard.py")   # <<<<<< redirects to your dashboard
            else:
                st.error("Incorrect username/email or password.")
        except Exception as e:
            st.error(f"Database error during login: {e}")

# --- ADMIN (kept as-is; we can also redirect later if you want) ---
with tabs[1]:
    st.subheader("Login as Admin")
    with st.form("admin_login", clear_on_submit=False):
        la_identifier = st.text_input("Admin Username or Email", placeholder="a.singh or admin@company.com")
        la_pw = st.text_input("Password", type="password")
        la_submit = st.form_submit_button("Log in as Admin", use_container_width=True)
    if la_submit:
        try:
            acct = login_admin(la_identifier, la_pw)
            if acct:
                st.session_state["account"] = acct
                st.switch_page("pages/admin_dashboard.py")   # optionally also send admins to the same dashboard
            else:
                st.error("Incorrect username/email or password.")
        except Exception as e:
            st.error(f"Database error during login: {e}")

# --- CTA UNDER TABS ---
st.markdown(
    "<p class='register-cta'>Haven't registered yet? "
    "<a href='?goto=register' target='_self'"
    "   onclick=\"window.location.search='?goto=register'; return false;\">"
    "Register</a></p>",
    unsafe_allow_html=True,
)
