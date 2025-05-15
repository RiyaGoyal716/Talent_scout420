# app.py

import streamlit as st
from streamlit_chat import message
import os
import requests
import fitz  # PyMuPDF
import time
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

st.set_page_config(page_title="TalentScout AI - Hiring Assistant", page_icon="🧠")

st.markdown("## 🧠 TalentScout AI: Resume-Based Interviewer")
st.caption("Upload your resume. Get skill-based questions, personalized feedback, and preparation topics.")

# ----------------------------
# Helper Functions
# ----------------------------

def extract_text_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def ask_groq(prompt):
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
    return res.json()["choices"][0]["message"]["content"].strip()

def extract_skills(resume_text):
    prompt = f"Extract the key technical skills from the following resume text:\n\n{resume_text}\n\nReturn them as a comma-separated list only."
    skills = ask_groq(prompt)
    return [s.strip() for s in skills.split(",") if s.strip()]

def generate_questions(skills):
    skill_list = ', '.join(skills)
    prompt = f"""
You are an expert technical interviewer. Based on these skills: {skill_list}, generate 5 questions:
- 2 [MCQ]
- 2 [MSQ]
- 1 [LONG]

Format strictly as:
[MCQ]
Q: ...
Options:
A. ...
B. ...
C. ...
D. ...
Correct: ...

[MSQ]
Q: ...
Options:
A. ...
B. ...
C. ...
D. ...
Correct: ..., ...

[LONG]
Q: ...
"""
    return ask_groq(prompt)

def evaluate_long_answer(question, user_answer):
    prompt = f"""
Evaluate the following answer to this question:

Question: {question}
Answer: {user_answer}

Score it from 0 to 5.
Then provide a 2-3 sentence feedback and suggest improvements.

Format:
Score: ...
Feedback: ...
Suggestions: ...
"""
    return ask_groq(prompt)

def generate_prep_topics(skills):
    prompt = f"List 15 important technical topics or questions a candidate should prepare for based on these skills: {', '.join(skills)}. Use bullet points."
    return ask_groq(prompt)

# ----------------------------
# Session State
# ----------------------------

if "resume_text" not in st.session_state:
    st.session_state.resume_text = None
if "skills" not in st.session_state:
    st.session_state.skills = None
if "questions" not in st.session_state:
    st.session_state.questions = []
if "answers" not in st.session_state:
    st.session_state.answers = []
if "step" not in st.session_state:
    st.session_state.step = "upload"
if "feedback" not in st.session_state:
    st.session_state.feedback = ""
if "topics" not in st.session_state:
    st.session_state.topics = ""

# ----------------------------
# UI Workflow
# ----------------------------

if st.session_state.step == "upload":
    uploaded = st.file_uploader("📄 Upload your resume (PDF)", type=["pdf"])
    if uploaded:
        st.session_state.resume_text = extract_text_from_pdf(uploaded)
        with st.spinner("Extracting skills..."):
            st.session_state.skills = extract_skills(st.session_state.resume_text)
        st.session_state.step = "confirm_skills"
        st.rerun()

elif st.session_state.step == "confirm_skills":
    st.markdown("### 🧠 Skills extracted:")
    st.success(", ".join(st.session_state.skills))
    choice = st.radio("Are these correct?", ["Yes", "No"])
    if choice == "Yes":
        with st.spinner("Generating questions..."):
            questions_text = generate_questions(st.session_state.skills)
            st.session_state.questions = [q.strip() for q in questions_text.split("\n\n") if q.strip()]
        st.session_state.step = "qa"
        st.rerun()
    else:
        manual = st.text_input("List your core skills separated by commas")
        if manual:
            st.session_state.skills = [s.strip() for s in manual.split(",")]
            with st.spinner("Generating questions..."):
                questions_text = generate_questions(st.session_state.skills)
                st.session_state.questions = [q.strip() for q in questions_text.split("\n\n") if q.strip()]
            st.session_state.step = "qa"
            st.rerun()

elif st.session_state.step == "qa":
    q_idx = len(st.session_state.answers)
    if q_idx < len(st.session_state.questions):
        current_q = st.session_state.questions[q_idx]
        st.markdown(f"**Q{q_idx+1}:**\n{current_q}")
        user_ans = st.text_input("Your Answer:", key=f"ans_{q_idx}")
        if user_ans:
            st.session_state.answers.append({"question": current_q, "answer": user_ans})
            st.rerun()
    else:
        # Evaluate the long answer (assumed to be the last)
        last_q = st.session_state.questions[-1]
        last_ans = st.session_state.answers[-1]["answer"]
        with st.spinner("Generating feedback..."):
            st.session_state.feedback = evaluate_long_answer(last_q, last_ans)
            st.session_state.topics = generate_prep_topics(st.session_state.skills)
        st.session_state.step = "result"
        st.rerun()

elif st.session_state.step == "result":
    st.success("✅ Interview complete! Here's your feedback:")
    st.markdown(f"### 📝 Long Answer Feedback\n{st.session_state.feedback}")
    st.markdown("### 📌 Topics You Should Prepare:")
    st.markdown(st.session_state.topics)
    st.balloons()
