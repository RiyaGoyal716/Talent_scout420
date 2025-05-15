# ai_interviewer.py
import os
import openai
import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from docx import Document
from io import StringIO

# Load .env and API keys
load_dotenv()
openai.api_key = os.getenv("GROQ_API_KEY")
openai.api_base = "https://api.groq.com/openai/v1"

# LLM Config
MODEL = "llama3-70b-8192"

def extract_text_from_resume(uploaded_file):
    text = ""
    if uploaded_file.name.endswith('.pdf'):
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            text += page.extract_text() or ""
    elif uploaded_file.name.endswith('.docx'):
        doc = Document(uploaded_file)
        for para in doc.paragraphs:
            text += para.text + "\n"
    elif uploaded_file.name.endswith('.txt'):
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        text = stringio.read()
    else:
        st.warning("Unsupported file format. Upload PDF, DOCX, or TXT.")
    return text.strip()

def generate_interview_questions(resume_text, job_role, level, topic=None):
    prompt = f"""
You are an AI Interviewer. Your task is to generate a set of {level} level interview questions for a candidate applying for the role of {job_role}.
If a topic is specified (like databases, ML, cloud, etc.), generate questions focused on that topic.

Resume of the candidate:
\"\"\"
{resume_text}
\"\"\"

Generate 3 relevant questions and wait for user response before continuing.
If the user says "next topic: XYZ", switch to that topic and generate new questions.
    """
    if topic:
        prompt += f"\n\nCurrent topic: {topic}"
    
    messages = [{"role": "user", "content": prompt}]
    try:
        response = openai.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.6,
            max_tokens=600
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating questions: {e}"

# Streamlit Frontend
def main():
    st.title("🧠 AI Interviewer - SmartHire")
    uploaded_file = st.file_uploader("Upload your Resume", type=["pdf", "docx", "txt"])
    
    if uploaded_file:
        resume_text = extract_text_from_resume(uploaded_file)
        st.success("Resume successfully parsed!")

        job_role = st.text_input("Enter the Job Role (e.g., Data Scientist, Software Engineer)")
        level = st.selectbox("Select Difficulty Level", ["Basic", "Intermediate", "Advanced"])
        topic = st.text_input("Optional: Specify a topic (e.g., Python, System Design, Cloud)")

        if st.button("Start Interview"):
            if job_role:
                questions = generate_interview_questions(resume_text, job_role, level.lower(), topic)
                st.session_state.chat_history = [{"role": "ai", "content": questions}]
                st.session_state.resume_text = resume_text
                st.session_state.job_role = job_role
                st.session_state.level = level.lower()
                st.session_state.topic = topic
            else:
                st.warning("Please enter the job role.")

    # Chat Interface
    if "chat_history" in st.session_state:
        st.subheader("🗨️ Interview Chat")
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        user_input = st.chat_input("Your Answer / Ask for new topic...")

        if user_input:
            with st.chat_message("user"):
                st.markdown(user_input)
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            # Detect topic switch
            if user_input.lower().startswith("next topic:"):
                new_topic = user_input.split("next topic:")[-1].strip()
                new_qs = generate_interview_questions(
                    st.session_state.resume_text,
                    st.session_state.job_role,
                    st.session_state.level,
                    new_topic
                )
                st.session_state.chat_history.append({"role": "ai", "content": new_qs})
            else:
                # Continue in same topic
                followup_prompt = f"""
Here is the candidate's answer:
\"\"\"
{user_input}
\"\"\"

Please provide the next 2 {st.session_state.level} questions for the role of {st.session_state.job_role}.
{"Focus on topic: " + st.session_state.topic if st.session_state.topic else ""}
Resume:
\"\"\"
{st.session_state.resume_text}
\"\"\"
"""
                try:
                    response = openai.chat.completions.create(
                        model=MODEL,
                        messages=[{"role": "user", "content": followup_prompt}],
                        temperature=0.6,
                        max_tokens=500
                    )
                    followup_qs = response.choices[0].message.content.strip()
                    st.session_state.chat_history.append({"role": "ai", "content": followup_qs})
                except Exception as e:
                    st.session_state.chat_history.append({"role": "ai", "content": f"Error: {e}"})

if __name__ == "__main__":
    main()
