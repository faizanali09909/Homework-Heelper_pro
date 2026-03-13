import os
# Disable CrewAI telemetry BEFORE any crewai imports to avoid signal handler errors
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"

import streamlit as st
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM
from crewai_tools import SerperDevTool
import time
import re
import json

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
load_dotenv()

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
        color: transparent;
        text-shadow: 0 0 0 #fbbf24; /* Primary trick for emoji coloring */
        filter: brightness(1.1) drop-shadow(0 0 2px rgba(251, 191, 36, 0.5));
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
        st.info("🔑 **Personalize your experience**. Enter your own API keys below.")
        user_groq_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...", help="Get your key at console.groq.com")
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
        st.markdown("<div style='height: 200px; background: #f8fafc; border: 2px dashed #e2e8f0; border-radius: 20px; display: flex; align-items: center; justify-content: center; color: #64748b; font-size: 1.5rem; font-family: Outfit; font-weight: 700;'>✨ Smart Learning Hub</div>", unsafe_allow_html=True)

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

        def run_crew_logic(topic_input, groq_key):
            final_groq = groq_key if groq_key else os.getenv("GROQ_API_KEY")
            final_serper = os.getenv("SERPER_API_KEY")
            
            if not final_groq:
                st.error("⚠️ Groq API Key is missing! Please provide it in the sidebar.")
                return None
            
            os.environ["SERPER_API_KEY"] = final_serper if final_serper else ""
            
            try:
                search_tool = SerperDevTool()
                llm_engine = LLM(model="groq/llama-3.1-8b-instant", api_key=final_groq)
                
                researcher = Agent(
                    role="Academic Researcher",
                    goal=f"Conduct deep research on {topic_input} and find accurate facts.",
                    backstory="You are a world-class academic researcher with a talent for finding high-quality sources.",
                    llm=llm_engine,
                    tools=[search_tool] if final_serper else [],
                    verbose=False
                )
                
                explainer = Agent(
                    role="Educational Specialist",
                    goal=f"Transform complex research about {topic_input} into a simple, engaging lesson.",
                    backstory="You are a beloved teacher known for making difficult subjects easy.",
                    llm=llm_engine,
                    verbose=False
                )
                
                task1 = Task(description=f"Research: {topic_input}", expected_output="Summary with 5 takeaways.", agent=researcher)
                task2 = Task(description=f"Explain: {topic_input}", expected_output="Engaging 300-word explanation.", agent=explainer)
                
                academic_crew = Crew(agents=[researcher, explainer], tasks=[task1, task2], verbose=False)
                return academic_crew.kickoff()
            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")
                return None

        if process_button:
            if not topic:
                st.warning("⚠️ Please enter a topic first!")
            else:
                with st.spinner("🧠 Connecting to AI Knowledge Graph..."):
                    raw_result = run_crew_logic(topic, user_groq_key)
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
st.markdown("<br><br><hr><p style='text-align: center; color: #94a3b8; font-size: 0.9rem;'>Powered by CrewAI & Advanced Agentic AI Architecture 🚀</p>", unsafe_allow_html=True)