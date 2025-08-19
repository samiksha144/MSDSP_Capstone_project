import base64
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components  # for history.replaceState

st.set_page_config(page_title="Pharma SOP • Checklist & Benefits", page_icon="💊", layout="wide")

# --- tiny router (run early)
goto = st.query_params.get("goto")
if isinstance(goto, list):   # handle older/varied Streamlit behavior
    goto = goto[0] if goto else None
if goto == "login":
    st.switch_page("pages/login.py")

# --- helper: remove transient query params (e.g., ?goto=...) from the URL without new history entry
def normalize_url(remove_params=("goto",)):
    # Server-side: clear for Streamlit widgets/state
    try:
        for p in remove_params:
            if p in st.query_params:
                del st.query_params[p]
    except Exception:
        pass
    # Client-side: replace current URL in-place (no extra history entry)
    components.html(f"""
    <script>
      (function() {{
        const url = new URL(window.location);
        const toRemove = {list(remove_params)};
        let changed = false;
        for (const p of toRemove) {{
          if (url.searchParams.has(p)) {{
            url.searchParams.delete(p);
            changed = true;
          }}
        }}
        if (changed) {{
          const qs = url.searchParams.toString();
          const newUrl = url.pathname + (qs ? ("?" + qs) : "") + url.hash;
          window.history.replaceState({{}}, "", newUrl);
        }}
      }})();
    </script>
    """, height=0)

def set_bg(img_file: str):
    p = Path(img_file)
    mime = "png" if p.suffix.lower() == ".png" else "jpeg"
    b64 = base64.b64encode(p.read_bytes()).decode()

    st.markdown(f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

      html, body, [data-testid="stAppViewContainer"], .block-container, .overlay-left, .overlay-right {{
          font-family: 'Poppins', sans-serif !important;
          color: black !important; /* Make default text black */
      }}

      html, body, [data-testid="stAppViewContainer"], .main, .block-container {{
        min-height: 100vh;
      }}
      .block-container {{ padding: 0 !important; }}

      [data-testid="stAppViewContainer"] {{
        background: url("data:image/{mime};base64,{b64}") no-repeat center center fixed;
        background-size: cover;
      }}
      [data-testid="stAppViewContainer"]::before {{
        content: "";
        position: fixed;
        inset: 0;
        background: linear-gradient(90deg, rgba(255,255,255,.85) 0%, rgba(255,255,255,.6) 35%, rgba(255,255,255,0) 70%);
        pointer-events: none;
        z-index: 0;
      }}
      [data-testid="stHeader"] {{ background: transparent; }}
      header {{ visibility: hidden; height: 0; }}

      /* Left section */
      .overlay-left {{
        position: relative;
        margin: 8vh 6vw;
        max-width: min(640px, 80vw);
        z-index: 1;
        color: black !important;
        text-shadow: none !important;
      }}
      .overlay-left h1 {{
        margin: 0 0 1rem 0;
        font-size: clamp(1.6rem,3.8vw,2.4rem);
        line-height: 1.3;
        font-weight: 700;
      }}
      .overlay-left h2 {{
        margin: 1.5rem 0 0.75rem 0;
        font-size: clamp(1.2rem,2.6vw,1.6rem);
        font-weight: 600;
      }}
      .overlay-left ul {{
        margin: 0.5rem 0 1rem 1.25rem;
        padding: 0;
        list-style: none;
      }}
      .overlay-left li {{
        font-size: clamp(0.9rem,1.8vw,1.2rem);
        line-height: 1.6;
        margin: .5rem 0;
        font-weight: 400;
      }}
      .overlay-left li::before {{ content: "✔️  "; }}

      /* Right box */
      .overlay-right {{
        position: fixed;
        right: 6vw;
        top: 50%;
        transform: translateY(-50%);
        width: min(400px, 30vw);
        z-index: 2;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1rem;
        text-align: center;
        padding: 1.6rem 1.2rem;
        color: black !important;
        backdrop-filter: blur(6px);
        background: rgba(255, 255, 255, .85);
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,.25);
      }}
      .right-title {{
        margin: 0;
        font-size: clamp(0.95rem, 1.4vw, 1.2rem);
        font-weight: 600;
        line-height: 1.6;
      }}
      .login-btn {{
        appearance: none;
        border: none;
        border-radius: 999px;
        padding: 0.7rem 1.4rem;
        font-size: 0.95rem;
        font-weight: 600;
        cursor: pointer;
        color: black !important;
        background: #21d4fd;
        box-shadow: 0 6px 16px rgba(0,0,0,.25);
        transition: transform .06s ease, box-shadow .2s ease, opacity .2s ease;
        text-decoration: none !important;
        display: inline-block;
      }}
      .login-btn:hover,
      .login-btn:focus,
      .login-btn:active {{
        text-decoration: none !important;
        transform: translateY(-1px);
        box-shadow: 0 10px 22px rgba(0,0,0,.3);
        opacity: .95;
        color: black !important;
      }}
    </style>
    """, unsafe_allow_html=True)

set_bg("images/pharma.png")

# Left checklist
st.markdown("""
<div class="overlay-left">
  <h1>Checklist for a Compliant Pharma SOP</h1>
  <ul>
    <li>Title page with SOP ID, version, and effective date</li>
    <li>Purpose & scope clearly defined</li>
    <li>Definitions & abbreviations</li>
    <li>Roles & responsibilities</li>
    <li>Step-by-step procedure (numbered)</li>
    <li>Materials, equipment & safety requirements</li>
    <li>References to regulations/related SOPs</li>
    <li>Change history / revision log</li>
    <li>Approval signatures (QA & department head)</li>
    <li>Annexes: forms, diagrams, flowcharts</li>
  </ul>

  <h2>Benefits of Generating SOPs on Our Website</h2>
  <ul>
    <li>Instant compliance checks (GMP/FDA/ISO)</li>
    <li>Create SOPs in minutes</li>
    <li>Access to a pro template library</li>
    <li>Automatic version control</li>
    <li>Secure cloud storage</li>
    <li>Audit-ready exports (PDF/Docx)</li>
    <li>Real-time team collaboration</li>
  </ul>
</div>
""", unsafe_allow_html=True)

# Right box with same-tab navigation to login
st.markdown("""
<div class="overlay-right">
  <div class="right-title">
    Want to summarise or generate<br>new SOP?
  </div>
  <!-- relative URL so hosting/proxy doesn't drop the query string; onclick ensures navigation even under subpaths -->
  <a class="login-btn" href="?goto=login" target="_self"
     onclick="window.location.search='?goto=login'; return false;">Login</a>
</div>
""", unsafe_allow_html=True)

# --- clean the URL so the Back button goes to the true previous page (no extra hop)
normalize_url(("goto",))
