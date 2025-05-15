import streamlit as st
from dotenv import load_dotenv
import os
import fitz  # PyMuPDF
import requests
import re

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

st.set_page_config(page_title="TalentScout AI", page_icon="🧠")
st.title("🧠 TalentScout AI - Resume Interview Assistant")

# ----- SESSION STATE -----
if "stage" not in st.session_state:
    st.session_state.stage = "upload"
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "skills" not in st.session_state:
    st.session_state.skills = ""
if "questions" not in st.session_state:
    st.session_state.questions = []
if "answers" not in st.session_state:
    st.session_state.answers = []
if "current_question" not in st.session_state:
    st.session_state.current_question = 0
if "feedback" not in st.session_state:
    st.session_state.feedback = ""

# ----- UTILS -----
def call_groq(prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}]
    }
    res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
    return res.json()["choices"][0]["message"]["content"]

def extract_text_from_pdf(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    return "".join(page.get_text() for page in doc)

def parse_questions(raw_text):
    question_blocks = raw_text.strip().split("\n\n")
    questions = []
    for block in question_blocks:
        question = {"question": "", "options": [], "correct": "", "type": "long"}
        lines = block.strip().split("\n")
        for line in lines:
            if line.startswith("Q:"):
                question["question"] = line[2:].strip()
            elif line.startswith("Options:"):
                opts = re.findall(r'[A-D]\. [^,]+', line)
                question["options"] = opts
                question["type"] = "mcq"
            elif line.startswith("Correct:"):
                corr = line.split(":")[1].strip()
                if "," in corr:
                    question["correct"] = [c.strip() for c in corr.split(",")]
                    question["type"] = "msq"
                else:
                    question["correct"] = corr.strip()
                    if question["type"] != "msq":
                        question["type"] = "mcq"
        questions.append(question)
    return questions

# ----- APP STAGES -----

# 1. Upload resume
if st.session_state.stage == "upload":
    uploaded = st.file_uploader("📄 Upload your resume (PDF)", type="pdf")
    if uploaded:
        st.session_state.resume_text = extract_text_from_pdf(uploaded)
        st.session_state.stage = "extract_skills"
        st.rerun()

# 2. Extract skills using Groq
elif st.session_state.stage == "extract_skills":
    with st.spinner("Extracting skills..."):
        prompt = f"Extract key technical skills from this resume text:\n{st.session_state.resume_text}\nReturn as comma-separated list only."
        st.session_state.skills = call_groq(prompt)
    st.session_state.stage = "confirm_skills"
    st.rerun()

# 3. Confirm or edit skills
elif st.session_state.stage == "confirm_skills":
    st.markdown("### Skills Found:")
    st.success(st.session_state.skills)
    confirm = st.radio("Are these skills correct?", ["Yes", "No"])
    if confirm == "Yes":
        st.session_state.stage = "generate_questions"
        st.rerun()
    else:
        manual = st.text_input("Enter correct skills (comma-separated):")
        if manual:
            st.session_state.skills = manual
            st.session_state.stage = "generate_questions"
            st.rerun()

# 4. Generate questions
elif st.session_state.stage == "generate_questions":
    with st.spinner("Generating questions..."):
        prompt = f"""
Generate 5 interview questions based on these skills: {st.session_state.skills}.
Include:
- 2 MCQ (with Options: A, B, C, D and correct)
- 1 MSQ (multiple correct answers)
- 2 Long Answer

Use format:
Q: What is X?
Options: A. ..., B. ..., C. ..., D. ...
Correct: B
"""
        raw = call_groq(prompt)
        st.session_state.questions = parse_questions(raw)
    st.session_state.stage = "ask_questions"
    st.rerun()

# 5. Ask questions one by one
elif st.session_state.stage == "ask_questions":
    q_idx = st.session_state.current_question
    if q_idx < len(st.session_state.questions):
        q = st.session_state.questions[q_idx]
        st.markdown(f"### Question {q_idx + 1}: {q['question']}")
        user_answer = None

        if q["type"] == "mcq":
            user_answer = st.radio("Choose one:", q["options"])
        elif q["type"] == "msq":
            user_answer = st.multiselect("Choose all that apply:", q["options"])
        else:
            user_answer = st.text_area("Your Answer:")

        if st.button("Submit Answer"):
            st.session_state.answers.append(user_answer)
            st.session_state.current_question += 1
            st.rerun()
    else:
        st.session_state.stage = "evaluate"
        st.rerun()

# 6. Evaluate responses
elif st.session_state.stage == "evaluate":
    score = 0
    feedback = []

    for i, q in enumerate(st.session_state.questions):
        user_ans = st.session_state.answers[i]
        if q["type"] == "mcq":
            correct = q["correct"]
            if user_ans.startswith(correct):
                score += 1
        elif q["type"] == "msq":
            correct_set = set(q["correct"])
            selected_set = set([opt[0] for opt in user_ans])
            if correct_set == selected_set:
                score += 1
        else:
            # Evaluate long answers with Groq
            long_feedback = call_groq(f"Evaluate this answer:\nQuestion: {q['question']}\nAnswer: {user_ans}\nGive detailed feedback:")
            feedback.append(f"**Q{i+1} Feedback:** {long_feedback}")

    final_feedback = f"🧠 You scored {score} out of 5.\n\n" + "\n\n".join(feedback)
    st.session_state.feedback = final_feedback
    st.session_state.stage = "result"
    st.rerun()

# 7. Show results
elif st.session_state.stage == "result":
    st.success("✅ Interview Completed!")
    st.markdown(st.session_state.feedback)
