# app.py
import os
import re
import secrets
import hashlib
import hmac
from datetime import datetime

import streamlit as st

# -----------------------------
# App config
# -----------------------------
st.set_page_config(page_title="Auth Demo", page_icon="🔐", layout="centered")

st.markdown("""
<style>
.block-container {padding-top: 1.25rem; max-width: 720px;}
.card {
  background: var(--background-color);
  border: 1px solid rgba(49, 51, 63, .15);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 6px 30px rgba(0,0,0,.06);
}
.subtitle {opacity:.8; margin-top:-.25rem; margin-bottom:1rem;}
.helper {font-size:.85rem; opacity:.75;}
.success-badge{display:inline-block;padding:2px 8px;border-radius:999px;background:#16a34a22;color:#16a34a;font-size:.8rem;margin-left:6px;}
.error-list {margin:.5rem 0 0 0; padding-left: 1rem;}
.error-list li {margin:.15rem 0;}

/* Horizontal radio styled like tabs */
.radio-tabs .stRadio > div {flex-direction: row; gap: .5rem;}
.radio-tabs label {padding: 6px 12px; border: 1px solid rgba(49,51,63,.15);
  border-radius: 999px; cursor: pointer;}
/* Streamlit nests an input then a label; the checked state styles the label sibling */
.radio-tabs input:checked + div > label {background: rgba(49,132,253,.15);}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Session "DB"
# -----------------------------
if "users" not in st.session_state:
    st.session_state.users = []  # [{email, username, full_name, pw_hash, pw_salt, avatar_path, created_at}]
if "auth_user" not in st.session_state:
    st.session_state.auth_user = None  # stores email of logged-in user

AVATAR_DIR = "avatars"
os.makedirs(AVATAR_DIR, exist_ok=True)

# -----------------------------
# Security helpers
# -----------------------------
def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000, dklen=32)
    return dk, salt

def verify_password(password, salt, expected_hash):
    test_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(test_hash, expected_hash)

# -----------------------------
# Validation helpers
# -----------------------------
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,24}$")

def valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email or ""))

def valid_username(username: str) -> bool:
    return bool(USERNAME_RE.match(username or ""))

def password_strength(pw):
    """Return (is_ok, issues)."""
    try:
        if not pw:
            return False, ["Password cannot be empty."]
        issues = []
        if len(pw) < 8: issues.append("Use at least 8 characters.")
        if not re.search(r"[A-Z]", pw): issues.append("Add an uppercase letter.")
        if not re.search(r"[a-z]", pw): issues.append("Add a lowercase letter.")
        if not re.search(r"[0-9]", pw): issues.append("Include a number.")
        if not re.search(r"[^A-Za-z0-9]", pw):
            issues.append("Include a special character.")

        return (len(issues) == 0, issues)
    except Exception as e:
        return False, [f"Password check failed: {e}"]

def user_exists(email: str, username: str) -> bool:
    email = (email or "").strip().lower()
    username = (username or "").strip().lower()
    return any(u["email"] == email or u["username"] == username for u in st.session_state.users)

def get_user_by_email(email: str):
    email = (email or "").strip().lower()
    return next((u for u in st.session_state.users if u["email"] == email), None)

# -----------------------------
# Registration UI
# -----------------------------
def registration_card():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## Create your account")
    st.markdown('<div class="subtitle helper">No database connected — users live only for this session.</div>', unsafe_allow_html=True)

    with st.form("register_form", clear_on_submit=False):
        full_name = st.text_input("Full name", placeholder="Priya Sharma")
        email = st.text_input("Email", placeholder="you@example.com")
        username = st.text_input("Username", placeholder="your_handle (3–24 letters/numbers/_)")

        col1, col2 = st.columns(2)
        with col1:
            pw = st.text_input("Password", type="password", placeholder="••••••••")
        with col2:
            pw2 = st.text_input("Confirm password", type="password", placeholder="••••••••")

        avatar = st.file_uploader(
            "Avatar (optional, PNG/JPG ≤ 2MB)",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=False
        )

        agree = st.checkbox("I agree to the Terms & Privacy Policy", value=False)
        submitted = st.form_submit_button("Create account", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        errors = []

        if not full_name or not full_name.strip():
            errors.append("Please enter your full name.")
        if not valid_email(email):
            errors.append("Please enter a valid email address.")
        if not valid_username(username):
            errors.append("Username must be 3–24 characters and only letters, numbers, or _.")
        ok, pw_issues = password_strength(pw or "")
        if not ok:
            errors.extend(pw_issues)
        if (pw or "") != (pw2 or ""):
            errors.append("Passwords do not match.")
        if avatar is not None and avatar.size > 2 * 1024 * 1024:
            errors.append("Avatar file is too large (max 2MB).")
        if not agree:
            errors.append("You must accept the Terms to create an account.")
        if user_exists(email, username):
            errors.append("That email or username is already registered (in this session).")

        if errors:
            st.error("Please fix the following:")
            st.markdown(
                "<ul class='error-list'>" +
                "".join(f"<li>{e}</li>" for e in errors if e) +
                "</ul>",
                unsafe_allow_html=True
            )
            return

        # Save avatar if provided
        avatar_path = None
        if avatar is not None:
            ext = os.path.splitext(avatar.name)[1].lower()
            safe_name = f"{(username or '').strip().lower()}_{secrets.token_hex(4)}{ext}"
            avatar_path = os.path.join(AVATAR_DIR, safe_name)
            with open(avatar_path, "wb") as f:
                f.write(avatar.getbuffer())

        # Store user
        pw_hash, salt = hash_password(pw or "")
        st.session_state.users.append({
            "email": (email or "").strip().lower(),
            "username": (username or "").strip().lower(),
            "full_name": (full_name or "").strip(),
            "pw_hash": pw_hash,
            "pw_salt": salt,
            "avatar_path": avatar_path,
            "created_at": datetime.utcnow().isoformat()
        })

        st.success("Account created successfully!")
        st.markdown('<span class="success-badge">You can sign in now</span>', unsafe_allow_html=True)

# -----------------------------
# Login UI
# -----------------------------
def login_card():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## Log in")
    st.markdown('<div class="subtitle helper">Use the email and password from registration.</div>', unsafe_allow_html=True)

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="you@example.com", key="login_email")
        pw = st.text_input("Password", type="password", placeholder="••••••••", key="login_pw")
        remember = st.checkbox("Keep me signed in (for this session only)", value=False)
        submitted = st.form_submit_button("Sign in", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        user = get_user_by_email(email)
        if not user:
            st.error("No account found with that email.")
            return
        if not verify_password(pw or "", user["pw_salt"], user["pw_hash"]):
            st.error("Incorrect password.")
            return

        st.session_state.auth_user = user["email"]
        st.success(f"Welcome back, {user['full_name']}!")
        if remember:
            st.caption("You'll stay logged in as long as this app session is running.")

# -----------------------------
# Protected area
# -----------------------------
def authed_area():
    user = get_user_by_email(st.session_state.auth_user)
    if not user:
        st.session_state.auth_user = None
        st.warning("Your session expired. Please log in again.")
        return

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## Dashboard")
    st.write(f"Signed in as **{user['full_name']}**  \n`{user['email']}`")

    c1, c2 = st.columns([1, 2])
    with c1:
        if user["avatar_path"] and os.path.exists(user["avatar_path"]):
            st.image(user["avatar_path"], caption="Your avatar", use_column_width=True)
        else:
            st.caption("No avatar uploaded.")
    with c2:
        st.write("**Username:**", user["username"])
        st.write("**Joined:**", user["created_at"])
        st.write("**Users in session:**", len(st.session_state.users))

        st.write("")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Log out", use_container_width=True):
                st.session_state.auth_user = None
                st.experimental_rerun()
        with col_b:
            if st.button("Delete my account", use_container_width=True):
                st.session_state.users = [u for u in st.session_state.users if u["email"] != user["email"]]
                st.session_state.auth_user = None
                st.success("Account deleted (session only).")
                st.experimental_rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# Layout: selector placed near the form
# -----------------------------
if st.session_state.auth_user:
    authed_area()
else:
    # radio "tabs" right above the card
    st.markdown("<div class='radio-tabs'>", unsafe_allow_html=True)
    view = st.radio("Choose view", ["Register", "Login"], horizontal=True,
                    label_visibility="collapsed", key="auth_view")
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")  # spacer

    if view == "Register":
        registration_card()
    else:
        login_card()

# -----------------------------
# Optional dev tools
# -----------------------------
with st.expander("🔎 Dev: show users in session"):
    if not st.session_state.users:
        st.caption("No users yet.")
    else:
        for u in st.session_state.users:
            st.write({
                "email": u["email"],
                "username": u["username"],
                "full_name": u["full_name"],
                "avatar_path": u["avatar_path"],
                "created_at": u["created_at"],
            })
