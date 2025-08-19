import re
import base64
import streamlit as st

from db_repo import (
    username_taken,
    email_taken,
    register_user,
    register_admin,
)

st.set_page_config(page_title="Registration", page_icon="🔐", layout="wide")

# --- tiny router 
goto = st.query_params.get("goto")
if isinstance(goto, list):
    goto = goto[0] if goto else None
if goto == "login":
    st.switch_page("pages/login.py")
elif goto == "manage_users":
    st.switch_page("pages/manage_users.py")

# Admin invite from secrets (fallback kept empty to force correct config)
DEFAULT_ADMIN_INVITE_CODE = st.secrets.get("app", {}).get("admin_invite", "")

# ====== FULL-PAGE BG + LEFT CARD + WHITE INPUTS ======
def set_bg_and_layout(image_path: str = "images/pharma.png", card_width_px: int = 560, left_gap_vw: int = 2):
    import base64
    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        b64 = ""

    st.markdown(
        f"""
        <style>
          html, body, [data-testid="stAppViewContainer"] {{ height: 100%; }}

          /* Full-page background */
          [data-testid="stAppViewContainer"] {{
            background-image: url("data:image/png;base64,{b64}");
            background-size: cover;
            background-position: center center;
            background-repeat: no-repeat;
            background-attachment: fixed;
          }}

          /* Transparent header */
          [data-testid="stHeader"] {{ background: transparent; }}

          /* Center vertically, left-align horizontally */
          [data-testid="stAppViewContainer"] > .main {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: flex-start;
            min-height: 100vh;
            background: transparent;
          }}

          /* Card */
          .block-container {{
            max-width: {card_width_px}px !important;
            width: 100%;
            margin-left: {left_gap_vw}vw !important;
            margin-right: auto !important;
            margin-top: clamp(24px, 6vh, 96px) !important;
            margin-bottom: clamp(24px, 6vh, 96px) !important;
            padding: 1.25rem 1.25rem 2.25rem 1.25rem;
            background: rgba(255,255,255,0.86);
            border: 1px solid rgba(255,255,255,0.55);
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.12);
            backdrop-filter: blur(2px);
          }}

          /* Make inputs truly white */
          div[data-baseweb="input"] > div,
          div[data-baseweb="textarea"] > div {{
            background-color: #ffffff !important;
            border: 1px solid rgba(209,213,219,0.95) !important;
          }}
          div[data-baseweb="input"] input,
          div[data-baseweb="textarea"] textarea {{
            background-color: #ffffff !important;
            color: #111827 !important;
          }}
          div[data-baseweb="input"] input::placeholder,
          div[data-baseweb="textarea"] textarea::placeholder {{
            color: #9ca3af !important;
            opacity: 1 !important;
          }}
          div[data-baseweb="input"] > div:focus-within,
          div[data-baseweb="textarea"] > div:focus-within {{
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 2px rgba(59,130,246,0.25) !important;
          }}

          /* "Registered user? Login" line on the right */
          .login-cta {{ text-align: right; margin-top: .5rem; }}
          .login-cta a {{ text-decoration: none; font-weight: 600; }}

          /* Tabs & text polish */
          .stTabs [data-baseweb="tab-list"] {{ gap: 1rem; }}
          .stTabs [data-baseweb="tab"] {{ padding: 0.5rem 0.75rem; }}
          .field-note {{ color:#6b7280; font-size: 0.85rem; margin-top: -0.35rem; }}
          h1, h2, h3 {{ color:#1f2937; }}

          /* Mobile */
          @media (max-width: 768px) {{
            .block-container {{ max-width: 92vw !important; margin-left: 4vw !important; }}
            .login-cta {{ text-align: left; }}
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )

set_bg_and_layout()  # uses pharma.png

# ====== VALIDATION ======
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
def validate_shared(username, email, pw, pw2):
    errs = []
    if not username or len(username.strip()) < 3:
        errs.append("Username must be at least 3 characters.")
    if not email or not EMAIL_RE.match(email.strip().lower()):
        errs.append("Enter a valid email address.")
    if not pw or len(pw) < 8:
        errs.append("Password must be at least 8 characters.")
    if pw != pw2:
        errs.append("Passwords do not match.")
    return errs

# ====== UI: REGISTRATION ONLY ======
st.title("🔐 Registration")

tabs = st.tabs(["👤 User", "🛡️ Admin"])

# ---------- USER ----------
with tabs[0]:
    st.subheader("Create a User account")
    with st.form("user_signup", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            u_username = st.text_input("Username", placeholder="e.g. jdoe")
        with c2:
            u_email = st.text_input("Email", placeholder="you@example.com")
        c3, c4 = st.columns(2)
        with c3:
            u_pw = st.text_input("Password", type="password")
            st.markdown('<div class="field-note">Use 8+ characters with letters & numbers.</div>', unsafe_allow_html=True)
        with c4:
            u_pw2 = st.text_input("Confirm Password", type="password")
        agree = st.checkbox("I agree to the Terms of Service")
        u_submit = st.form_submit_button("Sign up as User", use_container_width=True)

    if u_submit:
        errs = validate_shared(u_username, u_email, u_pw, u_pw2)
        if not agree:
            errs.append("You must agree to the Terms of Service.")
        # duplicate checks against SQL Server
        if username_taken(u_username):
            errs.append("That username is already taken.")
        if email_taken(u_email):
            errs.append("That email is already registered.")

        if errs:
            st.error("Please fix the following:\n\n- " + "\n- ".join(errs))
        else:
            try:
                # Calls your stored proc: dbo.sp_register_user
                register_user(u_username, u_email, u_pw)
                st.success("🎉 User account created!")
            except Exception as e:
                st.error(f"Database error while creating user: {e}")

# ---------- ADMIN ----------
with tabs[1]:
    st.subheader("Create an Admin account")
    with st.form("admin_signup", clear_on_submit=False):
        a_username = st.text_input("Admin Username", placeholder="e.g. a.singh")
        a_email = st.text_input("Admin Email", placeholder="admin@company.com")
        a_org = st.text_input("Organization / Team", placeholder="e.g. Acme Corp")
        a_invite = st.text_input("Admin Invite Code", type="password", placeholder="Use the configured admin invite code")
        d1, d2 = st.columns(2)
        with d1:
            a_pw = st.text_input("Password", type="password")
            st.markdown('<div class="field-note">Use 8+ characters with letters & numbers.</div>', unsafe_allow_html=True)
        with d2:
            a_pw2 = st.text_input("Confirm Password", type="password")
        st.markdown("**Admin Preferences (optional)**")
        a_reports = st.checkbox("Email me weekly system reports", value=True)
        a_submit = st.form_submit_button("Sign up as Admin", use_container_width=True)

    if a_submit:
        errs = validate_shared(a_username, a_email, a_pw, a_pw2)
        if not a_invite or a_invite.strip() != DEFAULT_ADMIN_INVITE_CODE:
            errs.append("Invalid Admin Invite Code.")
        if not a_org.strip():
            errs.append("Organization is required for admin accounts.")
        # duplicate checks against SQL Server
        if username_taken(a_username):
            errs.append("That username is already taken.")
        if email_taken(a_email):
            errs.append("That email is already registered.")

        if errs:
            st.error("Please fix the following:\n\n- " + "\n- ".join(errs))
        else:
            try:
                # Calls your stored proc: dbo.sp_register_admin
                register_admin(a_username, a_email, a_pw, a_org, a_reports)
                st.success("🛡️ Admin account created! Elevated privileges enabled.")
            except Exception as e:
                st.error(f"Database error while creating admin: {e}")

# ---------- Registered user? Login (link only for now) ----------
st.markdown(
    '<div class="login-cta">Registered user? '
    '<a href="?goto=login" target="_self" '
    '   onclick="window.location.search=\'?goto=login\'; return false;">Login</a>'
    '</div>',
    unsafe_allow_html=True,
)
