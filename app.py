import streamlit as st
from streamlit_chat import message
import ollama
import time
import PyPDF2
import docx

# ----------------------------
# Page Config and Styling
# ----------------------------
st.set_page_config(page_title="TalentScout AI - Hiring Assistant", page_icon="🧠", layout="centered")

st.markdown("""
    <style>
    body { background-color: #f5f7fa; }
    .stChatInputContainer { background: #fff; border-top: 2px solid #ccc; }
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
if "tech_questions" not in st.session_state:
    st.session_state.tech_questions = []
if "end_chat" not in st.session_state:
    st.session_state.end_chat = False

# ----------------------------
# LLM Wrapper
# ----------------------------
def generate_llm_response(prompt):
    with st.spinner("Thinking..."):
        response = ollama.chat(model="mistral", messages=[{"role": "user", "content": prompt}])
        return response["message"]["content"]

# ----------------------------
# Resume Extraction
# ----------------------------
def extract_text_from_resume(file):
    if file.type == "application/pdf":
        reader = PyPDF2.PdfReader(file)
        return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    elif file.type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
        doc = docx.Document(file)
        return "\n".join([para.text for para in doc.paragraphs])
    else:
        return "❌ Unsupported file format. Please upload a PDF or DOCX."

# ----------------------------
# Technical Question Generator
# ----------------------------
def get_technical_questions(tech_stack):
    prompt = f"You are an AI recruiter. Generate 3 concise technical questions EACH for the following technologies:\n{tech_stack}."
    return generate_llm_response(prompt)

def generate_questions_from_resume(text):
    prompt = f"Based on the following resume text, generate 5 concise technical interview questions:\n\n{text}\n\nQuestions:"
    return generate_llm_response(prompt)

# ----------------------------
# Chatbot Logic
# ----------------------------
def chat_logic(user_input):
    info = st.session_state.candidate_info
    stage = st.session_state.stage

    if user_input.lower() in ["exit", "quit", "bye", "end"]:
        st.session_state.end_chat = True
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
# Resume Upload UI
# ----------------------------
with st.expander("📄 Upload Resume for Smart Questions"):
    uploaded_file = st.file_uploader("Upload your resume (PDF or DOCX)", type=["pdf", "docx"])
    if uploaded_file:
        resume_text = extract_text_from_resume(uploaded_file)
        st.success("✅ Resume uploaded successfully.")
        if st.button("Generate Questions from Resume"):
            questions = generate_questions_from_resume(resume_text)
            st.session_state.messages.append({"role": "assistant", "content": f"📄 Based on your resume, here are some tailored questions:\n\n{questions}"})
            st.rerun()

# ----------------------------
# Chat Interface
# ----------------------------
with st.container():
    for i, msg in enumerate(st.session_state.messages):
        message(msg["content"], is_user=msg["role"] == "user", key=str(i))

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
