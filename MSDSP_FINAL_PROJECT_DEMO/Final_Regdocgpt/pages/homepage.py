import streamlit as st
import base64
from pathlib import Path
import streamlit.components.v1 as components  # for history manipulation

st.set_page_config(page_title="Create Pharma SOPs", page_icon="💊", layout="wide")

# --- tiny router
goto = st.query_params.get("goto")
if isinstance(goto, list):   # handle list form
    goto = goto[0] if goto else None
if goto == "checklist":
    st.switch_page("pages/checklist.py")

# --- helper: remove transient query params (e.g., ?goto=...) from the URL without new history entry
def normalize_url(remove_params=("goto",)):
    # Clear server-side so Streamlit widgets/state don't see it
    try:
        for p in remove_params:
            if p in st.query_params:
                del st.query_params[p]
    except Exception:
        pass
    # Replace current URL in-place (no extra history entry)
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

# --- background setup
IMG_PATH = Path("images/pharma.png")
img_b64 = base64.b64encode(IMG_PATH.read_bytes()).decode()

# ---------- CSS + HERO ----------
st.markdown(
    f"""
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@700&display=swap" rel="stylesheet">

    <style>
      /* Remove Streamlit default padding */
      .block-container {{ padding: 0 !important; }}
      [data-testid="stAppViewContainer"] .main {{ padding: 0 !important; }}
      [data-testid="stHeader"] {{ background: transparent; }}
      [data-testid="stToolbar"] {{ right: 1rem; }}

      /* Background image with overlay */
      .stApp {{
        background: url("data:image/png;base64,{img_b64}") no-repeat center center fixed;
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

      /* Button styles */
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
      <!-- ✅ query-param link; same-tab navigation -->
      <a class="btn" href="?goto=checklist" target="_self"
         onclick="window.location.search='?goto=checklist'; return false;">Get Started</a>
    </section>
    """,
    unsafe_allow_html=True,
)

# --- clean the URL so Back doesn't include transient params
normalize_url(("goto",))

# --- homepage back-guard: keep user on homepage if they press the Back button here
components.html("""
<script>
  (function(){
    try {
      // Push a marker state so the next Back triggers popstate
      history.pushState({home_guard:1}, "", window.location.href);
      // When user presses Back from homepage, immediately re-push and stay
      window.addEventListener("popstate", function(e){
        if (e.state && e.state.home_guard === 1) {
          history.pushState({home_guard:1}, "", window.location.href);
        }
      });
    } catch(e) {}
  })();
</script>
""", height=0)
