import os
import streamlit as st
import requests
import time
import uuid
import logfire
from dotenv import load_dotenv

# Load environment variables explicitly from root directory
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(dotenv_path=env_path)

# Initialize Logfire
try:
    token = os.getenv("LOGFIRE_TOKEN")
    logfire.configure(token=token, service_name="enterprise-rag-ui", inspect_arguments=False)
    logfire.instrument_requests()
    LOGFIRE_STATUS = "Connected & Tracing"
    LOGFIRE_COLOR = "success"
except Exception as e:
    LOGFIRE_STATUS = "Standby (No Token)"
    LOGFIRE_COLOR = "warning"


# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Enterprise Agentic RAG OS",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --- CUSTOM DESIGN SYSTEM (CSS) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Dark Slate Glassmorphism Background */
.stApp {
    background: radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.08) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(168, 85, 247, 0.08) 0%, transparent 40%),
                #0b0f17;
    color: #f3f4f6;
}

/* Header Container */
.hero-header {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.8) 100%);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 22px 28px;
    margin-bottom: 24px;
    box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
}

.hero-title {
    font-size: 1.85rem;
    font-weight: 700;
    background: linear-gradient(135deg, #818cf8 0%, #c084fc 50%, #e879f9 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
    letter-spacing: -0.02em;
}

.hero-subtitle {
    color: #94a3b8;
    font-size: 0.92rem;
    margin-top: 4px;
    margin-bottom: 0;
}

/* Status Badges */
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}
.pill-active {
    background: rgba(16, 185, 129, 0.12);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.3);
}
.pill-purple {
    background: rgba(168, 85, 247, 0.12);
    color: #c084fc;
    border: 1px solid rgba(168, 85, 247, 0.3);
}
.pill-indigo {
    background: rgba(99, 102, 241, 0.12);
    color: #818cf8;
    border: 1px solid rgba(99, 102, 241, 0.3);
}

/* Reasoning Step Cards */
.thought-card {
    background: rgba(30, 41, 59, 0.4);
    border-left: 3px solid #6366f1;
    border-radius: 4px 8px 8px 4px;
    padding: 8px 14px;
    margin-bottom: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    color: #cbd5e1;
}

/* Source Card Styling */
.source-block {
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 14px;
    margin-top: 8px;
    font-size: 0.88rem;
    color: #e2e8f0;
}

/* Sidebar Custom Styling */
section[data-testid="stSidebar"] {
    background-color: #0f172a !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
}

/* Chat Input Rounded Glass Styling */
div[data-testid="stChatInput"] {
    border-radius: 14px !important;
}
div[data-testid="stChatInput"] input {
    background-color: #1e293b !important;
    color: #f8fafc !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    border-radius: 12px !important;
}
</style>
""", unsafe_allow_html=True)


# --- SESSION MANAGEMENT ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    logfire.info(f"✨ New User Session Created: {st.session_state.session_id}")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "preset_prompt" not in st.session_state:
    st.session_state.preset_prompt = None


# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
        <span style="font-size: 1.8rem;">🧠</span>
        <div>
            <h3 style="margin: 0; font-size: 1.2rem; color: #f8fafc; font-weight: 700;">Agent OS</h3>
            <span style="font-size: 0.75rem; color: #94a3b8;">Enterprise RAG Engine</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # Backend Health Check
    base_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    backend_status = "Offline"
    try:
        r = requests.get(f"{base_url}/", timeout=3)
        if r.status_code == 200:
            backend_status = "Online & Ready"
    except Exception:
        backend_status = "Unreachable"

    if backend_status == "Online & Ready":
        st.success(f"🟢 Backend: {backend_status}")
    else:
        st.error(f"🔴 Backend: {backend_status}")

    st.info(f"🛡️ Logfire: {LOGFIRE_STATUS}")
    st.caption(f"🔑 Session Thread: `{st.session_state.session_id[:8]}...`")

    st.markdown("---")
    st.markdown("### 💡 Quick Prompts")

    presets = [
        "What is Kubernetes architecture and scheduler?",
        "Explain SRIOV and Intel NIC networking.",
        "How does horizontal pod autoscaling work?",
        "Can you write a poem about stars?" # Test guardrails
    ]

    for p in presets:
        if st.button(f"👉 {p}", use_container_width=True):
            st.session_state.preset_prompt = p

    st.markdown("---")
    if st.button("🗑️ Clear Conversation & Memory", type="primary", use_container_width=True):
        logfire.warning(f"🗑️ Memory Wipe Triggered for session: {st.session_state.session_id}")
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.preset_prompt = None
        st.rerun()


# --- HERO TOP HEADER ---
st.markdown(f"""
<div class="hero-header">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
        <div>
            <h1 class="hero-title">⚡ Enterprise Agentic Assistant</h1>
            <p class="hero-subtitle">Self-Correcting RAG Architecture with NeMo Guardrails & Qdrant Semantic Search</p>
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <span class="status-pill pill-active">● API Live</span>
            <span class="status-pill pill-purple">⚡ Groq GPT-OSS</span>
            <span class="status-pill pill-indigo">🔍 Qdrant Vector DB</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# --- DISPLAY CHAT HISTORY ---
AI_AVATAR = "🤖"
USER_AVATAR = "👤"

for msg in st.session_state.messages:
    avatar = AI_AVATAR if msg["role"] == "assistant" else USER_AVATAR
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        
        # Display saved thought process if available
        if msg.get("thought_process"):
            with st.expander("⚙️ Reasoning & Routing Steps", expanded=False):
                for step in msg["thought_process"]:
                    st.markdown(f"<div class='thought-card'>⚙️ {step}</div>", unsafe_allow_html=True)
        
        # Display saved sources if available
        if msg.get("sources"):
            sources_list = msg["sources"]
            with st.expander(f"📄 Retrieved Context ({len(sources_list)} Chunks)", expanded=False):
                tabs = st.tabs([f"Chunk {i+1}" for i in range(len(sources_list))])
                for i, tab in enumerate(tabs):
                    with tab:
                        st.info(sources_list[i])


# --- CAPTURE INPUT (DIRECT OR VIA PRESET) ---
prompt = st.chat_input("Ask a question about Kubernetes, Intel hardware, or networking...")

if st.session_state.preset_prompt:
    prompt = st.session_state.preset_prompt
    st.session_state.preset_prompt = None


# --- PROCESS QUERY ---
if prompt:
    with logfire.span("💬 User Interaction", query=prompt, session_id=st.session_state.session_id):
        # 1. Render User Message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(prompt)

        # 2. Process Assistant Response
        with st.chat_message("assistant", avatar=AI_AVATAR):
            data = {}
            with st.status("🧠 Agent Reasoning & Synthesizing...", expanded=True) as status:
                try:
                    url = f"{base_url}/query"
                    payload = {"q": prompt, "thread_id": st.session_state.session_id}
                    
                    start_time = time.time()
                    response = requests.post(url, json=payload, timeout=90)
                    elapsed = round(time.time() - start_time, 2)

                    if response.status_code != 200:
                        st.error(f"Backend Server Returned Error Status {response.status_code}")
                        status.update(label="❌ Execution Failed", state="error", expanded=True)
                        st.stop()

                    data = response.json()

                    # Render thought process steps in live status
                    steps = data.get("thought_process", [])
                    for step in steps:
                        st.markdown(f"<div class='thought-card'>⚙️ {step}</div>", unsafe_allow_html=True)

                    status.update(label=f"✅ Response Synthesized ({elapsed}s)", state="complete", expanded=False)

                except requests.exceptions.ConnectionError:
                    logfire.error("Backend Connection Error")
                    status.update(label="❌ Backend Offline", state="error", expanded=True)
                    st.error("Cannot connect to FastAPI backend on `http://localhost:8000`. Please start the server.")
                    st.stop()
                except Exception as e:
                    logfire.error(f"Execution Error: {e}")
                    status.update(label="❌ Execution Exception", state="error", expanded=True)
                    st.error(f"An unexpected error occurred: {e}")
                    st.stop()

            # Render Final Output Answer
            answer_placeholder = st.empty()
            full_answer = data.get("answer", "No response generated by assistant.")
            answer_placeholder.markdown(full_answer)

            # Render Retrieved Sources
            sources = data.get("sources", [])
            thought_process = data.get("thought_process", [])

            if sources:
                with st.expander(f"📄 Retrieved Context ({len(sources)} Chunks)", expanded=False):
                    tabs = st.tabs([f"Chunk {i+1}" for i in range(len(sources))])
                    for i, tab in enumerate(tabs):
                        with tab:
                            st.info(sources[i])
            else:
                st.caption("ℹ️ Conversational / Memory Response (No Vector DB Retrieval Required)")

            # Save full message state including metadata for history
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_answer,
                "thought_process": thought_process,
                "sources": sources
            })
            logfire.info("✅ Interaction completed successfully.")

