import streamlit as st
import base64
from pathlib import Path

# ---------- helpers ----------
def _b64(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode()

def _get_param():
    # Works on both new and older Streamlit versions
    try:
        return st.query_params.get("p", "home")
    except Exception:
        return st.experimental_get_query_params().get("p", ["home"])[0]

# ---------- routing: pick config first so it's set only once ----------
p = _get_param()
if p == "checklist":
    st.set_page_config(page_title="Pharma SOP • Checklist & Benefits", page_icon="💊", layout="wide")
else:
    st.set_page_config(page_title="Create Pharma SOPs", page_icon="💊", layout="wide")

# ---------- pages ----------
def render_homepage():
    img = _b64("images/pharma.png")

    st.markdown(
        f"""
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@700&display=swap" rel="stylesheet">

        <style>
          /* Hide sidebar just in case */
          [data-testid="stSidebar"] {{ display: none !important; }}

          /* Remove Streamlit default padding */
          .block-container {{ padding: 0 !important; }}
          [data-testid="stAppViewContainer"] .main {{ padding: 0 !important; }}
          [data-testid="stHeader"] {{ background: transparent; }}
          [data-testid="stToolbar"] {{ right: 1rem; }}

          /* Background image with overlay */
          .stApp {{
            background: url("data:image/png;base64,{img}") no-repeat center center fixed;
            background-size: cover;
          }}
          .stApp:before {{
            content: "";
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.35);
            z-index: 0;
          }}

          /* Center hero block */
          .hero {{
            position: relative;
            z-index: 1;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            gap: 0.9rem;
            padding: 2rem;
          }}
          .hero h1 {{
            font-family: 'Poppins', sans-serif;
            color: #fff;
            margin: 0;
            font-weight: 700;
            line-height: 1.1;
            font-size: clamp(2.6rem, 6vw, 4.3rem);
            text-shadow: 0 2px 18px rgba(0,0,0,.35);
          }}
          .hero p {{
            color: #e8eef6;
            font-style: italic;
            margin: 0 0 .6rem 0;
            font-size: clamp(1rem, 2vw, 1.25rem);
            text-shadow: 0 1px 12px rgba(0,0,0,.35);
          }}

          /* Button styles (yours) */
          .btn {{
            display: inline-block;
            background: #003366 !important;
            color: #fff !important;
            padding: 0.45rem 1.2rem;
            border-radius: 8px;
            font-weight: 700;
            font-size: 0.95rem;
            text-decoration: none !important;
            box-shadow: 0 2px 10px rgba(0,0,0,.25);
            transition: background .2s ease, transform .05s ease;
          }}
          .btn:hover {{ background: #005599 !important; }}
          .btn:active {{ transform: translateY(1px); }}

          html {{ scroll-behavior: smooth; }}
        </style>

        <!-- HERO -->
        <section class="hero">
          <h1>Create Pharma SOPs</h1>
          <p>“Consistency in process creates reliability in results.”</p>
          <!-- Keep your existing button exactly as-is -->
          <a class="btn" href="#start" id="get-started-btn">Get Started</a>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div id="start"></div>', unsafe_allow_html=True)
    st.write("Welcome! Let's build your SOPs.")

    # Make your styled button change the URL (?p=checklist) in SAME TAB, then reload once.
    st.markdown(
        """
        <script>
        document.addEventListener('DOMContentLoaded', function () {
          const btn = document.getElementById('get-started-btn') || document.querySelector('a.btn[href="#start"]');
          if (!btn || btn._wired) return;
          btn._wired = true;
          btn.addEventListener('click', function (e) {
            e.preventDefault();
            const url = new URL(window.location.href);
            url.searchParams.set('p', 'checklist');
            // replace() keeps same tab and avoids extra history entry
            window.location.replace(url.toString());
          });
        });
        </script>
        """,
        unsafe_allow_html=True
    )

def render_checklist():
    img = _b64("images/pharma.png")

    st.markdown(
        f"""
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

          [data-testid="stSidebar"] {{ display: none !important; }}

          html, body, [data-testid="stAppViewContainer"], .block-container, .overlay-left, .overlay-right {{
              font-family: 'Poppins', sans-serif !important;
              color: black !important;
          }}

          html, body, [data-testid="stAppViewContainer"], .main, .block-container {{
            min-height: 100vh;
          }}
          .block-container {{ padding: 0 !important; }}

          [data-testid="stAppViewContainer"] {{
            background: url("data:image/png;base64,{img}") no-repeat center center fixed;
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
        """,
        unsafe_allow_html=True
    )

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

    # Right box
    st.markdown("""
    <div class="overlay-right">
      <div class="right-title">
        Want to summarise or generate<br>new SOP?
      </div>
      <a class="login-btn" href="/login">Login</a>
    </div>
    """, unsafe_allow_html=True)

# ---------- render ----------
if p == "checklist":
    render_checklist()
else:
    render_homepage()
