import streamlit as st
import json
import difflib
from html import escape
import re

st.set_page_config(page_title="File Compare with Copy Button", layout="wide")
st.title("File Compare with Fixed Copy Buttons")

# ---- INPUTS ----
col1, col2 = st.columns(2)

with col1:
    st.subheader("File / Text 1")
    file1 = st.file_uploader("Upload first file", key="f1")
    text1_manual = st.text_area("Or paste first text here", height=200, key="t1")

with col2:
    st.subheader("File / Text 2")
    file2 = st.file_uploader("Upload second file", key="f2")
    text2_manual = st.text_area("Or paste second text here", height=200, key="t2")


# ---- UTILITY FUNCTIONS ----
def read_file(file):
    return file.read().decode("utf-8", errors="ignore")


def beautify_text(text, file_type="text"):
    if file_type == "json":
        try:
            return json.dumps(json.loads(text), indent=4)
        except:
            return text
    return text


def detect_type(filename, text):
    if filename and filename.endswith(".json"):
        return "json"
    try:
        json.loads(text)
        return "json"
    except:
        return "text"


def highlight_diff(line1, line2):
    matcher = difflib.SequenceMatcher(None, line1, line2)
    h1, h2 = "", ""
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            h1 += escape(line1[i1:i2])
            h2 += escape(line2[j1:j2])
        elif tag == "replace" or tag == "delete":
            h1 += f"<span style='background-color: #faa'>{escape(line1[i1:i2])}</span>"
        if tag == "replace" or tag == "insert":
            h2 += f"<span style='background-color: #afa'>{escape(line2[j1:j2])}</span>"
    return h1, h2


def colorize_json(text):
    # Simple JSON syntax highlighting
    text = re.sub(r'("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*")',
                  r'<span style="color: #0b7500">\1</span>', text)
    text = re.sub(r'\b(true|false|null)\b', r'<span style="color: #0000ff">\1</span>', text)
    text = re.sub(r'\b([-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)\b',
                  r'<span style="color: #ff6600">\1</span>', text)
    return text


# ---- PROCESS INPUTS ----
text1 = text2 = None
label1 = "Text 1"
label2 = "Text 2"

if file1:
    label1 = file1.name
    text1 = read_file(file1)
elif text1_manual.strip():
    text1 = text1_manual

if file2:
    label2 = file2.name
    text2 = read_file(file2)
elif text2_manual.strip():
    text2 = text2_manual

if text1 is None or text2 is None:
    st.info("Provide both File/Text 1 and File/Text 2 to compare.")
else:
    type1 = detect_type(file1.name if file1 else None, text1)
    type2 = detect_type(file2.name if file2 else None, text2)

    if type1 != type2:
        st.error(f"Both inputs must be of same type: {type1} vs {type2}")
    else:
        text1 = beautify_text(text1, type1)
        text2 = beautify_text(text2, type2)

        if st.button("Compare Files / Texts"):
            lines1 = text1.splitlines()
            lines2 = text2.splitlines()
            diff = difflib.SequenceMatcher(None, lines1, lines2)

            col_diff1, col_diff2 = st.columns(2)
            html1, html2 = "", ""

            # ---- GENERATE HIGHLIGHTED DIFF ----
            for tag, i1, i2, j1, j2 in diff.get_opcodes():
                if tag == "equal":
                    for l1, l2 in zip(lines1[i1:i2], lines2[j1:j2]):
                        html1 += escape(l1) + "<br>"
                        html2 += escape(l2) + "<br>"
                elif tag == "replace":
                    for l1, l2 in zip(lines1[i1:i2], lines2[j1:j2]):
                        h1, h2 = highlight_diff(l1, l2)
                        html1 += h1 + "<br>"
                        html2 += h2 + "<br>"
                elif tag == "delete":
                    for l1 in lines1[i1:i2]:
                        h1, _ = highlight_diff(l1, "")
                        html1 += h1 + "<br>"
                        html2 += "<br>"
                elif tag == "insert":
                    for l2 in lines2[j1:j2]:
                        _, h2 = highlight_diff("", l2)
                        html1 += "<br>"
                        html2 += h2 + "<br>"

            # ---- PANEL STYLE ----
            panel_style = """
                border: 1px solid #ccc;
                padding: 10px;
                background-color: #fdfdfd;
                border-radius: 5px;
                max-height: 600px;
                overflow: auto;
                font-family: monospace;
                position: relative;
            """

            # ---- RENDER PANEL FUNCTION ----
            def render_panel(label, html_content, text_content, file_type):
                if file_type == "json":
                    html_content = colorize_json(html_content)

                container = st.container()
                with container:
                    # Use columns for panel + copy button
                    col_panel, col_button = st.columns([15, 1])
                    with col_button:
                        if st.button("C", key=f"copy-{label}", help=f"Copy {label}"):
                            # Copy only the text content
                            st.experimental_set_clipboard(text_content)
                            st.success(f"{label} copied to clipboard!")

                    with col_panel:
                        st.markdown(f"<div style='{panel_style}'>{html_content}</div>", unsafe_allow_html=True)

            # ---- DISPLAY PANELS ----
            with col_diff1:
                render_panel(label1, html1, text1, type1)
            with col_diff2:
                render_panel(label2, html2, text2, type2)