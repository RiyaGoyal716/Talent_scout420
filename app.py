import streamlit as st
from streamlit_chat import message
import os
import requests
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

st.set_page_config(page_title="TalentScout AI - Hiring Assistant", page_icon="🧠", layout="centered")

# Custom CSS for styling
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

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []
if "stage" not in st.session_state:
    st.session_state.stage = "upload_resume"
if "candidate_info" not in st.session_state:
    st.session_state.candidate_info = {}
if "skills" not in st.session_state:
    st.session_state.skills = []
if "questions" not in st.session_state:
    st.session_state.questions = []
if "current_question" not in st.session_state:
    st.session_state.current_question = 0
if "answers" not in st.session_state:
    st.session_state.answers = []
if "end_chat" not in st.session_state:
    st.session_state.end_chat = False

# Function to send prompt to Groq LLaMA3 API
def ask_groq(prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        st.error(f"❌ Groq API error: {e}")
        return None

# Extract skills from resume text
def extract_skills_from_resume(resume_text):
    prompt = f"""
Extract the key technical skills from the following resume text. Provide a comma-separated list of skills only:

{resume_text}
"""
    response = ask_groq(prompt)
    if response:
        skills = [skill.strip() for skill in response.split(",") if skill.strip()]
        return skills
    else:
        return []

# Generate interview questions based on skills
def generate_questions(skills):
    skills_str = ", ".join(skills)
    prompt = f"""
You are a technical interviewer.

Generate a list of 5 interview questions based on these skills: {skills_str}.

Include a mix of question types: multiple choice (MCQ), multiple select (MSQ), and long answer questions.

Format each question clearly, including options where applicable, like so:

[MCQ] Question text?
Options:
A. Option 1
B. Option 2
C. Option 3
D. Option 4

[MSQ] Question text?
Options:
A. Option 1
B. Option 2
C. Option 3
D. Option 4

[Long] Question text?
"""
    response = ask_groq(prompt)
    if response:
        questions = [q.strip() for q in response.split("\n\n") if q.strip()]
        return questions
    else:
        return []

# Generate feedback and important topics
def generate_feedback_and_topics(answers, skills):
    ans_text = "\n".join([f"Q{i+1}: {a}" for i,a in enumerate(answers)])
    skills_str = ", ".join(skills)
    prompt = f"""
You are a senior hiring manager.

Given the candidate's answers below:

{ans_text}

And the candidate's skills: {skills_str}

Provide:

1. A concise constructive feedback summary on their performance.
2. A list of the 15 most important topics and questions they should prepare to improve for the role.

Format:

Feedback:
...

Important Topics:
1. ...
2. ...
...
15. ...
"""
    response = ask_groq(prompt)
    return response or "Sorry, feedback generation failed."

# Main chat logic to handle conversation stages
def chat_logic(user_input):

    if user_input.lower() in ["exit", "quit", "bye", "end"]:
        st.session_state.end_chat = True
        return "✅ Thank you for chatting with TalentScout! We’ll be in touch shortly. Goodbye! 👋"

    stage = st.session_state.stage

    if stage == "upload_resume":
        st.session_state.candidate_info["Resume Text"] = user_input
        st.session_state.skills = extract_skills_from_resume(user_input)
        if not st.session_state.skills:
            return "⚠️ Couldn't extract any skills from the resume. Please try again or type the skills manually."
        st.session_state.stage = "confirm_skills"
        skills_str = ", ".join(st.session_state.skills)
        return f"🔍 We found these key skills in your resume:\n\n**{skills_str}**\n\nIs this correct? (yes/no)"

    if stage == "confirm_skills":
        if user_input.lower() in ["yes", "y"]:
            st.session_state.stage = "ask_questions"
            st.session_state.questions = generate_questions(st.session_state.skills)
            st.session_state.current_question = 0
            st.session_state.answers = []
            if not st.session_state.questions:
                return "⚠️ Sorry, I couldn't generate questions for your skills. Please try again later."
            return f"🎯 Great! Let's start with question 1:\n\n{st.session_state.questions[0]}"
        elif user_input.lower() in ["no", "n"]:
            st.session_state.stage = "manual_skills"
            return "Please list your required skills separated by commas."
        else:
            return "Please answer 'yes' or 'no'. Is the extracted skills list correct?"

    if stage == "manual_skills":
        skills = [s.strip() for s in user_input.split(",") if s.strip()]
        if not skills:
            return "Please enter at least one skill."
        st.session_state.skills = skills
        st.session_state.stage = "ask_questions"
        st.session_state.questions = generate_questions(skills)
        st.session_state.current_question = 0
        st.session_state.answers = []
        if not st.session_state.questions:
            return "⚠️ Sorry, I couldn't generate questions for your skills. Please try again later."
        return f"👍 Thanks! Let's start with question 1:\n\n{st.session_state.questions[0]}"

    if stage == "ask_questions":
        st.session_state.answers.append(user_input)
        st.session_state.current_question += 1

        if st.session_state.current_question < min(5, len(st.session_state.questions)):
            q = st.session_state.questions[st.session_state.current_question]
            return f"Question {st.session_state.current_question + 1}:\n\n{q}"
        else:
            st.session_state.stage = "feedback"
            feedback = generate_feedback_and_topics(st.session_state.answers, st.session_state.skills)
            return f"📝 Here's your feedback and important topics to prepare:\n\n{feedback}\n\nThank you for participating!"

    if stage == "feedback":
        st.session_state.end_chat = True
        return "✅ This concludes our interview simulation. Good luck!"

    return "❓ Sorry, I didn't understand that. Please try again."

# -----------------
# Streamlit UI
# -----------------

st.markdown("## 🧠 TalentScout AI Assistant")
st.caption("Paste your resume text below and get tailored technical interview questions and personalized feedback.")

# Display chat history
with st.container():
    for i, msg in enumerate(st.session_state.messages):
        message(msg["content"], is_user=msg["role"] == "user", key=str(i))

if not st.session_state.end_chat:
    user_prompt = st.chat_input("Type here to talk to TalentScout...")

    if user_prompt:
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        bot_response = chat_logic(user_prompt)
        time.sleep(0.2)  # small delay for UX
        st.session_state.messages.append({"role": "assistant", "content": bot_response})

        st.experimental_rerun()

else:
    st.info("💡 The interview session has ended. Refresh the page to start a new session.")

# Footer
st.markdown("---")
st.caption("© 2025 TalentScout AI | Powered by Groq LLaMA3 API")
