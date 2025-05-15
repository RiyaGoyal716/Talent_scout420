import streamlit as st
from PyPDF2 import PdfReader
import docx2txt
import re
import json

# --- Your existing imports and Groq API setup ---

# Initialize session state variables
if "all_responses" not in st.session_state:
    st.session_state.all_responses = []

if "topic_questions" not in st.session_state:
    st.session_state.topic_questions = []

if "candidate_info" not in st.session_state:
    st.session_state.candidate_info = {}

if "end_chat" not in st.session_state:
    st.session_state.end_chat = False

# ----------------------------
# Helper function: Extract text from uploaded resume
# ----------------------------
def extract_text_from_resume(uploaded_file):
    if uploaded_file.type == "application/pdf":
        pdf_reader = PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    elif uploaded_file.type == "text/plain":
        return uploaded_file.getvalue().decode("utf-8")
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return docx2txt.process(uploaded_file)
    else:
        return ""

# ----------------------------
# Helper function: Call your Groq LLM API for response
# ----------------------------
def generate_llm_response(prompt):
    # Replace with your Groq API call, example:
    # response = groq_llm_api_call(prompt)
    # For demo, we return a mock JSON string:
    mock_response = json.dumps({
        "Full Name": "John Doe",
        "Email": "john.doe@example.com",
        "Phone Number": "+1-234-567-890",
        "Years of Experience": "5",
        "Position(s) applied for": "Software Engineer",
        "Current Location": "San Francisco, CA",
        "Tech Stack": "Python, Java, AWS"
    })
    return mock_response

# ----------------------------
# Extract candidate info from resume text using LLM
# ----------------------------
def extract_candidate_info_from_text(resume_text):
    prompt = f"""
You are an AI assistant. Extract the following candidate details from the resume text below:
- Full Name
- Email
- Phone Number
- Years of Experience
- Position(s) applied for
- Current Location
- Tech Stack

If any info is not available, reply with 'Not mentioned'.

Resume Text:
\"\"\"
{resume_text}
\"\"\"

Provide the info as a JSON object only.
"""
    response = generate_llm_response(prompt)
    try:
        candidate_info = json.loads(response)
    except Exception:
        candidate_info = {"Extracted Info": response}
    return candidate_info

# ----------------------------
# Generate technical questions based on topic (demo)
# ----------------------------
def get_technical_questions(topic):
    # Replace with your actual question generation logic or API call
    return f"1. Explain the basics of {topic}.\n2. What are advanced concepts in {topic}?\n3. How do you apply {topic} in real projects?"

# ----------------------------
# Chat logic after resume processing
# ----------------------------
def chat_logic(user_input):
    if user_input.lower() in ["exit", "quit", "bye", "end"]:
        st.session_state.end_chat = True
        # You can add your data saving logic here if needed
        return "✅ Thank you for chatting with TalentScout! We’ll be in touch shortly. Goodbye! 👋"

    if "generate questions on" in user_input.lower():
        topic = user_input.lower().split("generate questions on")[-1].strip()
        qns = get_technical_questions(topic)
        st.session_state.topic_questions.append((topic, qns))
        st.session_state.all_responses.append({"User Input": user_input, "AI Response": qns})
        return f"Here are your questions on **{topic}**:\n\n{qns}"

    return "🤖 You can ask me to generate technical questions by typing 'Generate questions on ...' or type 'end' to finish."

# ----------------------------
# Streamlit UI Layout
# ----------------------------

st.set_page_config(page_title="TalentScout AI Interviewer", page_icon="🤖")

st.title("🤖 TalentScout AI Interviewer")

with st.sidebar:
    st.header("Upload Resume")
    uploaded_file = st.file_uploader("📄 Upload Resume (PDF, DOCX, TXT)", type=["pdf", "txt", "docx"])
    if uploaded_file:
        with st.spinner("Extracting text and info from resume..."):
            resume_text = extract_text_from_resume(uploaded_file)
            candidate_info = extract_candidate_info_from_text(resume_text)
            st.session_state.candidate_info = candidate_info
            st.session_state.candidate_info["Resume Excerpt"] = resume_text[:300] + "..."
            # For demo, add some questions from resume content
            topic_q = get_technical_questions("Resume Content")
            st.session_state.topic_questions.append(("Resume Content", topic_q))
            st.session_state.all_responses.append({"Resume Extract": resume_text[:300], "Questions": topic_q})
        st.success("✅ Resume processed and candidate info extracted.")

if st.session_state.candidate_info:
    with st.sidebar.expander("👤 Extracted Candidate Info", expanded=True):
        for k, v in st.session_state.candidate_info.items():
            st.markdown(f"**{k}:** {v}")

if not st.session_state.end_chat:
    user_input = st.text_input("💬 Enter your message or 'Generate questions on <topic>'", key="input")
    if user_input:
        response = chat_logic(user_input)
        st.markdown(f"**TalentScout:** {response}")

else:
    st.info("Chat session ended. Please refresh to start a new session.")
