import os
# Disable CrewAI telemetry BEFORE any crewai imports to avoid signal handler errors
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"

import streamlit as st
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM
from crewai_tools import SerperDevTool

# Load environment variables
load_dotenv()

# Initialize tools
search = SerperDevTool()

# Initialize LLM
llm = LLM(
    model="groq/llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY")
)

# Page configuration
st.set_page_config(
    page_title="Homework Helper Pro",
    page_icon="📚",
    layout="centered"
)

# Custom CSS for styling
st.markdown("""
    <style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        padding: 20px 0;
    }
    .sub-header {
        text-align: center;
        color: #666;
        font-size: 1.1em;
        margin-bottom: 30px;
    }
    .stButton>button {
        background-color: #1f77b4;
        color: white;
        font-weight: bold;
        padding: 10px 30px;
        border-radius: 5px;
    }
    .stButton>button:hover {
        background-color: #145a8a;
    }
    .result-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin-top: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown("<h1 class='main-header'>📚 Homework Helper Pro</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Get help with any topic! Ask anything and our AI agents will research and explain it to you.</p>", unsafe_allow_html=True)

# Initialize session state
if 'result' not in st.session_state:
    st.session_state.result = None

# User input section
st.markdown("### 📝 Enter Your Topic or Question")
topic = st.text_area(
    "What do you need help with?",
    placeholder="e.g., Explain photosynthesis, Help me with algebra equations, What caused World War II?",
    height=100
)

# Process button
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    process_clicked = st.button("🔍 Get Help", use_container_width=True)

import time

def run_crew_with_retry(crew, inputs, max_retries=5):
    """Run crew with retry logic for handling rate limit and 503 errors"""
    for attempt in range(max_retries):
        try:
            return crew.kickoff(inputs=inputs)
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
                            import re
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

if process_clicked and topic:
    with st.spinner("🤖 Our AI agents are working on your request..."):
        # Define Agents
        Homework_Researcher = Agent(
            role="Homework Researcher",
            goal="Do accurate and efficient research about the given topic",
            backstory="A great researcher who has helped many students and learners with comprehensive research on various topics.",
            llm=llm,
            tools=[search],
            verbose=False
        )

        Explainer = Agent(
            role="Homework Explainer",
            goal="Explain the research topic to the user in an easy-to-understand manner",
            backstory="An expert explainer who breaks down complex topics into simple, digestible explanations that anyone can understand.",
            llm=llm,
            tools=[search],
            verbose=False
        )

        # Define Tasks
        Homework_Researcher_task = Task(
            description=f"Research the following topic thoroughly: {topic}. Find accurate information, key points, and reliable sources.",
            expected_output="A well-researched summary with key points and sources in 10-20 lines",
            agent=Homework_Researcher
        )

        Explainer_Task = Task(
            description=f"Explain the research about '{topic}' in simple, easy-to-understand words that a student can understand. Break down complex concepts.",
            expected_output="A clear, comprehensive explanation of the topic in simple terms",
            agent=Explainer
        )

        # Create and run crew
        crew = Crew(
            agents=[Homework_Researcher, Explainer],
            tasks=[Homework_Researcher_task, Explainer_Task],
            verbose=False
        )

        # Get result with retry logic
        try:
            result = run_crew_with_retry(crew, {"topic": topic})
            st.session_state.result = result
        except Exception as e:
            error_str = str(e)
            if "503" in error_str or "UNAVAILABLE" in error_str:
                st.error("""
                🤖 **Model Currently Busy**
                
                The Gemini API is experiencing high demand. Please try:
                1. Wait a few minutes and try again
                2. Try a simpler query
                3. Try again during off-peak hours
                
                Error: Service temporarily unavailable
                """)
            elif "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                st.error("""
                ⏱️ **Rate Limit Exceeded**
                
                You've reached the free tier limit (5 requests/minute). Options:
                
                1. **Wait 1 minute** and try again
                2. **Upgrade to paid plan** at https://ai.google.dev/pricing
                3. **Use a different API key** with higher limits
                
                For more info: https://ai.google.dev/gemini-api/docs/rate-limits
                """)
            else:
                st.error(f"An error occurred: {str(e)}")

# Display result
if st.session_state.result:
    st.markdown("---")
    st.markdown("### 🎯 Your Answer")
    st.markdown("<div class='result-box'>", unsafe_allow_html=True)
    st.markdown(st.session_state.result)
    st.markdown("</div>", unsafe_allow_html=True)

    # Download button
    result_text = str(st.session_state.result)
    st.download_button(
        label="📥 Download Result",
        data=result_text,
        file_name=f"homework_helper_result.txt",
        mime="text/plain"
    )

elif process_clicked and not topic:
    st.warning("⚠️ Please enter a topic or question first!")

# Footer
st.markdown("---")
st.markdown("<p style='text-align: center; color: #888;'>Powered by CrewAI & Groq (Llama 3.1 8B Instant) 🚀</p>", unsafe_allow_html=True)