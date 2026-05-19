import os
import sys

# Fix for Streamlit Cloud SQLite version requirement by ChromaDB
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

# Disable CrewAI telemetry BEFORE any crewai imports to avoid signal handler errors
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"

import streamlit as st
try:
    from dotenv import load_dotenv
except ImportError:
    pass
from crewai import Agent, Task, Crew, LLM
from crewai.tools import tool
from crewai_tools import SerperDevTool
import time
import re
import json
import tempfile
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

USER_DATA_FILE = "users_data.json"
SESSION_FILE = "session_data.json"

def load_data(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except: return {}
    return {}

def save_data(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f)

# Load environment variables
try:
    load_dotenv()
except NameError:
    pass

# Sync API Keys
api_key = os.getenv("GEMINI_API_KEY")
if api_key and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = api_key

# Page configuration
st.set_page_config(
    page_title="Homework Helper Pro ✨",
    page_icon="📚",
    layout="wide"
)

# Custom CSS for premium aesthetics
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Outfit:wght@400;700&display=swap');
    
    :root {
        --primary: #059669;
        --secondary: #0d9488;
        --accent: #f59e0b;
        --glass: rgba(255, 255, 255, 0.7);
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main-header {
        font-family: 'Outfit', sans-serif;
        background: linear-gradient(135deg, #059669 0%, #0d9488 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3.2rem;
        margin: 0;
        display: inline-block;
    }

    .header-emoji {
        display: inline-block;
        margin-right: 15px;
        /* Removed the text-shadow trick so the emoji renders naturally */
        filter: drop-shadow(0 4px 6px rgba(0, 0, 0, 0.1));
    }

    .sub-header {
        color: #64748b;
        font-size: 1.1rem;
        margin-top: -10px;
        margin-bottom: 2rem;
        font-weight: 400;
    }

    /* Auth Buttons Styling */
    .auth-box {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 5px 15px;
        cursor: pointer;
        transition: all 0.2s;
        font-weight: 600;
        color: #059669;
        text-align: center;
        display: inline-block;
        margin-left: 10px;
        font-size: 0.9rem;
    }
    .auth-box:hover {
        border-color: #059669;
        background: #f0fdf4;
    }

    /* Glassmorphism containers */
    .glass-card {
        background: var(--glass);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.05);
        margin-bottom: 2rem;
    }

    /* Input Fields */
    .stTextArea textarea {
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        font-size: 1.1rem;
        transition: all 0.3s ease;
    }

    .stTextArea textarea:focus {
        border-color: transparent !important;
        box-shadow: none !important;
        outline: none !important;
    }

    .stTextArea textarea:hover {
        border-color: #e2e8f0 !important;
    }

    /* Custom Footer Box */
    .footer-box {
        background: transparent;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        margin-top: 3rem;
    }
    .footer-text {
        background: linear-gradient(135deg, #059669 0%, #0d9488 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 1.2rem;
        margin: 0;
        font-family: 'Outfit', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# Data & Session Initialization
users_db = load_data(USER_DATA_FILE)
session_info = load_data(SESSION_FILE)

if 'page' not in st.session_state:
    st.session_state.page = "home"
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = session_info.get("logged_in", False)
if 'user_name' not in st.session_state:
    st.session_state.user_name = session_info.get("user_name", "")
if 'homework_history' not in st.session_state:
    if st.session_state.logged_in and st.session_state.user_name in users_db:
        st.session_state.homework_history = users_db[st.session_state.user_name].get("history", [])
    else:
        st.session_state.homework_history = []
if 'latest_result' not in st.session_state:
    st.session_state.latest_result = None

# Header Navigation Bar
col_title, col_auth = st.columns([3, 1])

with col_title:
    st.markdown("<h1 class='main-header'><span class='header-emoji'>📚</span> Homework Helper Pro</h1>", unsafe_allow_html=True)

with col_auth:
    st.markdown("<div style='text-align: right; padding-top: 15px;'>", unsafe_allow_html=True)
    
    # Navigation Buttons row
    nav_c1, nav_c2, nav_c3 = st.columns([1, 1, 1])
    
    with nav_c1:
        if st.button("🏠 Home", key="nav_home", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()

    if not st.session_state.logged_in:
        with nav_c2:
            if st.button("Login", key="nav_login", use_container_width=True):
                st.session_state.page = "login"
                st.rerun()
        with nav_c3:
            if st.button("Sign Up", key="nav_signup", use_container_width=True):
                st.session_state.page = "signup"
                st.rerun()
    else:
        with nav_c2:
            st.write(f"**{st.session_state.user_name}**")
        with nav_c3:
            if st.button("Logout", key="nav_logout", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.user_name = ""
                st.session_state.homework_history = []
                st.session_state.page = "home"
                save_data(SESSION_FILE, {"logged_in": False, "user_name": ""})
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<p class='sub-header' style='margin-left: 0;'>Experience the future of learning with autonomous AI research agents</p>", unsafe_allow_html=True)

# Page Routing
if st.session_state.page == "login":
    st.markdown("## 🔐 Login to your Account")
    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Login"):
            if user in users_db:
                if users_db[user]["password"] == pwd:
                    st.session_state.logged_in = True
                    st.session_state.user_name = user
                    st.session_state.homework_history = users_db[user].get("history", [])
                    st.session_state.page = "home"
                    save_data(SESSION_FILE, {"logged_in": True, "user_name": user})
                    st.rerun()
                else:
                    st.error("❌ Wrong Password!")
            else:
                st.error("❌ User not found!")
    with c2:
        if st.button("Cancel"):
            st.session_state.page = "home"
            st.rerun()

elif st.session_state.page == "signup":
    st.markdown("## 🆕 Create New Account")
    new_user = st.text_input("Choose Username")
    new_pwd = st.text_input("Choose Password", type="password")
    confirm_pwd = st.text_input("Confirm Password", type="password")
    
    if new_user and new_user in users_db:
        st.info(f"👋 **Hey {new_user}!** It looks like you already have an account with us.")
        st.write("Would you like to use your existing account or create a new one with a different name?")
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("✅ Yes, use my account", use_container_width=True):
                st.session_state.page = "login"
                st.rerun()
        with c2:
            if st.button("❌ No, I'll pick a different name", use_container_width=True):
                # Just clears the input by reloading or letting them edit
                st.rerun()
    else:
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("Create"):
                if new_user and new_pwd == confirm_pwd:
                    users_db[new_user] = {"password": new_pwd, "history": []}
                    save_data(USER_DATA_FILE, users_db)
                    st.session_state.logged_in = True
                    st.session_state.user_name = new_user
                    st.session_state.homework_history = []
                    st.session_state.page = "home"
                    save_data(SESSION_FILE, {"logged_in": True, "user_name": new_user})
                    st.rerun()
                else:
                    st.error("❌ Passwords don't match or fields empty")
        with c2:
            if st.button("Cancel"):
                st.session_state.page = "home"
                st.rerun()

elif st.session_state.page == "home":
    # Sidebar for Config & History
    with st.sidebar:
        st.markdown("<h2 style='text-align: center; color: #059669; font-family: Outfit;'>⚙️ Configuration</h2>", unsafe_allow_html=True)
        st.info("🚀 Experience advanced AI research")
        st.markdown("---")
        
        if st.session_state.homework_history:
            st.markdown("### 🕰️ History")
            if st.button("🗑️ Clear My History", use_container_width=True):
                st.session_state.homework_history = []
                st.session_state.latest_result = None
                if st.session_state.user_name in users_db:
                    users_db[st.session_state.user_name]["history"] = []
                    save_data(USER_DATA_FILE, users_db)
                st.rerun()
                
            for i, item in enumerate(reversed(st.session_state.homework_history)):
                with st.expander(f"📌 {item['title']}"):
                    st.markdown(item["result"])
        else:
            st.caption("No history yet. Start asking!")

    # Main Content
    col_left, col_mid, col_right = st.columns([1, 4, 1])

    with col_mid:
        # Fallback to a placeholder if image is missing for any reason
        st.markdown("<div style='height: 200px; background: transparent; border: 2px dashed rgba(255, 255, 255, 0.2); border-radius: 20px; display: flex; align-items: center; justify-content: center; color: #e2e8f0; font-size: 1.5rem; font-family: Outfit; font-weight: 700;'>✨ Smart Learning Hub</div>", unsafe_allow_html=True)

        st.markdown("### 📚 Study Materials (Optional)")
        study_file = st.file_uploader("Upload textbook, notes, or research papers (PDF/TXT):", type=["pdf", "txt"])
        
        vectorstore = None
        if study_file:
            with st.spinner("🧠 Processing your study materials..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{study_file.name.split('.')[-1]}") as tmp:
                    tmp.write(study_file.getvalue())
                    tmp_path = tmp.name
                try:
                    if study_file.name.endswith(".pdf"):
                        loader = PyPDFLoader(tmp_path)
                    else:
                        loader = TextLoader(tmp_path)
                    docs = loader.load()
                    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=60)
                    chunks = splitter.split_documents(docs)
                    embeddings = GoogleGenerativeAIEmbeddings(
                        model="models/gemini-embedding-001",
                        google_api_key=os.getenv("GEMINI_API_KEY")
                    )
                    vectorstore = Chroma.from_documents(chunks, embeddings)
                    st.success("✅ Materials indexed! Agents will use them for research.")
                except Exception as e:
                    st.error(f"Error processing file: {e}")
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

        st.markdown("### 📝 What do you need help with?")
        topic = st.text_area(
            label="Enter your topic, question, or problem statement:",
            placeholder="e.g., Explain the concept of Quantum Entanglement in simple terms...",
            height=120,
            label_visibility="collapsed"
        )
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            process_button = st.button("🚀 Research & Explain", use_container_width=True)

        # Core Logic
        def clean_output(text):
            # Remove phrases like "Thought: I now can give a great answer."
            # and variations at the beginning of the text.
            patterns = [
                r"^Thought:\s*I now can give a great answer\.\s*",
                r"^Thought:\s*I've got the final answer\s*",
                r"^Final Answer:\s*"
            ]
            cleaned = text
            for pattern in patterns:
                cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
            return cleaned.strip()

        def run_crew_logic(topic_input, vstore=None):
            final_groq = os.getenv("GROQ_API_KEY")
            final_serper = os.getenv("SERPER_API_KEY")
            
            if not final_groq:
                st.error("⚠️ Groq API Key is missing in .env file!")
                return None
            
            os.environ["SERPER_API_KEY"] = final_serper if final_serper else ""
            
            try:
                search_tool = SerperDevTool()
                
                # Define RAG Tool if vectorstore exists
                study_tool = None
                if vstore:
                    @tool("Search Study Materials")
                    def study_tool(query: str):
                        """Search the uploaded study materials for specific facts, definitions, and explanations."""
                        results = vstore.similarity_search(query, k=2)
                        return "\n".join([r.page_content for r in results])

                llm_engine = LLM(model="gemini/gemini-flash-latest", api_key=os.getenv("GEMINI_API_KEY"))
                
                researcher = Agent(
                    role="Academic Researcher",
                    goal=f"Conduct deep research on {topic_input} and find accurate facts.",
                    backstory="You are a world-class academic researcher with a talent for finding high-quality sources.",
                    llm=llm_engine,
                    tools=[search_tool] if final_serper else [] + ([study_tool] if study_tool else []),
                    verbose=False
                )
                
                explainer = Agent(
                    role="Educational Specialist",
                    goal=f"Transform complex research about {topic_input} into a simple, engaging lesson.",
                    backstory="You are a beloved teacher known for making difficult subjects easy.",
                    llm=llm_engine,
                    tools=[study_tool] if study_tool else [],
                    verbose=False
                )
                
                task1_desc = f"Research: {topic_input}."
                if study_tool:
                    task1_desc += " Prioritize information from the uploaded study materials."
                
                task1 = Task(description=task1_desc, expected_output="Summary with 5 takeaways.", agent=researcher)
                task2 = Task(description=f"Explain: {topic_input}. Use the research findings and study materials to create a clear guide.", expected_output="Engaging 300-word explanation.", agent=explainer)
                
                academic_crew = Crew(agents=[researcher, explainer], tasks=[task1, task2], verbose=False)
                return run_crew_with_retry(academic_crew)
            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")
                return None

        def run_crew_with_retry(crew, inputs=None, max_retries=5):
            """Run crew with retry logic for handling rate limit and 503 errors"""
            for attempt in range(max_retries):
                try:
                    return crew.kickoff(inputs=inputs) if inputs else crew.kickoff()
                except Exception as e:
                    error_str = str(e)
                    # Handle 503 - Service Unavailable
                    if "503" in error_str or "UNAVAILABLE" in error_str:
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 2
                            st.warning(f"🤖 Model busy, retrying in {wait_time} seconds... (Attempt {attempt + 1}/{max_retries})")
                            time.sleep(wait_time)
                        else:
                            raise e
                    # Handle 429 - Rate Limit Exceeded
                    elif "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                        if attempt < max_retries - 1:
                            # Extract retry delay from error if available, otherwise use default
                            wait_time = 20  # Default 20 seconds for rate limits
                            if "retryDelay" in error_str:
                                try:
                                    # Try to parse the retry delay from error
                                    match = re.search(r'(\d+)s', error_str)
                                    if match:
                                        wait_time = int(match.group(1)) + 2  # Add buffer
                                except:
                                    pass
                            st.warning(f"⏱️ Rate limit hit! Waiting {wait_time} seconds... (Attempt {attempt + 1}/{max_retries})")
                            time.sleep(wait_time)
                        else:
                            raise e
                    else:
                        raise e

        if process_button:
            if not topic:
                st.warning("⚠️ Please enter a topic first!")
            else:
                with st.spinner("🧠 Connecting to AI Knowledge Graph..."):
                    raw_result = run_crew_logic(topic, vectorstore)
                    if raw_result:
                        result = clean_output(str(raw_result))
                        st.session_state.latest_result = result
                        words = topic.split()
                        title = " ".join(words[:5]) + ("..." if len(words) > 5 else "")
                        
                        if st.session_state.logged_in:
                            st.session_state.homework_history.append({"title": title, "result": result})
                            users_db = load_data(USER_DATA_FILE)
                            if st.session_state.user_name in users_db:
                                users_db[st.session_state.user_name]["history"] = st.session_state.homework_history
                                save_data(USER_DATA_FILE, users_db)
                            st.success("✨ Research Complete! Saved to your history.")
                        else:
                            st.success("✨ Research Complete!")
                            st.info("💡 **Tip**: Log in to save your research history permanently.")

        if st.session_state.latest_result:
            st.markdown("---")
            st.markdown("<div class='glass-card fade-in'>", unsafe_allow_html=True)
            st.markdown("<h2 style='color: #059669; font-family: Outfit;'>🎯 Your Explanation</h2>", unsafe_allow_html=True)
            st.markdown(st.session_state.latest_result)
            st.download_button(label="📥 Download Study Guide", data=st.session_state.latest_result, file_name="study_guide.md", mime="text/markdown", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown("""
<div class='footer-box'>
    <p class='footer-text'>✨ This website is made by Faizan Ali ✨</p>
    <p style='color: #94a3b8; font-size: 0.8rem; margin-top: 5px;'>Powered by CrewAI & Advanced Agentic AI Architecture 🚀</p>
</div>
""", unsafe_allow_html=True)