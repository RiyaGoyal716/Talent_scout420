import streamlit as st
import os
import requests
from dotenv import load_dotenv
import re

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.ai/v1/llama3/generate"  # Replace if your actual endpoint differs

st.set_page_config(page_title="Groq Interview Question Generator", page_icon="🎯")

# Initialize session state
if "topic" not in st.session_state:
    st.session_state.topic = None
if "batch_num" not in st.session_state:
    st.session_state.batch_num = 0
if "history" not in st.session_state:
    st.session_state.history = []

def call_groq_api(prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": prompt,
        "max_tokens": 512,
        "temperature": 0.7,
        "top_p": 0.95,
        "stop": ["###"]
    }
    try:
        response = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        text = result.get("choices", [{}])[0].get("text", "").strip()
        return text
    except Exception as e:
        return f"Error calling Groq API: {e}"

def generate_prompt(topic, batch_num):
    return (
        f"Generate a batch of 10-15 interview questions for the role/topic '{topic}'. "
        f"Include a mix of easy to advanced level questions, including situational questions, coding snippets, "
        f"and questions typically asked in MNC interviews. "
        f"Format output as numbered questions with brief answers. "
        f"This is batch number {batch_num}.\n\n"
        f"Batch {batch_num} questions:\n"
    )

def parse_and_display_questions(text):
    """
    Parses numbered questions and answers from text and displays nicely in Streamlit.
    Expected format: 
    1. Question?
       Answer: ...
    """
    # Split by numbered questions (e.g. 1. 2. 3.)
    pattern = r"(\d+)\.\s*(.+?)(?=(\n\d+\.|\Z))"
    matches = re.findall(pattern, text, flags=re.S)
    if not matches:
        # Fallback: show raw text if parsing fails
        st.text(text)
        return

    for num, qa_text, _ in matches:
        # Try to split question and answer if "Answer:" present
        parts = re.split(r"Answer\s*:\s*", qa_text, maxsplit=1, flags=re.I)
        question = parts[0].strip()
        answer = parts[1].strip() if len(parts) > 1 else None

        st.markdown(f"**Q{num}. {question}**")
        if answer:
            # Detect code snippets inside answer (simple heuristic for ``` or indentation)
            if "```" in answer:
                st.markdown(f"**Answer:**")
                st.code(answer.strip("``` \n"))
            else:
                st.markdown(f"**Answer:** {answer}")
        else:
            st.markdown("_Answer not provided._")
        st.markdown("---")

def main():
    st.title("🎯 Groq Interview Question Generator")
    st.write(
        "Type commands below:\n"
        "- `Generate questions on <topic>` to start a new question batch.\n"
        "- `continue` to get the next batch of questions.\n"
        "- `exit` to reset the session."
    )

    user_input = st.text_input("Your command or topic:", key="user_input")

    if user_input:
        user_input_lower = user_input.strip().lower()

        if user_input_lower.startswith("generate questions on"):
            topic = user_input[len("generate questions on"):].strip()
            if not topic:
                st.warning("Please specify a topic after 'Generate questions on'")
                return
            st.session_state.topic = topic
            st.session_state.batch_num = 1
            st.session_state.history = []
        elif user_input_lower == "continue":
            if not st.session_state.topic:
                st.warning("Please start by typing: Generate questions on <topic>")
                return
            st.session_state.batch_num += 1
        elif user_input_lower in ["exit", "quit", "stop"]:
            st.success("Session ended. Start again by typing 'Generate questions on <topic>'.")
            st.session_state.topic = None
            st.session_state.batch_num = 0
            st.session_state.history = []
            return
        else:
            st.info("Invalid command. Use 'Generate questions on <topic>', 'continue', or 'exit'.")
            return

        prompt = generate_prompt(st.session_state.topic, st.session_state.batch_num)
        with st.spinner(f"Generating batch {st.session_state.batch_num} questions for '{st.session_state.topic}'..."):
            response_text = call_groq_api(prompt)

        if response_text.startswith("Error"):
            st.error(response_text)
            return

        st.session_state.history.append((st.session_state.batch_num, response_text))

        st.markdown(f"## Batch {st.session_state.batch_num} Questions for **{st.session_state.topic}**")
        parse_and_display_questions(response_text)

if __name__ == "__main__":
    main()
