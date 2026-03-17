import streamlit as st
import httpx

# 1. CORE ARCHITECTURE & STATE
st.set_page_config(
    page_title="Copilot Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_URL = "http://127.0.0.1:8000"

if "folder_history" not in st.session_state:
    st.session_state.folder_history = [{"id": "root", "name": "root"}]
if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected_files" not in st.session_state:
    st.session_state.selected_files = []
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0


# 2. UI/UX & CUSTOM CSS INJECTION
def inject_custom_css():
    st.markdown("""
<style>
    /* HIDE STREAMLIT CHROME & FIX ALIGNMENTS */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stAppDeployButton { display: none !important; }

    /* GLOBAL THEME: TEAL & WHITE */
    :root {
        --teal-light: #f0fdfa;
        --teal-main: #0d9488;
        --teal-dark: #115e59;
        --text-color: #0f172a;
        --bg-white: #ffffff;
        --border-color: #ccfbf1;
    }

    html, body, [class*="css"], .stMarkdown {
        font-family: 'Inter', sans-serif !important;
        color: var(--text-color) !important;
    }

    /* Force Light Mode Overrides */
    .stApp, .main {
        background-color: var(--teal-light) !important;
    }

    h1, h2, h3, h4, .stMarkdown h1, .stMarkdown h3 {
        color: var(--teal-dark) !important;
        font-weight: 800 !important;
    }
    
    p, span, label, div {
        color: var(--text-color) !important;
    }

    /* COLLAPSED SIDEBAR TOGGLE BUTTON FIX */
    [data-testid="collapsedControl"] {
        color: var(--teal-main) !important;
        background-color: var(--bg-white) !important;
        border-radius: 50% !important;
        border: 1px solid var(--border-color) !important;
        box-shadow: 0 4px 6px -1px rgba(13, 148, 136, 0.1) !important;
    }
    [data-testid="collapsedControl"] svg {
        fill: var(--teal-main) !important;
        color: var(--teal-main) !important;
    }

    /* SIDEBAR */
    [data-testid="stSidebar"] {
        background-color: var(--bg-white) !important;
        border-right: 1px solid var(--border-color) !important;
    }
    
    [data-testid="stSidebar"] h3 {
        color: var(--teal-main) !important;
        font-weight: 700 !important;
        margin-bottom: -5px;
    }

    [data-testid="stSidebar"] .stCaption {
        color: var(--teal-dark) !important;
        background: var(--teal-light);
        padding: 5px 10px;
        border-radius: 5px;
        border-left: 2px solid var(--teal-main);
    }

    /* FOLDER BUTTONS */
    div.stButton > button {
        width: 100%;
        text-align: left;
        background: transparent;
        border: 1px solid transparent;
        padding: 8px 12px;
        color: var(--text-color) !important;
        justify-content: flex-start;
        border-radius: 8px;
        transition: all 0.2s;
        box-shadow: none !important;
    }
    
    div.stButton > button:hover {
        background-color: var(--teal-light) !important;
        border: 1px solid var(--border-color) !important;
        color: var(--teal-main) !important;
    }
    div.stButton > button p {
        color: inherit !important;
    }

    /* PRIMARY UPLOAD BUTTON */
    [data-testid="stExpander"] div.stButton > button {
        background-color: var(--teal-main) !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        text-align: center !important;
        justify-content: center !important;
    }
    [data-testid="stExpander"] div.stButton > button:hover {
        background-color: var(--teal-dark) !important;
    }
    [data-testid="stExpander"] div.stButton > button p {
        color: #ffffff !important;
    }

    /* EXPANDER FIX */
    [data-testid="stExpander"] {
        background-color: var(--bg-white) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 10px;
    }
    [data-testid="stExpander"] summary {
        color: var(--teal-dark) !important;
        font-weight: 600 !important;
    }
    [data-testid="stExpander"] summary p {
        color: var(--teal-dark) !important;
    }
    [data-testid="stFileUploader"], 
    [data-testid="stFileUploadDropzone"] {
        background-color: var(--bg-white) !important;
        border-radius: 10px !important;
    }
    [data-testid="stFileUploader"] {
        border: 2px dashed var(--teal-main) !important;
    }
    [data-testid="stFileUploader"] p, 
    [data-testid="stFileUploader"] small,
    [data-testid="stFileUploadDropzone"] div,
    [data-testid="stFileUploadDropzone"] span {
        color: var(--teal-dark) !important;
    }
    [data-testid="stFileUploadDropzone"] button {
        background-color: var(--teal-light) !important;
        color: var(--teal-dark) !important;
        border: 1px solid var(--teal-main) !important;
    }

    /* MULTISELECT FIX */
    .stMultiSelect label p {
        color: var(--teal-dark) !important;
        font-weight: 600 !important;
    }
    .stMultiSelect div[data-baseweb="select"] {
        background-color: var(--bg-white) !important;
        border: 1px solid var(--border-color) !important;
    }
    span[data-baseweb="tag"] {
        background-color: var(--teal-light) !important;
        color: var(--teal-dark) !important;
        border: 1px solid var(--border-color) !important;
    }

    /* LABEL FIX FOR ENTERPRISE TEXT */
    div[style*="Enterprise Intelligence"] {
        color: var(--teal-main) !important;
        background: var(--teal-light) !important;
        border: 1px solid var(--border-color) !important;
    }

    /* RADIO BUTTONS (SEARCH MODE) FIX */
    .stRadio {
        display: flex;
        justify-content: center;
        background-color: transparent !important;
        margin-top: 10px;
    }
    .stRadio > div {
        flex-direction: row;
        gap: 15px;
        background: var(--bg-white);
        padding: 5px 15px;
        border-radius: 30px;
        border: 1px solid var(--border-color);
        box-shadow: 0 4px 6px -1px rgba(13, 148, 136, 0.1);
    }
    .stRadio label {
        color: var(--teal-dark) !important;
        font-weight: 600 !important;
        background: transparent !important;
    }
    .stRadio label div {
        color: var(--teal-dark) !important;
    }

    /* CHAT MESSAGES */
    [data-testid="stChatMessage"] {
        background-color: var(--bg-white) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        margin-bottom: 20px;
    }
    [data-testid="stChatMessage"][data-role="user"] {
        background-color: #e0f2fe !important; /* Soft blue to contrast with teal */
        border: 1px solid #bae6fd !important;
    }
    [data-testid="stChatMessage"] code {
        color: var(--teal-dark) !important;
        background: var(--teal-light) !important;
    }
    [data-testid="stChatMessage"] a {
        color: var(--teal-main) !important;
        font-weight: 600;
    }

    /* AVATARS */
    [data-testid="chatAvatarIcon-assistant"] {
        background-color: var(--teal-main) !important;
        border: none !important;
    }
    
    /* CHAT INPUT */
    [data-testid="stChatInput"] {
        border: 2px solid var(--border-color) !important;
        border-radius: 15px !important;
        background-color: var(--bg-white) !important;
        box-shadow: 0 -4px 15px rgba(0,0,0,0.05) !important;
    }
    [data-testid="stChatInput"] textarea, [data-testid="stChatInput"] input {
        color: var(--teal-dark) !important;
        background-color: var(--bg-white) !important;
    }
    [data-testid="stChatInput"] textarea::placeholder {
        color: #94a3b8 !important;
    }
    [data-testid="stChatInput"] button {
        background-color: var(--teal-main) !important;
        color: #ffffff !important;
        border-radius: 8px !important;
    }
    [data-testid="stChatInput"] button svg {
        fill: #ffffff !important;
        color: #ffffff !important;
    }

    /* CLEANUP */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 5rem !important;
    }
    hr {
        border-top: 1px solid var(--border-color) !important;
        background: transparent !important;
    }
</style>
""", unsafe_allow_html=True)


def inject_header_html():
    """Inject a clean status pill into the sidebar."""
    st.sidebar.markdown("""
<div style="
    display: inline-flex;
    align-items: center;
    gap: 7px;
    margin-bottom: 8px;
    background: linear-gradient(135deg, rgba(16,185,129,0.08), rgba(16,185,129,0.04));
    border: 1px solid rgba(16,185,129,0.22);
    border-radius: 999px;
    padding: 5px 12px 5px 9px;
">
    <div style="
        width: 7px; height: 7px;
        border-radius: 50%;
        background: #10b981;
        box-shadow: 0 0 0 2px rgba(16,185,129,0.25), 0 0 8px rgba(16,185,129,0.4);
        animation: statusPulse 2.4s ease-in-out infinite;
        flex-shrink: 0;
    "></div>
    <span style="
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.62rem;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: #059669;
        font-weight: 500;
    ">System Online</span>
</div>
<style>
@keyframes statusPulse {
    0%, 100% { box-shadow: 0 0 0 2px rgba(16,185,129,0.2), 0 0 6px rgba(16,185,129,0.3); }
    50%       { box-shadow: 0 0 0 4px rgba(16,185,129,0.12), 0 0 14px rgba(16,185,129,0.5); }
}
</style>
""", unsafe_allow_html=True)


inject_custom_css()

# API Helpers
@st.cache_data(ttl=60)
def fetch_folder_contents(folder_id: str):
    try:
        response = httpx.get(f"{API_URL}/list-folder", params={"folder_id": folder_id}, timeout=15.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"status": "error", "detail": str(e)}

current_folder = st.session_state.folder_history[-1]
contents = fetch_folder_contents(current_folder["id"])


# 3. LEFT SIDEBAR: THE KNOWLEDGE EXPLORER
with st.sidebar:
    inject_header_html()

    st.markdown("### 🗂️ Knowledge Base")

    # Breadcrumb
    path_names = [f["name"] for f in st.session_state.folder_history]
    st.caption(" / ".join(path_names))

    # Back Button
    if len(st.session_state.folder_history) > 1:
        if st.button("⬅️ Back"):
            st.session_state.folder_history = st.session_state.folder_history[:-1]
            st.rerun()

    st.divider()

    # --- UPLOAD SECTION ---
    with st.expander("📤 Upload Document", expanded=False):
        uploaded_file = st.file_uploader(
            "Upload a new file to the knowledge base",
            type=["pdf", "docx", "pptx", "mp4", "mkv", "avi", "mov", "mp3", "wav", "m4a"],
            label_visibility="collapsed",
            key=f"uploader_{st.session_state.uploader_key}"
        )
        if uploaded_file is not None:
            if st.button("Start Upload", use_container_width=True):
                with st.spinner(f"Uploading and processing {uploaded_file.name}..."):
                    try:
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        data = {"uploaded_by": "Streamlit User"}

                        # Set a high timeout because embedding and chunking large videos takes time
                        resp = httpx.post(f"{API_URL}/upload", data=data, files=files, timeout=300.0)
                        resp.raise_for_status()

                        st.success("✅ Upload complete!")
                        st.session_state.uploader_key += 1
                        st.rerun()
                    except Exception as e:
                        st.error(f"Upload failed: {str(e)}")

    st.divider()

    file_options = []

    if contents.get("status") == "success":
        folders = contents.get("folders", [])
        files = contents.get("files", [])

        if not folders and not files:
            st.caption("Folder is empty")

        # Folders
        for f in folders:
            label = f"📁 {f['name']} ({f.get('child_count', 0)})"
            if st.button(label, key=f"folder_{f['id']}"):
                st.session_state.folder_history = st.session_state.folder_history + [{"id": f["id"], "name": f["name"]}]
                st.rerun()

        # Files
        for f in files:
            ext = f.get("extension", "unknown").lower()
            icon = "📄"
            if ext == "pdf": icon = "📕"
            elif ext in ["docx", "doc"]: icon = "📘"
            elif ext in ["pptx", "ppt"]: icon = "📙"
            elif ext in ["mp4", "mkv", "avi", "mov"]: icon = "🎬"
            elif ext in ["mp3", "wav", "m4a"]: icon = "🎵"

            st.markdown(f"<div style='padding: 6px 12px; font-size: 14px;'>{icon} {f['name']}</div>", unsafe_allow_html=True)
            file_options.append(f["name"])
    else:
        st.error(f"Failed to load contents: {contents.get('detail')}")

    st.divider()

    # Context Selection
    st.session_state.selected_files = st.multiselect(
        "Context Selection",
        options=file_options,
        default=file_options,
        help="Included in contextual search"
    )


# 4. MAIN AREA: THE COPILOT INTERFACE

# Premium eyebrow label
st.markdown("""
<div style="text-align: center; padding: 1.2rem 0 0.4rem 0;">
    <div style="
        display: inline-block;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.62rem;
        letter-spacing: 0.24em;
        text-transform: uppercase;
        color: #4f46e5;
        background: linear-gradient(135deg, rgba(79,70,229,0.07), rgba(14,165,233,0.05));
        border: 1px solid rgba(79,70,229,0.18);
        border-radius: 999px;
        padding: 5px 16px;
        margin-bottom: 10px;
        font-weight: 500;
    ">Enterprise Intelligence Platform</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; font-weight: 800; margin-bottom: -10px;'>🤖 Copilot Agent</h1>", unsafe_allow_html=True)

# Search mode toggle
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    search_mode = st.radio(
        "Search Mode",
        options=["🎯 Contextual Search", "🌍 Global Drive Search"],
        horizontal=True,
        label_visibility="collapsed"
    )

st.divider()

# Render chat layout
for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# Chat Input & Form Processing
if prompt := st.chat_input("Ask Copilot anything about your knowledge base..."):
    # Append user prompt
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # Process backend request
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Analyzing Knowledge Base..."):
            payload = {
                "question": prompt,
                "search_mode": search_mode,
                "target_files": st.session_state.selected_files
            }
            try:
                response = httpx.post(f"{API_URL}/ask", json=payload, timeout=60.0)

                # Check for 422 if FastAPI strictly rejects extra fields on standard `str = Body()` definitions
                if response.status_code == 422:
                    fallback_payload = {"question": prompt}
                    response = httpx.post(f"{API_URL}/ask", json=fallback_payload, timeout=60.0)

                response.raise_for_status()
                data = response.json()

                answer = data.get("answer", "No answer found.")
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})

                # Display Sources If Any
                sources = data.get("sources", [])
                if sources:
                    st.caption("**Sources:**")
                    for s in sources:
                        url = s.get('file_path', '#')
                        name = s.get('file_name', 'Source')
                        st.markdown(f"- [{name}]({url})")

            except Exception as e:
                st.toast(f"Connection Error: {str(e)}", icon="🚨")
                error_msg = "Oops! Having trouble connecting to the Copilot backend. Please try again."
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})