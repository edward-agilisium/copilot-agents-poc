import streamlit as st
import httpx

# ============================================================
# 1. PAGE CONFIG & SESSION STATE
# ============================================================
st.set_page_config(
    page_title="Copilot Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_URL = "http://127.0.0.1:8000"

# — Preserved state keys (do not rename) —
if "folder_history" not in st.session_state:
    st.session_state.folder_history = [{"id": "root", "name": "root"}]
if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected_files" not in st.session_state:
    st.session_state.selected_files = set()
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# ============================================================
# 2. GLASSMORPHISM CSS
# ============================================================
def inject_custom_css():
    st.markdown("""
<style>
    /* ── CORE RESET ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    #MainMenu, footer, .stAppDeployButton { visibility: hidden; display: none !important; }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }

    /* ── TEAL COLOR TOKENS ── */
    :root {
        --teal-main:   #ececec;
        --teal-dark:   #d4d4d4;
        --teal-deeper: #ffffff;
        --teal-light:  #2b2b2b;
        --teal-bg:     #171717;
        --slate:       #f8fafc;
        --slate-mid:   #a3a3a3;
        --slate-faint: #737373;
        --white:       #1e1e1e;
        --glass-bg:    rgba(33, 33, 33, 0.7);
        --glass-border:rgba(66, 66, 66, 0.5);
        --shadow-sm:   0 1px 3px rgba(0,0,0,0.5), 0 1px 2px rgba(0,0,0,0.3);
        --shadow-md:   0 4px 16px rgba(0,0,0,0.6), 0 2px 6px rgba(0,0,0,0.4);
        --shadow-lg:   0 10px 40px rgba(0,0,0,0.8), 0 4px 12px rgba(0,0,0,0.5);
        --radius-sm:   8px;
        --radius-md:   14px;
        --radius-lg:   20px;
    }

    /* ══════════════════════════════════════
       FORCE LIGHT MODE — defeat dark theme
       ══════════════════════════════════════ */
    .stApp,
    .stApp > div,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > section,
    [data-testid="stBottom"],
    .main .block-container,
    section[data-testid="stSidebarContent"] {
        background-color: transparent !important;
        color: #ececec !important;
    }

    /* Force all generic text/labels/spans to be dark-on-light */
    p, span, label, div, h1, h2, h3, h4, small, li, a {
        color: #ececec !important;
    }

    /* Sidebar specific text overrides */
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] small {
        color: #d4d4d4 !important;
    }

    /* Dark mode override */
    [data-testid="stBaseButton-secondary"],
    [data-testid="stBaseButton-primary"],
    div[class*="stTextInput"] input,
    div[class*="stTextArea"] textarea,
    div[data-baseweb="select"],
    div[data-baseweb="popover"],
    div[data-baseweb="menu"] ul li,
    div[data-baseweb="menu"],
    div[data-baseweb="textarea"],
    [data-testid="stFileUploadDropzone"],
    [data-testid="stFileUploadDropzone"] * {
        background-color: #212121 !important;
        color: #ececec !important;
        border: 1px solid #424242 !important;
    }

    /* ── HEADER OVERRIDE ── */
    [data-testid="stHeader"] {
        background: transparent !important;
    }

    /* ── MAIN BG ── */
    .stApp {
        background: linear-gradient(135deg, #111111 0%, #171717 40%, #171717 100%) !important;
    }

    .block-container {
        padding-top: 3rem !important;
        padding-bottom: 4rem !important;
        max-width: 1200px !important;
    }

    /* ── SIDEBAR ── */
    [data-testid="stSidebar"] {
        background: #171717 !important;
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-right: 1px solid var(--glass-border) !important;
        box-shadow: 2px 0 24px rgba(0,0,0,0.07) !important;
    }

    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: var(--teal-deeper) !important;
        font-weight: 700 !important;
    }

    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label {
        color: var(--slate-mid) !important;
    }

    /* ── SIDEBAR TOGGLE BUTTONS — always visible, never hidden ── */

    /* EXPAND button: shown when sidebar is collapsed */
    [data-testid="collapsedControl"] {
        opacity: 1 !important;
        visibility: visible !important;
        display: flex !important;
        background: #212121 !important;
        border-radius: 50% !important;
        border: 2px solid #424242 !important;
        box-shadow: 0 4px 16px rgba(0,0,0,0.3) !important;
        color: #ececec !important;
        min-width: 36px !important;
        min-height: 36px !important;
        align-items: center !important;
        justify-content: center !important;
        z-index: 99999 !important;
        position: fixed !important;
        top: 12px !important;
        left: 12px !important;
    }
    /* The inner button element Streamlit puts inside collapsedControl */
    [data-testid="collapsedControl"] button {
        opacity: 1 !important;
        background: transparent !important;
        color: #ececec !important;
    }
    [data-testid="collapsedControl"] svg,
    [data-testid="collapsedControl"] button svg {
        fill: #ececec !important;
        opacity: 1 !important;
    }

    /* COLLAPSE button: the <<< button visible inside sidebar */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapseButton"] button {
        opacity: 1 !important;
        visibility: visible !important;
        color: #ececec !important;
        background: rgba(0,0,0,0.08) !important;
        border-radius: 6px !important;
    }
    [data-testid="stSidebarCollapseButton"] svg {
        fill: #ececec !important;
        opacity: 1 !important;
    }
    /* Hover states */
    [data-testid="collapsedControl"]:hover,
    [data-testid="stSidebarCollapseButton"]:hover {
        background: #f0fdfa !important;
        box-shadow: 0 6px 20px rgba(0,0,0,0.4) !important;
        opacity: 1 !important;
    }

    /* ── TABS ── */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--glass-bg);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: var(--radius-lg);
        border: 1px solid var(--glass-border);
        box-shadow: var(--shadow-sm);
        padding: 5px 8px;
        gap: 4px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: var(--radius-md) !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        color: var(--slate-faint) !important;
        padding: 8px 20px !important;
        border: none !important;
        background: transparent !important;
        transition: all 0.25s ease !important;
    }

    .stTabs [aria-selected="true"] {
        color: var(--teal-main) !important;
        background: #2b2b2b !important;
        box-shadow: var(--shadow-sm) !important;
        font-weight: 600 !important;
    }

    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 24px !important;
    }

    /* ── ALL BUTTONS (RESET) ── */
    div.stButton > button {
        border-radius: var(--radius-sm) !important;
        border: 1px solid #424242 !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
        box-shadow: none !important;
        background-color: #2b2b2b !important;
        color: #ececec !important;
    }
    div.stButton > button p,
    div.stButton > button span {
        color: #ececec !important;
    }
    div.stButton > button:hover {
        background-color: #3b3b3b !important;
        border-color: #525252 !important;
    }
    div.stButton > button:hover p,
    div.stButton > button:hover span {
        color: #ffffff !important;
    }

    /* ── FOLDER CARD BUTTONS ── */
    .folder-card-btn div.stButton > button {
        width: 100% !important;
        min-height: 100px !important;
        background: #212121 !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: var(--radius-md) !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;

        justify-content: center !important;
        text-align: center !important;
        padding: 12px !important;
        cursor: pointer !important;
        box-shadow: var(--shadow-sm) !important;
        transition: all 0.25s ease !important;
        font-size: 0.85rem !important;
        color: var(--slate-mid) !important;
    }

    .folder-card-btn div.stButton > button:hover {
        background: linear-gradient(135deg, rgba(0,0,0,0.08), rgba(0,0,0,0.05)) !important;
        border-color: var(--teal-main) !important;
        box-shadow: var(--shadow-md) !important;
        transform: translateY(-2px) !important;
        color: var(--teal-deep) !important;
    }

    .folder-card-btn div.stButton > button p {
        color: inherit !important;
    }

    /* ── PRIMARY ACTION BUTTON ── */
    .primary-btn div.stButton > button {
        background: linear-gradient(135deg, var(--teal-main), var(--teal-dark)) !important;
        color: white !important;
        border: none !important;
        border-radius: var(--radius-md) !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
        transition: all 0.25s ease !important;
    }
    .primary-btn div.stButton > button:hover {
        box-shadow: 0 8px 24px rgba(0,0,0,0.4) !important;
        transform: translateY(-1px) !important;
    }
    .primary-btn div.stButton > button p { color: white !important; }

    /* ── DANGER/CLEAR BUTTON ── */
    .danger-btn div.stButton > button {
        background: rgba(239,68,68,0.07) !important;
        color: #dc2626 !important;
        border: 1px solid rgba(239,68,68,0.25) !important;
        border-radius: var(--radius-sm) !important;
    }
    .danger-btn div.stButton > button:hover {
        background: rgba(239,68,68,0.12) !important;
        border-color: rgba(239,68,68,0.5) !important;
    }
    .danger-btn div.stButton > button p { color: #dc2626 !important; }

    /* ── SIDEBAR BACK BUTTON ── */
    .back-btn div.stButton > button {
        background: rgba(0,0,0,0.08) !important;
        color: var(--teal-main) !important;
        border: 1px solid rgba(0,0,0,0.2) !important;
        border-radius: var(--radius-sm) !important;
        font-size: 0.82rem !important;
        padding: 4px 12px !important;
        width: auto !important;
    }
    .back-btn div.stButton > button p { color: var(--teal-main) !important; }

    /* ── FILE UPLOADER ── */
    [data-testid="stFileUploader"] {
        background: #212121 !important;
        border: 2px dashed #424242 !important;
        border-radius: 14px !important;
        padding: 8px !important;
    }
    [data-testid="stFileUploader"]:hover {
        background: #f0fdfa !important;
        border-color: #0f766e !important;
    }
    /* The actual inner dropzone Streamlit renders */
    [data-testid="stFileUploadDropzone"] {
        background: #ffffff !important;
        border-radius: 10px !important;
        border: none !important;
    }
    /* Force every child element inside the dropzone to white */
    [data-testid="stFileUploadDropzone"],
    [data-testid="stFileUploadDropzone"] *:not(button):not(svg) {
        background-color: #ffffff !important;
        color: #d4d4d4 !important;
    }
    [data-testid="stFileUploadDropzone"] small,
    [data-testid="stFileUploadDropzone"] span,
    [data-testid="stFileUploadDropzone"] p {
        color: #64748b !important;
    }
    [data-testid="stFileUploadDropzone"] button {
        background: #f0fdfa !important;
        color: #ececec !important;
        border: 1px solid #525252 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    [data-testid="stFileUploader"] p,
    [data-testid="stFileUploader"] small {
        color: #64748b !important;
    }

    /* ── EXPANDER ── */
    [data-testid="stExpander"] {
        background: var(--glass-bg) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: var(--radius-md) !important;
        backdrop-filter: blur(8px) !important;
        box-shadow: var(--shadow-sm) !important;
    }
    [data-testid="stExpander"] summary {
        color: var(--teal-deep) !important;
        font-weight: 600 !important;
    }
    [data-testid="stExpander"] summary p { color: var(--teal-deep) !important; }

    /* ── MULTISELECT ── */
    .stMultiSelect label p { color: var(--slate-mid) !important; font-weight: 600 !important; }
    .stMultiSelect div[data-baseweb="select"] {
        background: var(--glass-bg) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: var(--radius-sm) !important;
    }
    span[data-baseweb="tag"] {
        background: linear-gradient(135deg, rgba(0,0,0,0.12), rgba(0,0,0,0.08)) !important;
        color: var(--teal-deeper) !important;
        border: 1px solid rgba(0,0,0,0.25) !important;
        border-radius: 6px !important;
    }

    /* ── RADIO (SEARCH MODE) ── */
    .stRadio > div {
        flex-direction: row !important;
        gap: 12px !important;
        background: var(--glass-bg);
        border: 1px solid var(--glass-border);
        border-radius: 999px;
        padding: 5px 18px;
        box-shadow: var(--shadow-sm);
        width: fit-content;
        margin: 0 auto;
    }
    .stRadio label { font-weight: 500 !important; color: var(--slate-mid) !important; }
    .stRadio label div { color: inherit !important; }

    /* ── CHAT MESSAGES ── */
    [data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 12px 0 !important;
    }

    [data-testid="stChatMessage"][data-testid*="user"],
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background: #212121 !important;
        border-radius: 12px !important;
        padding: 16px !important;
        border: 1px solid #424242 !important;
    }

    [data-testid="stChatMessage"] p { color: var(--slate) !important; line-height: 1.7 !important; }
    [data-testid="stChatMessage"] code {
        color: var(--teal-deeper) !important;
        background: rgba(0,0,0,0.4) !important;
        border-radius: 4px !important;
        padding: 1px 5px !important;
    }
    [data-testid="stChatMessage"] a { color: var(--teal-main) !important; font-weight: 600 !important; }

    [data-testid="chatAvatarIcon-assistant"] {
        background: linear-gradient(135deg, #171717, #212121) !important;
        border: 1px solid #424242 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
    }

    /* ── CHAT INPUT ── */
    [data-testid="stChatInput"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important; 
    }
    [data-testid="stChatInput"] > div {
        background: #212121 !important;
        border: 1px solid #424242 !important;
        border-radius: 28px !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4) !important;
        padding-right: 12px !important;
        margin-top: 10px !important;
    }
    [data-testid="stChatInput"] textarea,
    [data-testid="stChatInput"] input {
        background: transparent !important;
        color: #ececec !important;
        caret-color: #ececec !important;
        padding-left: 12px !important;
        border: none !important;
    }
    [data-testid="stChatInput"] textarea::placeholder { color: #888888 !important; }
    [data-testid="stChatInput"] button {
        background: #3b82f6 !important;
        border-radius: 50% !important;
        width: 38px !important; height: 38px !important;
        border: none !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
        display: flex !important; align-items: center !important; justify-content: center !important;
        margin-left: 8px !important;
    }
    [data-testid="stChatInput"] button svg { fill: white !important; }

    /* ── DIVIDERS ── */
    hr { border-color: var(--glass-border) !important; margin: 12px 0 !important; }

    /* ── GLASS CARD (reusable helper class) ── */
    .glass-card {
        background: var(--glass-bg);
        border: 1px solid var(--glass-border);
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-sm);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        padding: 20px;
        margin-bottom: 16px;
    }

    /* ── METRIC/PILL TAGS ── */
    .context-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: linear-gradient(135deg, rgba(0,0,0,0.1), rgba(0,0,0,0.07));
        border: 1px solid rgba(0,0,0,0.2);
        border-radius: 999px;
        padding: 3px 12px;
        font-size: 0.78rem;
        font-weight: 500;
        color: var(--teal-deeper);
        margin: 2px 3px;
        font-family: 'Inter', sans-serif;
    }

    /* ── STATUS PILL ── */
    .status-online {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: linear-gradient(135deg, rgba(16,185,129,0.08), rgba(16,185,129,0.04));
        border: 1px solid rgba(16,185,129,0.22);
        border-radius: 999px;
        padding: 5px 14px 5px 10px;
        font-size: 0.7rem;
        font-family: 'Inter', monospace;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #059669;
        font-weight: 600;
    }
    .status-dot {
        width: 7px; height: 7px;
        border-radius: 50%;
        background: #10b981;
        box-shadow: 0 0 0 3px rgba(16,185,129,0.2);
        animation: pulse 2.4s ease-in-out infinite;
        flex-shrink: 0;
    }
    @keyframes pulse {
        0%, 100% { box-shadow: 0 0 0 2px rgba(16,185,129,0.2), 0 0 6px rgba(16,185,129,0.3); }
        50%       { box-shadow: 0 0 0 4px rgba(16,185,129,0.1), 0 0 14px rgba(16,185,129,0.5); }
    }

    /* ── FILE ROW IN LIBRARY ── */
    .file-row {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 11px 16px;
        background: var(--glass-bg);
        border: 1px solid rgba(0,0,0,0.1);
        border-radius: var(--radius-sm);
        margin-bottom: 8px;
        transition: all 0.2s ease;
        cursor: default;
    }
    .file-row:hover {
        background: rgba(0,0,0,0.04);
        border-color: rgba(0,0,0,0.2);
        box-shadow: var(--shadow-sm);
    }
    .file-row .file-name {
        font-size: 0.88rem;
        font-weight: 500;
        color: var(--slate-mid);
        flex: 1;
    }
    .file-row .file-ext {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        background: rgba(0,0,0,0.1);
        color: var(--teal-deeper);
        border-radius: 4px;
        padding: 2px 7px;
    }

    /* ── CHAT EMPTY STATE ── */
    .chat-empty {
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        padding: 100px 20px 60px; text-align: center;
    }
    .chat-empty-icon {
        width: 64px; height: 64px; border-radius: 16px;
        background: #212121; border: 1px solid #424242;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.8rem; margin-bottom: 24px; color: #ececec !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    }
    .chat-empty-title {
        font-size: 1.5rem !important; font-weight: 600 !important; color: #ececec !important;
        margin-bottom: 12px !important; letter-spacing: -0.02em !important;
    }
    .chat-empty-sub {
        font-size: 0.95rem !important; color: #888888 !important; line-height: 1.6 !important;
        max-width: 420px; margin: 0 auto !important;
    }

    /* ── CAPABILITY CARDS ── */
    .cap-grid {
        display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;
        max-width: 900px; margin: 0 auto 40px; padding: 0 20px;
    }
    .cap-card {
        background: #171717; border: 1px solid #2b2b2b; border-radius: 12px;
        padding: 20px; text-align: left; transition: all 0.2s ease;
    }
    .cap-card:hover {
        background: #212121; border-color: #424242; box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    }
    .cap-header {
        display: flex; align-items: center; gap: 10px; margin-bottom: 12px;
    }
    .cap-icon {
        background: #2b2b2b; border: 1px solid #424242; border-radius: 8px;
        width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;
        font-size: 1rem; color: #ececec;
    }
    .cap-title {
        font-size: 1rem !important; font-weight: 600 !important; color: #ececec !important;
    }
    .cap-desc {
        font-size: 0.85rem !important; color: #888888 !important; line-height: 1.5 !important;
    }

    /* ── HEADER HERO BAR ── */
    .hero-bar {
        background: linear-gradient(135deg, rgba(0,0,0,0.06), rgba(0,0,0,0.04));
        border: 1px solid rgba(0,0,0,0.12);
        border-radius: var(--radius-lg);
        padding: 18px 28px;
        margin-bottom: 22px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    /* ── CHECKBOX STYLING (Force white when unticked, red when ticked) ── */
    [data-testid="stCheckbox"] [data-baseweb="checkbox"] input + div {
        background-color: #212121 !important;
        border: 2px solid #525252 !important;
        border-radius: 4px !important;
        transition: all 0.2s ease;
    }
    
    /* When checked -> vibrant red */
    [data-testid="stCheckbox"] [data-baseweb="checkbox"] input:checked + div {
        background-color: #ececec !important;
        border-color: #ececec !important;
    }
    
    /* SVG Checkmark color */
    [data-testid="stCheckbox"] [data-baseweb="checkbox"] svg {
        fill: #171717 !important;
        color: #171717 !important;
    }
</style>
""", unsafe_allow_html=True)


inject_custom_css()


# ============================================================
# 3. API HELPERS
# ============================================================
@st.cache_data(ttl=60)
def fetch_folder_contents(folder_id: str):
    try:
        r = httpx.get(f"{API_URL}/list-folder", params={"folder_id": folder_id}, timeout=15.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def get_file_icon(ext: str) -> str:
    ext = ext.lower()
    if ext == "pdf":               return "📕"
    elif ext in ["docx", "doc"]:   return "📘"
    elif ext in ["pptx", "ppt"]:   return "📙"
    elif ext in ["mp4","mkv","avi","mov"]: return "🎬"
    elif ext in ["mp3","wav","m4a"]: return "🎵"
    elif ext in ["png","jpg","jpeg","gif"]: return "🖼️"
    elif ext in ["xlsx","csv"]:    return "📊"
    else:                          return "📄"


current_folder = st.session_state.folder_history[-1]
contents = fetch_folder_contents(current_folder["id"])


# ============================================================
# 4. SLIM SIDEBAR — Context Selection + Clear Chat only
# ============================================================
with st.sidebar:
    # Status pill
    st.markdown("""
<div class="status-online">
    <div class="status-dot"></div>
    System Online
</div>
""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🔍 Context Selection")
    st.caption("Files included in Contextual AI Search")

    # Build file options from current folder listing
    current_folder_files = []
    if contents.get("status") == "success":
        current_folder_files = [f["name"] for f in contents.get("files", [])]

    # The sidebar ONLY displays already-selected files so that the user can remove them.
    # It does not allow adding new unselected files from the current folder.
    def sync_from_sidebar():
        # Update the global set to match the items currently selected in the sidebar widget
        st.session_state.selected_files = set(st.session_state["sidebar_multi"])

    current_selection = list(st.session_state.selected_files)

    if current_selection:
        # Pre-populate the widget state before rendering so it reflects new checkbox taps
        st.session_state["sidebar_multi"] = current_selection
        
        st.multiselect(
            "Select files",
            options=current_selection,
            key="sidebar_multi",
            label_visibility="collapsed",
            help="View or remove files from your accumulated search context",
            on_change=sync_from_sidebar
        )
    else:
        st.caption("No files currently available or selected.")

    st.divider()

    # Search Mode Toggle
    st.markdown("### 🔭 Search Mode")
    search_mode = st.radio(
        "Mode",
        options=["🎯 Contextual Search", "🌍 Global Drive Search"],
        label_visibility="collapsed"
    )

    st.divider()

    # Clear Chat
    st.markdown("### 💬 Chat History")
    st.markdown(f"<small style='color:#64748b'>{len(st.session_state.messages)} messages</small>", unsafe_allow_html=True)
    st.markdown("<div class='danger-btn'>", unsafe_allow_html=True)
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# 5b. PRE-RENDER: Process any pending AI response BEFORE drawing tabs
#     This ensures all messages are in session_state when the tab renders,
#     so history always flows top-to-bottom with input at the very bottom.
# ============================================================
if st.session_state.get("_pending_prompt"):
    prompt = st.session_state.pop("_pending_prompt")
    payload = {
        "question": prompt,
        "search_mode": search_mode,
        "target_files": list(st.session_state.selected_files)
    }
    with st.spinner("Analyzing your knowledge base..."):
        try:
            response = httpx.post(f"{API_URL}/ask", json=payload, timeout=60.0)
            if response.status_code == 422:
                response = httpx.post(f"{API_URL}/ask",
                                      json={"question": prompt}, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            answer = data.get("answer", "No answer found.")
            sources = data.get("sources", [])
            # Build full answer string including sources so it stores cleanly
            full_answer = answer
            if sources:
                src_lines = "\n\n**Sources:**\n" + "\n".join(
                    f"- [{s.get('file_name','Source')}]({s.get('file_path','#')})"
                    for s in sources
                )
                full_answer += src_lines
            st.session_state.messages.append({"role": "assistant", "content": full_answer})
        except Exception as e:
            err = f"⚠️ Could not connect to Copilot backend: {str(e)}"
            st.session_state.messages.append({"role": "assistant", "content": err})

# ============================================================
# 6. TABS
# ============================================================
tab_chat, tab_library = st.tabs(["💬 AI Copilot", "📚 Knowledge Library"])

# ────────────────────────────────────────────────────────────
# TAB 1 — AI COPILOT CHAT
# ────────────────────────────────────────────────────────────
with tab_chat:

    # — Active context pills —
    if st.session_state.selected_files and search_mode == "🎯 Contextual Search":
        selected_list = list(st.session_state.selected_files)
        pills_html = " ".join(
            f"<span class='context-pill'>📎 {f}</span>"
            for f in selected_list[:5]
        )
        extra = ""
        if len(selected_list) > 5:
            extra = f"<span class='context-pill'>+{len(selected_list)-5} more</span>"
        st.markdown(
            f"<div style='margin-bottom:14px;'><small style='color:#64748b;font-weight:600;'>"
            f"🎯 Searching in:</small><br>{pills_html}{extra}</div>",
            unsafe_allow_html=True
        )
    elif search_mode == "🌍 Global Drive Search":
        st.markdown(
            "<div style='margin-bottom:14px;'><span class='context-pill'>🌍 Global Drive Search — all indexed documents</span></div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "<div style='margin-bottom:14px;'><span style='color:#f59e0b;font-size:0.82rem;font-weight:500;'>"
            "⚠️ No files selected — results may be empty in Contextual mode.</span></div>",
            unsafe_allow_html=True
        )

    if not st.session_state.messages:
        st.markdown("""
<div class="chat-empty">
    <div class="chat-empty-icon">⚡</div>
    <div class="chat-empty-title">Copilot is ready</div>
    <div class="chat-empty-sub">
        Your intelligent knowledge agent is connected and standing by.<br>
        Search across your SharePoint library or ask a direct question to begin.
    </div>
</div>

<div class="cap-grid">
    <div class="cap-card">
        <div class="cap-header">
            <div class="cap-icon">🔍</div>
            <div class="cap-title">Semantic Retrieval</div>
        </div>
        <div class="cap-desc">Goes beyond keyword matching. Understands intent and context to surface the most relevant passages across your documents.</div>
    </div>
    <div class="cap-card">
        <div class="cap-header">
            <div class="cap-icon">📎</div>
            <div class="cap-title">Cited Answers</div>
        </div>
        <div class="cap-desc">Every response is grounded in your actual documents with traceable source references — verify and trust the output.</div>
    </div>
    <div class="cap-card">
        <div class="cap-header">
            <div class="cap-icon">📁</div>
            <div class="cap-title">Scoped Search</div>
        </div>
        <div class="cap-desc">Focus on selected files with Contextual mode, or sweep your entire SharePoint drive with Global mode.</div>
    </div>
</div>
""", unsafe_allow_html=True)
    else:
        for msg in st.session_state.messages:
            avatar = "👤" if msg["role"] == "user" else "🤖"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

    # — Chat Input (always appears after all history) —
    if prompt := st.chat_input("Ask Copilot anything about your knowledge base..."):
        # Append user message & queue for API call, then rerun
        # (API is processed at the TOP of the next run, before tabs render)
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state["_pending_prompt"] = prompt
        st.rerun()


# ============================================================
# 7. TAB 2 — KNOWLEDGE LIBRARY
# ============================================================
with tab_library:

    # — Breadcrumb + Back —
    crumb_col, back_col = st.columns([5, 1])
    with crumb_col:
        path_names = [f["name"] for f in st.session_state.folder_history]
        breadcrumb = " › ".join(path_names)
        st.markdown(
            f"<div style='font-size:0.82rem;color:#64748b;font-weight:500;padding:6px 0;'>"
            f"📁 {breadcrumb}</div>",
            unsafe_allow_html=True
        )
    with back_col:
        if len(st.session_state.folder_history) > 1:
            st.markdown("<div class='back-btn'>", unsafe_allow_html=True)
            if st.button("⬅ Back", use_container_width=True):
                st.session_state.folder_history = st.session_state.folder_history[:-1]
                st.cache_data.clear()
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # — Upload Section —
    with st.expander("＋ Add Knowledge  —  Upload a document to your SharePoint Drive", expanded=False):
        up_l, up_r = st.columns([3, 1])
        with up_l:
            uploaded_file = st.file_uploader(
                "Drag & drop or browse",
                type=["pdf", "docx", "pptx", "mp4", "mkv", "avi", "mov", "mp3", "wav", "m4a"],
                label_visibility="visible",
                key=f"uploader_{st.session_state.uploader_key}"
            )
        with up_r:
            if uploaded_file is not None:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("<div class='primary-btn'>", unsafe_allow_html=True)
                if st.button("🚀 Upload to SharePoint", use_container_width=True):
                    with st.spinner(f"Storing {uploaded_file.name} in SharePoint..."):
                        try:
                            files = {
                                "file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
                            }
                            data = {"uploaded_by": "Streamlit User"}
                            resp = httpx.post(
                                f"{API_URL}/upload",
                                params={"folder_id": current_folder["id"]}, 
                                data=data,
                                files=files,
                                timeout=120.0
                            )
                            resp.raise_for_status()

                            st.success(f"✅ **{uploaded_file.name}** stored in SharePoint!")
                            st.info("🤖 The Agent is indexing this document in the background. It will be searchable in moments.")
                            st.toast("Background indexing started!", icon="🚀")

                            st.session_state.uploader_key += 1
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Upload failed: {str(e)}")
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown(
                    "<br><small style='color:#94a3b8;'>Select a file to enable upload.</small>",
                    unsafe_allow_html=True
                )

    st.markdown("<br>", unsafe_allow_html=True)

    # — Folder/File Listing —
    if contents.get("status") == "success":
        folders = contents.get("folders", [])
        files   = contents.get("files",   [])

        # FOLDERS — Drive-style grid (4 per row)
        if folders:
            st.markdown(
                "<div style='font-size:0.78rem;font-weight:700;letter-spacing:0.12em;"
                "text-transform:uppercase;color:#64748b;margin-bottom:14px;'>📂 Folders</div>",
                unsafe_allow_html=True
            )
            cols = st.columns(4)
            for idx, f in enumerate(folders):
                col = cols[idx % 4]
                with col:
                    child_count = f.get("child_count", 0)
                    st.markdown("<div class='folder-card-btn'>", unsafe_allow_html=True)
                    if st.button(
                        f"📁\n\n{f['name']}\n\n{child_count} items",
                        key=f"folder_{f['id']}",
                        use_container_width=True
                    ):
                        st.session_state.folder_history = (
                            st.session_state.folder_history
                            + [{"id": f["id"], "name": f["name"]}]
                        )
                        st.cache_data.clear()
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

        # FILES — clean list
        if files:
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Select/Deselect All Header Row
            hdr_l, hdr_m, hdr_r = st.columns([6, 3, 3])
            with hdr_l:
                st.markdown(
                    "<div style='font-size:0.78rem;font-weight:700;letter-spacing:0.12em;"
                    "text-transform:uppercase;color:#64748b;padding-top:10px;'>"
                    f"📄 Files ({len(files)})</div>",
                    unsafe_allow_html=True
                )
                
            def select_all(file_list):
                for fl in file_list:
                    st.session_state.selected_files.add(fl['name'])
                    st.session_state[f"chk_{fl['id']}"] = True

            def deselect_all(file_list):
                for fl in file_list:
                    st.session_state.selected_files.discard(fl['name'])
                    st.session_state[f"chk_{fl['id']}"] = False
                    
            def toggle_item(fname, ckey):
                if st.session_state[ckey]:
                    st.session_state.selected_files.add(fname)
                else:
                    st.session_state.selected_files.discard(fname)

            with hdr_m:
                st.button("☑️ Select All", use_container_width=True, on_click=select_all, args=(files,))
            with hdr_r:
                st.button("🔲 Deselect All", use_container_width=True, on_click=deselect_all, args=(files,))
                
            st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

            for f in files:
                ext  = f.get("extension", "").lower()
                icon = get_file_icon(ext)
                size_kb = f.get("size", 0) // 1024
                size_str = f"{size_kb:,} KB" if size_kb else ""
                web_url  = f.get("webUrl", "#")
                
                chk_key = f"chk_{f['id']}"
                
                # Unidirectional state sync: If key doesn't exist, initialize it from global set
                if chk_key not in st.session_state:
                    st.session_state[chk_key] = f['name'] in st.session_state.selected_files
                
                row_col_chk, row_col_file = st.columns([0.5, 12])
                with row_col_chk:
                    st.markdown("<div style='margin-top:20px;'>", unsafe_allow_html=True)
                    st.checkbox("sel", key=chk_key, label_visibility="collapsed", on_change=toggle_item, args=(f['name'], chk_key))
                    st.markdown("</div>", unsafe_allow_html=True)
                
                with row_col_file:
                    st.markdown(f"""
<div class="file-row">
    <span style="font-size:1.4rem;">{icon}</span>
    <span class="file-name"><a href="{web_url}" target="_blank"
          style="color:#334155;text-decoration:none;">{f['name']}</a></span>
    {f'<span class="file-ext">{ext}</span>' if ext else ""}
    <span style="font-size:0.78rem;color:#94a3b8;">{size_str}</span>
</div>
""", unsafe_allow_html=True)

        if not folders and not files:
            st.markdown("""
<div class="empty-state">
    <div class="emoji">📭</div>
    <p style="font-size:1rem;font-weight:600;color:#334155;">This folder is empty</p>
    <p>Upload a document using the button above.</p>
</div>
""", unsafe_allow_html=True)

    else:
        st.error(f"⚠️ Failed to load folder contents: {contents.get('detail', 'Unknown error')}")
        if st.button("🔄 Retry"):
            st.cache_data.clear()
            st.rerun()
