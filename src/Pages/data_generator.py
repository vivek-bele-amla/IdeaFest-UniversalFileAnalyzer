import streamlit as st
from utils.prompt_to_data_generator import generate_sample_data
import json

st.title("Data Generator")

st.markdown("""
<style>
    header[data-testid="stHeader"] { display: none; }
""", unsafe_allow_html=True)

user_input = st.text_area(
    "Enter your prompt here:",
    "Generate JSON data for users with userid, username, email, and password"
)

if st.button("Generate"):
    if not user_input.strip():
        st.warning("Please enter a prompt first!")
    else:
        result = generate_sample_data(user_input)
        st.subheader("Output:")
        st.code(result)

        file_ext = "txt"
        mime_type = "text/plain"
        trimmed = result.strip()

        try:
            json.loads(trimmed)
            file_ext = "json"
            mime_type = "application/json"
        except:
            if "\n" in trimmed and "," in trimmed:
                file_ext = "csv"
                mime_type = "text/csv"

            elif trimmed.startswith("|") and "|" in trimmed:
                file_ext = "md"
                mime_type = "text/markdown"

            elif trimmed.startswith("<?xml") or (trimmed.startswith("<") and trimmed.endswith(">")):
                file_ext = "xml"
                mime_type = "application/xml"

        st.download_button(
            label=f"Download Output ({file_ext})",
            data=result,
            file_name=f"ai_output.{file_ext}",
            mime=mime_type
        )