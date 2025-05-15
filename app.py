import streamlit as st
from streamlit_chat import message
from dotenv import load_dotenv
import os
import time
import fitz  # PyMuPDF
import requests
import pandas as pd
from datetime import datetime

# ----------------------------
# Load Environment Variables
# ----------------------------
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# ----------------------------
# Page Config & Styles
# ----------------------------
st.set_page_config(page_title="TalentScout AI", page_icon="🧠", layout="centered")

st.markdown("""
    <style>
    .stButton button { background-color: #003366; color: white; font-weight: bold; border-radius: 8px; }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #003366; }
    </style>
""", unsafe_allow_html=True)

st.markdown("## 🧠 TalentScout AI Assistant")
st.caption("Your intelligent virtual recruiter for smarter hiring decisions.")

# ----------------------------
# State Initialization
# ----------------------------
if "messages" not in st.session_state: st.session_state.messages = []
if "stage" not in st.session_state: st.session_state.stage = "greeting"
if "candidate_info" not in st.session_state: st.session_state.candidate_info = {}
if "tech_questions" not in st.session_state: st.session_state.tech_questions = []
if "end_chat" not in st.session_state: st.session_state.end_chat = False
if "resume_questions" not in st.session_state: st.session_state.resume_questions = ""

# ----------------------------
# LLM Response via Groq API
# ----------------------------
def generate_llm_response(prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5
    }
    response = requests.post(GROQ_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# ----------------------------
# Question Generators
# ----------------------------
def get_technical_questions(tech_stack):
    prompt = f"You are an AI recruiter. Generate 3 short technical interview questions for each of the following technologies:\n{tech_stack}."
    return generate_llm_response(prompt)

def get_questions_from_resume(resume_text):
    prompt = f"You are an AI interviewer. Read the resume below and generate 5 job-relevant technical interview questions based on the content:\n\n{resume_text}"
    return generate_llm_response(prompt)

# ----------------------------
# Resume Parsing
# ----------------------------
def extract_text_from_resume(uploaded_file):
    if uploaded_file is not None:
        with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
            text = ""
            for page in doc:
                text += page.get_text()
            return text.strip()
    return ""

# ----------------------------
# Save Candidate Data
# ----------------------------
def save_candidate_data():
    info = st.session_state.candidate_info
    if not info: return

    df = pd.DataFrame([info])
    df["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df["Resume Questions"] = st.session_state.resume_questions
    if os.path.exists("candidate_data.csv"):
        df.to_csv("candidate_data.csv", mode="a", index=False, header=False)
    else:
        df.to_csv("candidate_data.csv", index=False)

# ----------------------------
# Chat Logic
# ----------------------------
def chat_logic(user_input):
    info = st.session_state.candidate_info
    stage = st.session_state.stage

    if user_input.lower() in ["exit", "quit", "bye", "end"]:
        st.session_state.end_chat = True
        save_candidate_data()
        return "✅ Thank you for chatting with TalentScout! We’ll be in touch shortly. Goodbye! 👋"

    if stage == "greeting":
        st.session_state.stage = "full_name"
        return "👋 Welcome! I’m your virtual assistant from TalentScout.\n\nCan I know your full name?"

    elif stage == "full_name":
        info["Full Name"] = user_input
        st.session_state.stage = "email"
        return "📧 What’s your email address?"

    elif stage == "email":
        info["Email"] = user_input
        st.session_state.stage = "phone"
        return "📞 Could you share your phone number?"

    elif stage == "phone":
        info["Phone"] = user_input
        st.session_state.stage = "experience"
        return "🧑‍💻 How many years of experience do you have?"

    elif stage == "experience":
        info["Experience"] = user_input
        st.session_state.stage = "position"
        return "🎯 What position(s) are you applying for?"

    elif stage == "position":
        info["Position"] = user_input
        st.session_state.stage = "location"
        return "📍 Where are you currently located?"

    elif stage == "location":
        info["Location"] = user_input
        st.session_state.stage = "tech_stack"
        return "💻 Please list your tech stack (e.g., Python, React, MongoDB)..."

    elif stage == "tech_stack":
        info["Tech Stack"] = user_input
        st.session_state.stage = "questioning"
        tech_q = get_technical_questions(user_input)
        st.session_state.tech_questions = tech_q.split("\n")
        return f"🧪 Here are some questions based on your tech stack:\n\n{tech_q}"

    elif stage == "questioning":
        st.session_state.stage = "done"
        return "✅ That’s all I need for now. Thank you for your time! You’ll hear from us soon. 🙏"

    else:
        return "❓ Hmm, I didn’t quite get that. Could you please rephrase?"

# ----------------------------
# Resume Upload Section
# ----------------------------
with st.expander("📄 Upload Resume (PDF) for Question Generation"):
    uploaded_file = st.file_uploader("Upload your resume", type=["pdf"])
    if uploaded_file:
        resume_text = extract_text_from_resume(uploaded_file)
        if resume_text:
            st.success("✅ Resume processed!")
            with st.spinner("Generating interview questions..."):
                questions = get_questions_from_resume(resume_text)
                st.session_state.resume_questions = questions
            st.markdown("### 🧠 AI-Generated Interview Questions from Resume:")
            st.markdown(questions)

# ----------------------------
# Chat Interface
# ----------------------------
for i, msg in enumerate(st.session_state.messages):
    message(msg["content"], is_user=msg["role"] == "user", key=str(i))

if not st.session_state.end_chat:
    user_prompt = st.chat_input("Talk to TalentScout...")

    if user_prompt:
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        bot_response = chat_logic(user_prompt)
        time.sleep(0.3)
        st.session_state.messages.append({"role": "assistant", "content": bot_response})
        st.rerun()
else:
    st.success("✅ Conversation ended. Refresh the page to start again.")
    with st.expander("📋 Candidate Summary"):
        for k, v in st.session_state.candidate_info.items():
            st.markdown(f"**{k}:** {v}")
    if os.path.exists("candidate_data.csv"):
        st.download_button("📅 Download Chat & Info (CSV)", data=open("candidate_data.csv", "rb"), file_name="candidate_data.csv", mime="text/csv")
