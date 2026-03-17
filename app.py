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


# 2. UI/UX & CUSTOM CSS INJECTION
def inject_custom_css():
    st.markdown("""
<style>
    /* Hide default Streamlit components except the header which contains the sidebar toggle! */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppDeployButton {display:none;}
    
    /* Modern Typography Standardization */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
    html, body, [class*="css"], .stMarkdown {
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Sidebar Styling for Mac Finder / VS Code Feel */
    [data-testid="stSidebar"] {
        background-color: var(--secondary-background-color) !important;
        border-right: 1px solid rgba(128,128,128,0.2) !important;
    }

    /* Sleek buttons for folders */
    div.stButton > button {
        width: 100%;
        text-align: left;
        border: none;
        background: transparent;
        padding: 6px 10px;
        font-weight: 500;
        justify-content: flex-start;
        box-shadow: none;
        transition: background-color 0.2s ease, border-radius 0.2s;
        border-radius: 6px;
    }
    div.stButton > button:hover {
        background-color: rgba(128, 128, 128, 0.15);
        color: var(--text-color);
        border: none;
    }
    div.stButton > button:focus:not(:focus-visible) {
        color: var(--text-color);
        background: transparent;
    }

    /* Floating Chat Input */
    [data-testid="stChatInput"] {
        border-radius: 12px;
        box-shadow: 0px 4px 16px rgba(0,0,0,0.1);
        border: 1px solid rgba(128,128,128,0.2) !important;
    }
    
    /* Hide block container top padding to fill screen more cleanly */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
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
st.markdown("<h1 style='text-align: center; font-weight: 600; margin-bottom: -10px;'>🤖 Copilot Agent</h1>", unsafe_allow_html=True)

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
if prompt := st.chat_input("Ask Copilot anything..."):
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
