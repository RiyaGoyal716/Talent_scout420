# app.py
import streamlit as st
from streamlit_chat import message
import os
import requests
import time
import fitz  # for PDF parsing
import docx
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

st.set_page_config(page_title="TalentScout AI - Resume First Chatbot", page_icon="🧠", layout="centered")

st.markdown("## 🧠 TalentScout AI - Resume Interview Assistant")
st.caption("Upload your resume and get personalized interview experience.")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "resume_uploaded" not in st.session_state:
    st.session_state.resume_uploaded = False
if "skills_confirmed" not in st.session_state:
    st.session_state.skills_confirmed = None
if "extracted_skills" not in st.session_state:
    st.session_state.extracted_skills = ""
if "custom_skills" not in st.session_state:
    st.session_state.custom_skills = ""
if "questions" not in st.session_state:
    st.session_state.questions = []
if "answers" not in st.session_state:
    st.session_state.answers = []
if "question_index" not in st.session_state:
    st.session_state.question_index = 0
if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = False

# ----------------------------
# Resume Text Extractor
# ----------------------------
def extract_text_from_resume(uploaded_file):
    if uploaded_file.type == "application/pdf":
        with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
            return "\n".join(page.get_text() for page in doc)
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = docx.Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs])
    else:
        return ""

# ----------------------------
# Groq Completion Function
# ----------------------------
def call_groq(prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ Groq API error: {str(e)}"

# ----------------------------
# Question Generator
# ----------------------------
def generate_questions(skills):
    prompt = f"""
You are an AI interviewer. Generate 5 mixed-format (MCQ, MSQ, and descriptive) coding questions covering the following skills:
{skills}
Number each question. Indicate type as [MCQ], [MSQ], or [Descriptive].
"""
    return call_groq(prompt).split("\n")

# ----------------------------
# Feedback Generator
# ----------------------------
def generate_feedback(answers, skills):
    combined = "\n".join(f"Q{i+1}: {q}\nA{i+1}: {a}" for i, (q, a) in enumerate(zip(st.session_state.questions, answers)))
    prompt = f"""
You are a senior interviewer. Analyze the candidate's answers below and give:
1. Constructive feedback
2. 15 topics or questions to prepare next, based on skills: {skills}

Conversation:
{combined}
"""
    return call_groq(prompt)

# ----------------------------
# Step 1: Upload Resume
# ----------------------------
if not st.session_state.resume_uploaded:
    uploaded = st.file_uploader("📄 Upload your resume (PDF or DOCX)", type=["pdf", "docx"])
    if uploaded:
        resume_text = extract_text_from_resume(uploaded)
        st.session_state.resume_uploaded = True
        skill_prompt = f"Extract the key technical skills from this resume:\n\n{resume_text}\n\nReturn them as a comma-separated list."
        st.session_state.extracted_skills = call_groq(skill_prompt)

# ----------------------------
# Step 2: Confirm Skills
# ----------------------------
if st.session_state.resume_uploaded and st.session_state.skills_confirmed is None:
    st.markdown(f"🧠 We extracted these skills from your resume:\n\n`{st.session_state.extracted_skills}`")
    response = st.radio("Are these skills correct?", ["Yes", "No"])
    if response == "Yes":
        st.session_state.skills_confirmed = True
        st.session_state.questions = generate_questions(st.session_state.extracted_skills)
    elif response == "No":
        st.session_state.skills_confirmed = False

# ----------------------------
# Step 3: Manual Skills Entry
# ----------------------------
if st.session_state.skills_confirmed is False and not st.session_state.custom_skills:
    custom = st.text_input("Please enter your correct skills (comma-separated):")
    if custom:
        st.session_state.custom_skills = custom
        st.session_state.questions = generate_questions(custom)

# ----------------------------
# Step 4: Ask Questions
# ----------------------------
if st.session_state.questions and st.session_state.question_index < len(st.session_state.questions):
    q = st.session_state.questions[st.session_state.question_index]
    st.markdown(f"**Question {st.session_state.question_index + 1}:** {q}")
    user_answer = st.text_area("Your Answer:", key=f"ans_{st.session_state.question_index}")
    if st.button("Submit Answer"):
        st.session_state.answers.append(user_answer)
        st.session_state.question_index += 1
        st.rerun()

# ----------------------------
# Step 5: Show Feedback
# ----------------------------
if st.session_state.question_index == 5 and not st.session_state.feedback_given:
    st.markdown("✅ You've completed the mini-interview! Generating feedback...")
    skills_used = st.session_state.extracted_skills if st.session_state.skills_confirmed else st.session_state.custom_skills
    feedback = generate_feedback(st.session_state.answers, skills_used)
    st.markdown("### 📝 Feedback & Preparation Tips")
    st.markdown(feedback)
    st.session_state.feedback_given = True

# ----------------------------
# Chat Log Display (Optional)
# ----------------------------
st.divider()
st.markdown("### 💬 Chat History")
for i, msg in enumerate(st.session_state.messages):
    message(msg["content"], is_user=msg["role"] == "user", key=str(i))
