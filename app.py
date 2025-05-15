import streamlit as st
from streamlit_chat import message
import os
import time
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import requests

# ----------------------------
# Load Environment Variables
# ----------------------------
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# ----------------------------
# Set Custom Page Config
# ----------------------------
st.set_page_config(page_title="TalentScout AI - Hiring Assistant", page_icon="🧠", layout="centered")

# ----------------------------
# Custom CSS Styling
# ----------------------------
st.markdown("""
    <style>
    body {
        background-color: #f5f7fa;
    }
    .st-emotion-cache-1avcm0n {
        padding-top: 1rem;
    }
    .stChatInputContainer {
        background: #fff;
        border-top: 2px solid #ccc;
    }
    .stButton button {
        background-color: #003366;
        color: white;
        font-weight: bold;
        border-radius: 8px;
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #003366;
    }
    .chat-container {
        background-color: #ffffff;
        padding: 1.2rem;
        border-radius: 12px;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.08);
        margin-top: 1rem;
    }
    .info-box {
        background-color: #eaf3ff;
        padding: 0.8rem;
        border-radius: 10px;
        margin-bottom: 10px;
        font-size: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------
# App Header
# ----------------------------
st.markdown("## 🧠 TalentScout AI Assistant")
st.caption("Your intelligent virtual recruiter for smarter hiring decisions.")

# ----------------------------
# State Initialization
# ----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "stage" not in st.session_state:
    st.session_state.stage = "greeting"
if "candidate_info" not in st.session_state:
    st.session_state.candidate_info = {}
if "topic_questions" not in st.session_state:
    st.session_state.topic_questions = []
if "end_chat" not in st.session_state:
    st.session_state.end_chat = False
if "all_responses" not in st.session_state:
    st.session_state.all_responses = []

# ----------------------------
# LLM API Wrapper
# ----------------------------
def generate_llm_response(prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data)
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"❌ Error: {e}"

# ----------------------------
# Resume Upload & Processing
# ----------------------------
def extract_text_from_resume(uploaded_file):
    if uploaded_file.type == "application/pdf":
        import fitz  # PyMuPDF
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text = " ".join([page.get_text() for page in doc])
        return text
    elif uploaded_file.type == "text/plain":
        return uploaded_file.read().decode("utf-8")
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        import docx
        doc = docx.Document(uploaded_file)
        return " ".join([para.text for para in doc.paragraphs])
    else:
        return "Unsupported file type."

# ----------------------------
# Tech Question Generator
# ----------------------------
def get_technical_questions(tech_stack):
    prompt = f"""
You are an AI interviewer. Generate 3 beginner, 3 intermediate, and 3 advanced technical interview questions based on the following technologies or topics:
{tech_stack}
"""
    return generate_llm_response(prompt)

# ----------------------------
# Conversation Flow Logic
# ----------------------------
def chat_logic(user_input):
    info = st.session_state.candidate_info
    stage = st.session_state.stage

    if user_input.lower() in ["exit", "quit", "bye", "end"]:
        st.session_state.end_chat = True
        save_data_to_csv()
        return "✅ Thank you for chatting with TalentScout! We’ll be in touch shortly. Goodbye! 👋"

    if "generate questions on" in user_input.lower():
        topic = user_input.lower().split("generate questions on")[-1].strip()
        qns = get_technical_questions(topic)
        st.session_state.topic_questions.append((topic, qns))
        st.session_state.all_responses.append({"User Input": user_input, "AI Response": qns})
        return f"Here are your questions on **{topic}**:\n\n{qns}"

    if stage == "greeting":
        st.session_state.stage = "full_name"
        return "👋 Welcome! I’m your virtual assistant from TalentScout.\n\nCan I know your **full name**?"

    elif stage == "full_name":
        info["Full Name"] = user_input
        st.session_state.stage = "email"
        return "📧 What’s your **email address**?"

    elif stage == "email":
        info["Email"] = user_input
        st.session_state.stage = "phone"
        return "📞 Could you share your **phone number**?"

    elif stage == "phone":
        info["Phone"] = user_input
        st.session_state.stage = "experience"
        return "🧑‍💻 How many **years of experience** do you have?"

    elif stage == "experience":
        info["Experience"] = user_input
        st.session_state.stage = "position"
        return "🎯 What **position(s)** are you applying for?"

    elif stage == "position":
        info["Position"] = user_input
        st.session_state.stage = "location"
        return "📍 Where are you **currently located**?"

    elif stage == "location":
        info["Location"] = user_input
        st.session_state.stage = "tech_stack"
        return "💻 Please list your **tech stack** (e.g., Python, React, MongoDB)..."

    elif stage == "tech_stack":
        info["Tech Stack"] = user_input
        tech_q = get_technical_questions(user_input)
        st.session_state.topic_questions.append((user_input, tech_q))
        st.session_state.all_responses.append({"Tech Stack": user_input, "Questions": tech_q})
        st.session_state.stage = "done"
        return f"🧪 Here are some questions based on your tech stack:\n\n{tech_q}\n\n✅ That’s all I need for now. You can ask me to generate questions on any topic by typing: 'Generate questions on ...'"

    else:
        return "❓ I didn’t quite get that. You can continue our chat or type 'end' to finish."

# ----------------------------
# Save to CSV
# ----------------------------
def save_data_to_csv():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    info = st.session_state.candidate_info
    all_qas = st.session_state.all_responses

    # Save candidate info
    df_info = pd.DataFrame([info])
    df_info.to_csv(f"candidate_info_{timestamp}.csv", index=False)

    # Save Q&A log
    df_qas = pd.DataFrame(all_qas)
    df_qas.to_csv(f"candidate_qna_{timestamp}.csv", index=False)

# ----------------------------
# Chat Interface
# ----------------------------
with st.container():
    for i, msg in enumerate(st.session_state.messages):
        message(msg["content"], is_user=msg["role"] == "user", key=str(i))

# ----------------------------
# File Upload Section
# ----------------------------
with st.sidebar:
    uploaded_file = st.file_uploader("📄 Upload Resume (PDF, DOCX, TXT)", type=["pdf", "txt", "docx"])
    if uploaded_file:
        resume_text = extract_text_from_resume(uploaded_file)
        st.session_state.candidate_info["Resume"] = resume_text[:300] + "..."
        topic_q = get_technical_questions(resume_text[:600])
        st.session_state.topic_questions.append(("Resume Content", topic_q))
        st.session_state.all_responses.append({"Resume Extract": resume_text[:300], "Questions": topic_q})
        st.success("Resume processed. Questions based on resume will appear in chat.")

# ----------------------------
# Chat Input
# ----------------------------
if not st.session_state.end_chat:
    user_prompt = st.chat_input("Type here to talk to TalentScout...")

    if user_prompt:
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        bot_response = chat_logic(user_prompt)
        time.sleep(0.2)
        st.session_state.messages.append({"role": "assistant", "content": bot_response})
        st.rerun()
else:
    st.success("Conversation has ended. Refresh the page to restart.")
    with st.expander("📄 Candidate Summary"):
        for k, v in st.session_state.candidate_info.items():
            st.markdown(f"**{k}:** {v}")

    with st.expander("🧾 All Questions Asked"):
        for topic, qns in st.session_state.topic_questions:
            st.markdown(f"### 🔹 {topic}\n{qns}")
