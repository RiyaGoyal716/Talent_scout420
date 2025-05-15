import streamlit as st
from dotenv import load_dotenv
import os
import fitz  # PyMuPDF
import requests
import time

# Load environment variable
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Streamlit config
st.set_page_config(page_title="TalentScout AI", page_icon="🧠", layout="centered")
st.title("🧠 TalentScout AI - Resume Interview Assistant")

# State
if "stage" not in st.session_state:
    st.session_state.stage = "upload"
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "skills" not in st.session_state:
    st.session_state.skills = ""
if "question_index" not in st.session_state:
    st.session_state.question_index = 0
if "questions" not in st.session_state:
    st.session_state.questions = []
if "feedback" not in st.session_state:
    st.session_state.feedback = ""

# Groq API call
def call_groq(prompt):
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama3-8b-8192",
            "messages": [{"role": "user", "content": prompt}]
        }
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"❌ Groq API failed: {e}")
        return "⚠️ Could not get response from Groq API."

# PDF parser
def extract_text_from_pdf(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# Stage 1: Resume Upload
if st.session_state.stage == "upload":
    uploaded = st.file_uploader("📄 Upload your resume (PDF only)", type=["pdf"])
    if uploaded:
        st.session_state.resume_text = extract_text_from_pdf(uploaded)
        st.session_state.stage = "extract_skills"
        st.rerun()

# Stage 2: Skill Extraction
elif st.session_state.stage == "extract_skills":
    with st.spinner("Extracting skills from your resume..."):
        prompt = f"""
You're an expert resume analyzer.

Extract key technical skills mentioned in this resume:

{st.session_state.resume_text}

Return as a comma-separated list only.
"""
        st.session_state.skills = call_groq(prompt)
        st.session_state.stage = "confirm_skills"
        st.rerun()

# Stage 3: Confirm Skills
elif st.session_state.stage == "confirm_skills":
    st.markdown("### 🧠 Skills Identified from Resume:")
    st.markdown(f"**{st.session_state.skills}**")
    answer = st.radio("Are these correct?", ["Yes", "No"])
    if answer == "Yes":
        st.session_state.stage = "ask_questions"
        st.rerun()
    elif answer == "No":
        manual = st.text_input("Please enter your correct skills (comma-separated):")
        if manual:
            st.session_state.skills = manual
            st.session_state.stage = "ask_questions"
            st.rerun()

# Stage 4: Generate 5 Questions
elif st.session_state.stage == "ask_questions":
    if not st.session_state.questions:
        with st.spinner("Generating interview questions..."):
            prompt = f"""
You are an AI interviewer.

Generate 5 diverse technical interview questions on: {st.session_state.skills}

Include:
- 2 MCQ (multiple choice with 4 options, mark correct)
- 1 MSQ (multiple select, multiple correct options)
- 2 long answer conceptual questions

Format each question like this:
Q: ...
Options: A. ..., B. ..., C. ..., D. ...
Correct: B

If no options, skip Options/Correct.
"""
            raw_q = call_groq(prompt)
            st.session_state.questions = raw_q.strip().split("\n\n")
    if st.session_state.question_index < len(st.session_state.questions):
        q = st.session_state.questions[st.session_state.question_index]
        st.markdown(f"### ❓ Question {st.session_state.question_index+1}")
        st.markdown(q)
        if st.button("Next Question"):
            st.session_state.question_index += 1
            st.rerun()
    else:
        st.session_state.stage = "feedback"
        st.rerun()

# Stage 5: Feedback + Suggest Topics
elif st.session_state.stage == "feedback":
    with st.spinner("Generating feedback and suggested topics..."):
        q_list = "\n".join(st.session_state.questions)
        prompt = f"""
Analyze the following technical questions:

{q_list}

Now generate:
1. General feedback for the candidate based on these questions
2. A list of 15 important topics they must revise with 1 sample question each

Format:
**Feedback:** ...
**Topics to Revise:**
1. Topic - Sample Q: ...
"""
        st.session_state.feedback = call_groq(prompt)
    st.markdown("## ✅ Feedback & Preparation Plan")
    st.markdown(st.session_state.feedback)
    st.success("🧠 You're all set! Good luck with your interview!")

