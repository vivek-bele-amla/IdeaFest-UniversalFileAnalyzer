import streamlit as st
import os
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

st.markdown("""
<style>
    /* Align everything to the left */
    .stApp .block-container { padding-left: 2rem; padding-right: 2rem; }
</style>
""", unsafe_allow_html=True)

if not OPENAI_API_KEY:
    raise Exception("OPENAI_API_KEY not found in .env file")

client = OpenAI(api_key=OPENAI_API_KEY)

def convert_file_with_prompt(file_content, user_prompt):
    if not file_content.strip():
        return "File content is empty"
    if not user_prompt.strip():
        return "Prompt is empty"

    SYSTEM_PROMPT = """
    You are a universal file converter AI.
    Your tasks:
    1. Detect the input format (JSON, XML, CSV, TEXT)
    2. Convert it into the format requested by the user
    Rules:
    - Output ONLY the converted result
    - Do NOT add explanations
    - Do NOT wrap in code blocks
    - Maintain full data accuracy
    - Ensure output is VALID format
    Format rules:
    - JSON → valid JSON
    - XML → proper tags with a single root element
    - CSV → include headers
    - If unclear → return best possible valid format
    """

    final_prompt = f"""
    User Request:
    {user_prompt}

    File Content:
    {file_content}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": final_prompt}
        ],
        temperature=0,
        max_tokens=3000
    )

    output = response.choices[0].message.content.strip()
    output = output.replace("```xml", "").replace("```json", "").replace("```csv", "").replace("```", "").strip()
    return output

def detect_extension(output):
    output = output.strip()
    if output.startswith("{") or output.startswith("["):
        return "json"
    elif output.startswith("<"):
        return "xml"
    elif "," in output and "\n" in output:
        return "csv"
    else:
        return "txt"

st.set_page_config(page_title="Data Converter", layout="wide")
st.title("Data Converter")

uploaded_file = st.file_uploader("Upload File", type=["json", "xml", "csv", "txt"])
user_prompt = st.text_area("Enter conversion instruction", placeholder="Example: Convert this JSON to XML")

def read_file(file):
    return file.read().decode("utf-8", errors="ignore")

if st.button("Convert File"):
    if not uploaded_file:
        st.warning("Please upload a file")
    elif not user_prompt.strip():
        st.warning("Please enter a prompt")
    else:
        file_content = read_file(uploaded_file)
        progress_bar = st.progress(0, text="Processing file...")
        progress_bar.progress(30, text="Sending request to AI...")
        output = convert_file_with_prompt(file_content, user_prompt)
        progress_bar.progress(70, text="Finalizing output...")
        progress_bar.progress(100, text="Done!")
        progress_bar.empty()

        st.subheader("Converted Output")
        st.code(output)

        file_ext = detect_extension(output)
        file_name = f"converted_output.{file_ext}"
        st.download_button(
            "Download File",
            output,
            file_name=file_name,
            mime="application/json" if file_ext == "json" else f"text/{file_ext}"
        )