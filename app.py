import streamlit as st
from streamlit_chat import message
import re
import io
import docx2txt
from datetime import datetime
import pandas as pd

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []

if "candidate_info" not in st.session_state:
    st.session_state.candidate_info = {}

if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""

if "all_responses" not in st.session_state:
    st.session_state.all_responses = []

# -------- Resume text extraction helpers --------
def extract_text_from_pdf(file) -> str:
    import fitz  # PyMuPDF
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_text_from_docx(file) -> str:
    # docx2txt needs a file path or bytes
    text = docx2txt.process(file)
    return text

def extract_text_from_txt(file) -> str:
    return file.read().decode("utf-8")

def extract_text_from_resume(uploaded_file) -> str:
    filetype = uploaded_file.type
    if "pdf" in filetype:
        return extract_text_from_pdf(uploaded_file)
    elif "word" in filetype or uploaded_file.name.endswith(".docx"):
        return extract_text_from_docx(uploaded_file)
    elif "text" in filetype or uploaded_file.name.endswith(".txt"):
        return extract_text_from_txt(uploaded_file)
    else:
        return ""

# -------- Resume info extraction --------
def extract_resume_details(text):
    details = {}

    # Extract email
    emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
    details["email"] = emails[0] if emails else ""

    # Extract phone (simple pattern for international and local)
    phones = re.findall(r"\+?\d[\d\s\-\(\)]{7,}\d", text)
    details["phone"] = phones[0] if phones else ""

    # Extract name (simple heuristic: first non-empty line with 2 words capitalized)
    lines = text.splitlines()
    name = ""
    for line in lines:
        if line.strip():
            words = line.strip().split()
            if 1 < len(words) < 5:
                cap_words = sum(1 for w in words if w[0].isupper())
                if cap_words >= 2:
                    name = line.strip()
                    break
    details["name"] = name

    # Extract skills (simple keyword matching for demo, ideally use a skill list)
    skill_keywords = ["python", "java", "c++", "machine learning", "data analysis",
                      "sql", "aws", "docker", "kubernetes", "spark", "hadoop", "react",
                      "nodejs", "tensorflow", "pandas", "nlp"]
    skills_found = []
    text_lower = text.lower()
    for skill in skill_keywords:
        if skill in text_lower:
            skills_found.append(skill)
    details["skills"] = ", ".join(skills_found)

    # Extract experience years (look for patterns like 'X years', 'X+ years')
    exp = re.findall(r"(\d+)\s*\+?\s*years", text_lower)
    experience_years = max([int(e) for e in exp]) if exp else ""
    details["experience_years"] = experience_years

    return details

# -------- Chatbot logic --------
def generate_interview_questions(topic):
    # For demo, generate 15 basic questions on topic
    base_questions = [
        f"Explain the fundamental concepts of {topic}.",
        f"What are the common challenges faced in {topic}?",
        f"Describe a project where you applied {topic}.",
        f"How do you stay updated with the latest trends in {topic}?",
        f"What tools or frameworks do you use for {topic}?",
        f"Explain a difficult problem you solved related to {topic}.",
        f"How would you explain {topic} to a non-technical person?",
        f"Compare {topic} with alternative approaches or technologies.",
        f"Describe the most important skills for mastering {topic}.",
        f"What are best practices when working with {topic}?",
        f"How do you handle errors or exceptions in {topic}?",
        f"Describe the future outlook or developments in {topic}.",
        f"What books or courses do you recommend for learning {topic}?",
        f"How have you applied {topic} in a team setting?",
        f"Explain how you would optimize performance in {topic}."
    ]
    return "\n\n".join(base_questions)

def chat_logic(user_input):
    user_input_lower = user_input.lower().strip()

    # If user requests question generation
    if user_input_lower.startswith("generate questions on "):
        topic = user_input[21:].strip()
        if not topic:
            return "❗ Please specify a topic after 'Generate questions on'."
        questions = generate_interview_questions(topic)
        return f"Here are 15 questions on *{topic}*:\n\n" + questions

    # Otherwise fallback
    return ("❓ Please ask me to 'Generate questions on <topic>' or type 'continue' to get more questions.")

# -------- Main UI --------
st.set_page_config(page_title="TalentScout AI - Interview Q Generator", page_icon="🧠")

st.title("🧠 TalentScout AI - Interview Question Generator")
st.markdown("Upload your resume, then generate tailored interview questions on any topic!")

st.divider()

# Resume upload & extraction
uploaded_file = st.file_uploader("Upload Resume (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])
if uploaded_file:
    text = extract_text_from_resume(uploaded_file)
    st.session_state.resume_text = text
    if text.strip():
        st.success("✅ Resume text extracted successfully!")
        extracted_info = extract_resume_details(text)
        st.session_state.candidate_info.update(extracted_info)

        st.markdown("### Extracted Resume Details:")
        st.write(f"**Name:** {extracted_info.get('name', '')}")
        st.write(f"**Email:** {extracted_info.get('email', '')}")
        st.write(f"**Phone:** {extracted_info.get('phone', '')}")
        st.write(f"**Skills:** {extracted_info.get('skills', '')}")
        st.write(f"**Experience (years):** {extracted_info.get('experience_years', '')}")
    else:
        st.error("❌ Could not extract text from this file.")

st.divider()

# Optional candidate info editing
with st.expander("Optional: Edit candidate info or add more details"):
    st.session_state.candidate_info["name"] = st.text_input("Name", st.session_state.candidate_info.get("name", ""))
    st.session_state.candidate_info["email"] = st.text_input("Email", st.session_state.candidate_info.get("email", ""))
    st.session_state.candidate_info["phone"] = st.text_input("Phone", st.session_state.candidate_info.get("phone", ""))
    st.session_state.candidate_info["experience"] = st.selectbox("Years of Experience", ["", "0-1", "1-3", "3-5", "5+"],
                                                                   index=["", "0-1", "1-3", "3-5", "5+"].index(st.session_state.candidate_info.get("experience", "")) if st.session_state.candidate_info.get("experience", "") in ["", "0-1", "1-3", "3-5", "5+"] else 0)
    st.session_state.candidate_info["expected_salary"] = st.text_input("Expected Salary", st.session_state.candidate_info.get("expected_salary", ""))
    st.session_state.candidate_info["graduation_year"] = st.text_input("Graduation Year", st.session_state.candidate_info.get("graduation_year", ""))
    st.session_state.candidate_info["graduation_stream"] = st.text_input("Graduation Stream", st.session_state.candidate_info.get("graduation_stream", ""))

st.divider()

# Chat container
chat_container = st.container()

# User input form
with st.form("chat_input_form", clear_on_submit=True):
    user_input = st.text_input("You:", placeholder="Ask me to generate questions on a topic or type 'continue'")
    submitted = st.form_submit_button("Send")

if submitted and user_input:
    response = chat_logic(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "assistant", "content": response})

with chat_container:
    for i, chat in enumerate(st.session_state.messages):
        is_user = chat["role"] == "user"
        message(chat["content"], is_user=is_user, key=f"msg_{i}")

# Initial greeting
if len(st.session_state.messages) == 0:
    greeting = ("Hello! 👋 To get started, please type:\n\n"
                "**Generate questions on <topic>**\n\n"
                "Example: Generate questions on Python programming")
    st.session_state.messages.append({"role": "assistant", "content": greeting})
    st.experimental_rerun()
