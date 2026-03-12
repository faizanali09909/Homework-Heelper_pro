import os
# Disable CrewAI telemetry BEFORE any crewai imports to avoid signal handler errors
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"

import streamlit as st
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM
from crewai_tools import SerperDevTool
import time
import re

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
        --primary: #2563eb;
        --secondary: #7c3aed;
        --accent: #f59e0b;
        --glass: rgba(255, 255, 255, 0.7);
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main-header {
        font-family: 'Outfit', sans-serif;
        text-align: center;
        background: linear-gradient(135deg, #059669 0%, #0d9488 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3.8rem;
        padding: 1rem 0;
        margin-bottom: 0;
    }

    .sub-header {
        text-align: center;
        color: #64748b;
        font-size: 1.25rem;
        margin-bottom: 2rem;
        font-weight: 400;
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

    /* Premium Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white;
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        font-size: 1.1rem;
        padding: 0.8rem 2.5rem;
        border: none;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3);
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }

    .stButton>button:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 25px rgba(37, 99, 235, 0.4);
        background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
    }

    /* Input Fields */
    .stTextArea textarea {
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        font-size: 1.1rem;
        transition: all 0.3s ease;
    }

    /* Remove irritating red/orange focus outline COMPLETELY */
    .stTextArea textarea:focus {
        border-color: transparent !important;
        box-shadow: none !important;
        outline: none !important;
    }

    .stTextArea textarea:hover {
        border-color: #e2e8f0 !important;
    }

    /* Sidebar Styling */
    .css-1d391kg {
        background-color: #f8fafc;
    }

    /* Results */
    .result-content {
        color: #1e293b;
        line-height: 1.8;
        font-size: 1.1rem;
    }

    /* Animation */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .fade-in {
        animation: fadeIn 0.8s ease-out forwards;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""
if 'homework_history' not in st.session_state:
    st.session_state.homework_history = []
if 'latest_result' not in st.session_state:
    st.session_state.latest_result = None

# Sidebar Content
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #059669; font-family: Outfit;'>👤 Account</h2>", unsafe_allow_html=True)
    
    if not st.session_state.logged_in:
        auth_mode = st.tabs(["Login", "Sign Up"])
        
        with auth_mode[0]:
            user = st.text_input("Username", key="login_user")
            pwd = st.text_input("Password", type="password", key="login_pwd")
            if st.button("Login", use_container_width=True):
                if user and pwd:
                    st.session_state.logged_in = True
                    st.session_state.user_name = user
                    st.success(f"Welcome back, {user}!")
                    st.rerun()
                else:
                    st.error("Please enter credentials")
        
        with auth_mode[1]:
            new_user = st.text_input("Username", key="signup_user")
            new_pwd = st.text_input("Password", type="password", key="signup_pwd")
            confirm_pwd = st.text_input("Confirm Password", type="password", key="signup_confirm")
            if st.button("Create Account", use_container_width=True):
                if new_user and new_pwd == confirm_pwd:
                    st.session_state.logged_in = True
                    st.session_state.user_name = new_user
                    st.success("Account created!")
                    st.rerun()
                else:
                    st.error("Passwords don't match or fields empty")
    else:
        st.write(f"Logged in as: **{st.session_state.user_name}**")
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_name = ""
            st.rerun()

    st.markdown("---")
    st.markdown("<h2 style='text-align: center; color: #059669; font-family: Outfit;'>⚙️ Configuration</h2>", unsafe_allow_html=True)
    st.info("🔑 **Personalize your experience**. Enter your own API keys below.")
    
    user_groq_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...", help="Get your key at console.groq.com")
    
    st.markdown("---")
    
    if st.session_state.homework_history:
        st.markdown("### 🕰️ History")
        if st.button("🗑️ Clear My History", use_container_width=True):
            st.session_state.homework_history = []
            st.session_state.latest_result = None
            st.rerun()
            
        for i, item in enumerate(reversed(st.session_state.homework_history)):
            with st.expander(f"📌 {item['title']}"):
                st.markdown(item["result"])
    else:
        st.caption("No history yet. Start asking!")

# Main Layout
col_left, col_mid, col_right = st.columns([1, 4, 1])

with col_mid:
    # Header Section
    st.markdown("<h1 class='main-header'>📚 Homework Helper Pro</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>Experience the future of learning with autonomous AI research agents</p>", unsafe_allow_html=True)
    
    # Hero Image (Using the absolute path of the generated image)
    # Note: Using the actual filename generated in the previous step
    hero_image_path = os.path.join(os.getcwd(), "brain", "231a4480-ff66-4f78-a88c-f94d7056b334", "homework_ai_hero_1773332946142.png")
    # In a real scenario, we might need a relative or public URL, but for local streamlit run, local paths work.
    # However, to be safe with streamlit, it's often better to use PIL or just the path if served.
    if os.path.exists(hero_image_path):
        st.image(hero_image_path, use_container_width=True)
    else:
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
    def run_crew_logic(topic_input, groq_key):
        # Use provided keys or fall back to env
        final_groq = groq_key if groq_key else os.getenv("GROQ_API_KEY")
        final_serper = os.getenv("SERPER_API_KEY")
        
        if not final_groq:
            st.error("⚠️ Groq API Key is missing! Please provide it in the sidebar.")
            return None
        
        os.environ["SERPER_API_KEY"] = final_serper if final_serper else ""
        
        try:
            # Initialize tools & LLM
            search_tool = SerperDevTool()
            llm_engine = LLM(
                model="groq/llama-3.1-8b-instant",
                api_key=final_groq
            )
            
            # Agents
            researcher = Agent(
                role="Academic Researcher",
                goal=f"Conduct deep research on {topic_input} and find accurate facts.",
                backstory="You are a world-class academic researcher with a talent for finding high-quality sources and hidden insights.",
                llm=llm_engine,
                tools=[search_tool] if final_serper else [],
                verbose=False
            )
            
            explainer = Agent(
                role="Educational Specialist",
                goal=f"Transform complex research about {topic_input} into a simple, engaging lesson.",
                backstory="You are a beloved teacher known for making the most difficult subjects easy for anyone to understand.",
                llm=llm_engine,
                verbose=False
            )
            
            # Tasks
            task1 = Task(
                description=f"Thoroughly research the topic: {topic_input}. Focus on key concepts, historical context, and current developments.",
                expected_output="A structured summary with at least 5 key takeaways and a list of reliable reference points.",
                agent=researcher
            )
            
            task2 = Task(
                description=f"Based on the research, write a 300-word explanation of {topic_input}. Use analogies and simple language. Structure it with clear headings.",
                expected_output="An engaging educational explanation designed for a student.",
                agent=explainer
            )
            
            # Crew
            academic_crew = Crew(
                agents=[researcher, explainer],
                tasks=[task1, task2],
                verbose=False
            )
            
            return academic_crew.kickoff()
        except Exception as e:
            st.error(f"❌ An error occurred: {str(e)}")
            return None

    if process_button:
        if not topic:
            st.warning("⚠️ Please enter a topic first!")
        else:
            with st.spinner("🧠 Connecting to AI Knowledge Graph... Our researchers are on it!"):
                result = run_crew_logic(topic, user_groq_key)
                
                if result:
                    st.session_state.latest_result = str(result)
                    
                    # Create a title for history
                    words = topic.split()
                    title = " ".join(words[:5]) + ("..." if len(words) > 5 else "")
                    
                    st.session_state.homework_history.append({
                        "title": title,
                        "result": str(result)
                    })
                    st.success("✨ Research Complete!")

    # Display Latest Result
    if st.session_state.latest_result:
        st.markdown("---")
        st.markdown("<div class='glass-card fade-in'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color: #2563eb; font-family: Outfit;'>🎯 Your Explanation</h2>", unsafe_allow_html=True)
        st.markdown("<div class='result-content'>", unsafe_allow_html=True)
        st.markdown(st.session_state.latest_result)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Download
        st.download_button(
            label="📥 Download Study Guide",
            data=st.session_state.latest_result,
            file_name="study_guide.md",
            mime="text/markdown",
            use_container_width=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 0.9rem;'>Powered by CrewAI, Groq & Advanced Agentic AI Architecture 🚀</p>", unsafe_allow_html=True)