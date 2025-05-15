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
# Page Config & Styling
# ----------------------------
st.set_page_config(page_title="TalentScout AI - Hiring Assistant", page_icon="🧠", layout="centered")
st.markdown("""
    <style>
    body {
        background-color: #f5f7fa;
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
# Initialize session state
# ----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "candidate_info" not in st.session_state:
    st.session_state.candidate_info = {}
if "topic_questions" not in st.session_state:
    st.session_state.topic_questions = []
if "all_responses" not in st.session_state:
    st.session_state.all_responses = []
if "question_page" not in st.session_state:
    st.session_state.question_page = 0
if "current_topic" not in st.session_state:
    st.session_state.current_topic = ""
if "end_chat" not in st.session_state:
    st.session_state.end_chat = False

# ----------------------------
# LLM API call wrapper
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
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
        if response.status_code == 401:
            return "❌ Error: Invalid API key. Please check your GROQ_API_KEY."
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"❌ Error calling Groq API: {e}"

# ----------------------------
# Resume Text Extraction
# ----------------------------
def extract_text_from_resume(uploaded_file):
    if uploaded_file.type == "application/pdf":
        import fitz
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        return " ".join([page.get_text() for page in doc])
    elif uploaded_file.type == "text/plain":
        return uploaded_file.read().decode("utf-8")
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        import docx
        doc = docx.Document(uploaded_file)
        return " ".join([para.text for para in doc.paragraphs])
    else:
        return ""

# ----------------------------
# Generate 10-15 questions with answers with paging
# ----------------------------
def generate_questions_with_answers(topic, page=0, batch_size=5):
    # Prompt requests 5 Q&A at a time (easy to advanced + situational + code snippet + MNC style)
    prompt = f"""
You are an expert AI interviewer. Generate {batch_size} technical interview questions and detailed answers on the topic: "{topic}".
Include a mix of:
- easy, intermediate, and advanced questions,
- situational and scenario-based coding problems,
- code snippets to analyze or complete,
- questions typical of top MNC interviews.
Format your response as a numbered list with each question followed by its answer.  
Return only {batch_size} questions per response.
"""
    response = generate_llm_response(prompt)
    return response

# ----------------------------
# Chat logic handling
# ----------------------------
def chat_logic(user_input):
    if user_input.lower() in ["exit", "quit", "bye", "end"]:
        st.session_state.end_chat = True
        save_data_to_csv()
        return "✅ Thank you for chatting with TalentScout! We’ll be in touch shortly. Goodbye! 👋"

    if user_input.lower().startswith("generate questions on "):
        topic = user_input[19:].strip()
        st.session_state.current_topic = topic
        st.session_state.question_page = 0
        qna = generate_questions_with_answers(topic, page=0)
        st.session_state.topic_questions.append((topic, qna))
        st.session_state.all_responses.append({"User Input": user_input, "AI Response": qna})
        return f"Here are some questions and answers on **{topic}**:\n\n{qna}\n\nType 'continue' to get more questions."

    if user_input.lower() == "continue":
        if not st.session_state.current_topic:
            return "❌ Please first generate questions by typing: Generate questions on <topic>"
        st.session_state.question_page += 1
        qna = generate_questions_with_answers(st.session_state.current_topic, page=st.session_state.question_page)
        if "error" in qna.lower() or not qna.strip():
            return "❌ Sorry, no more questions available or API error."
        st.session_state.topic_questions.append((st.session_state.current_topic, qna))
        st.session_state.all_responses.append({"User Input": user_input, "AI Response": qna})
        return f"More questions on **{st.session_state.current_topic}**:\n\n{qna}\n\nType 'continue' to get even more questions."

    return "❓ I didn’t quite get that. You can type 'Generate questions on <topic>' to start or 'end' to finish."

# ----------------------------
# Save candidate info & Q&A
# ----------------------------
def save_data_to_csv():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    info = st.session_state.candidate_info
    all_qas = st.session_state.all_responses

    df_info = pd.DataFrame([info])
    df_info.to_csv(f"candidate_info_{timestamp}.csv", index=False)

    df_qas = pd.DataFrame(all_qas)
    df_qas.to_csv(f"candidate_qna_{timestamp}.csv", index=False)

# ----------------------------
# Main App UI
# ----------------------------
st.markdown("## 🧠 TalentScout AI Assistant")
st.caption("Your intelligent virtual recruiter for smarter hiring decisions.")

# Sidebar Resume Upload
with st.sidebar:
    st.markdown("### 📄 Upload Resume (PDF, DOCX, TXT)")
    uploaded_file = st.file_uploader("", type=["pdf", "txt", "docx"])
    if uploaded_file:
        resume_text = extract_text_from_resume(uploaded_file)
        if resume_text:
            st.success("Resume processed successfully!")
            st.session_state.candidate_info["Resume"] = resume_text[:500] + "..."
            # Optionally generate questions on resume content summary
            prompt_for_resume = resume_text[:600].replace("\n", " ")
            resume_qna = generate_questions_with_answers(prompt_for_resume, page=0)
            st.session_state.topic_questions.append(("Resume Content", resume_qna))
            st.session_state.all_responses.append({"Resume Extract": resume_text[:300], "Questions": resume_qna})
            # Add message for user to see in chat
            st.session_state.messages.append({"role": "assistant", "content": "I processed your resume and generated some questions based on it. You can ask me for more by typing 'continue' or 'Generate questions on <topic>'."})
        else:
            st.error("Failed to extract text from resume. Please try another file.")

# Show chat messages
with st.container():
    for i, chat in enumerate(st.session_state.messages):
        is_user = chat["role"] == "user"
        message(chat["content"], is_user=is_user, key=f"msg_{i}")

if not st.session_state.end_chat:
    user_prompt = st.chat_input("Type here to talk to TalentScout...")
    if user_prompt:
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        bot_response = chat_logic(user_prompt)
        time.sleep(0.3)
        st.session_state.messages.append({"role": "assistant", "content": bot_response})

else:
    st.success("Conversation ended. Refresh to start again.")
    with st.expander("📄 Candidate Summary"):
        for k, v in st.session_state.candidate_info.items():
            st.markdown(f"**{k}:** {v}")
    with st.expander("🧾 All Questions Asked"):
        for topic, qns in st.session_state.topic_questions:
            st.markdown(f"### 🔹 {topic}\n{qns}")

# Initial greeting on first load if no messages
if len(st.session_state.messages) == 0:
    greeting = ("Hello! 👋 To get started, please type:\n\n"
                "**Generate questions on <topic>**\n\n"
"Example: Generate questions on Python programming\n\n"
"Or upload your resume from the sidebar for custom questions.")
st.session_state.messages.append({"role": "assistant", "content": greeting})
# Render greeting message immediately
message(greeting, key="greeting")
