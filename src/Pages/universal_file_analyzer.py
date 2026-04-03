import streamlit as st
import pandas as pd
import io
from utils.loader import load_file, load_text
from utils.prompt_to_filter import apply_filters, apply_column_selection, prompt_to_filters

st.set_page_config(page_title="Universal File Analyzer", layout="wide")
st.title("Universal File Analyzer")

st.markdown("""
<style>
header[data-testid="stHeader"] { display: none; }

/* Download button strip */
.download-strip {
    display: flex;
    align-items: center;
    gap: 4px;
}
.download-strip .stDownloadButton button {
    padding: 3px 10px;
    font-size: 11px;
    height: 26px;
    min-width: unset;
    border-radius: 4px;
    background-color: transparent;
    border: 1px solid #ccc;
    color: inherit;
}
.download-strip .stDownloadButton button:hover {
    border-color: #888;
    background-color: #f0f0f0;
}
</style>
""", unsafe_allow_html=True)

file = st.file_uploader("Upload a file", type=["json", "csv", "xlsx", "xls", "xml"])

with st.expander("Or paste your data directly", expanded=False):
    pasted_text = st.text_area(
        "Paste JSON, CSV, or XML here",
        height=150,
        placeholder='Paste JSON: [{"col": "val"}] or CSV: col1,col2\\nval1,val2 or XML...',
        label_visibility="collapsed"
    )

df = None

if file:
    progress_bar = st.progress(0, text="Loading file...")
    try:
        progress_bar.progress(30, text="Reading file...")
        df = load_file(file)
        progress_bar.progress(70, text="Processing data...")
        progress_bar.progress(100, text="Done!")
        progress_bar.empty()
    except Exception as e:
        progress_bar.empty()
        st.error(f"Error loading file: {e}")

elif pasted_text.strip():
    progress_bar = st.progress(0, text="Parsing pasted data...")
    try:
        progress_bar.progress(50, text="Processing...")
        df = load_text(pasted_text.strip())
        progress_bar.progress(100, text="Done!")
        progress_bar.empty()
    except Exception as e:
        progress_bar.empty()
        st.error(f"Error parsing pasted data: {e}")

if df is not None and not df.empty:
    st.write(f"{df.shape[0]} Rows  {df.shape[1]} Columns")
    st.dataframe(df.reset_index(drop=True).rename(lambda x: x + 1).rename_axis("No."))

    user_prompt = st.text_area(
        "Describe your filter in natural language",
        placeholder="Example: show rows where status is failed and amount > 1000"
    )

    if st.button("Apply AI Filter") and user_prompt.strip():
        sample_data = df.head(10).to_dict(orient="records")

        ai_progress = st.progress(0, text="Analyzing prompt...")
        ai_json = prompt_to_filters(user_prompt, list(df.columns), sample_data=sample_data)
        ai_progress.progress(60, text="Applying filters...")
        filtered_df = apply_filters(df, ai_json)
        filtered_df = apply_column_selection(filtered_df, ai_json)
        ai_progress.progress(100, text="Done!")
        ai_progress.empty()

        buffer = io.BytesIO()
        filtered_df.to_excel(buffer, index=False, engine="openpyxl")

        # Matching rows left, buttons tightly packed right
        left, right = st.columns([6, 2])

        with left:
            st.markdown(f"**Matching rows:** {len(filtered_df)}")

        with right:
            st.markdown('<div class="download-strip">', unsafe_allow_html=True)
            b1, b2, b3, b4 = st.columns(4)
            with b1:
                st.download_button("JSON", filtered_df.to_json(orient="records", indent=2), "filtered.json", key="dl_json")
            with b2:
                st.download_button("CSV", filtered_df.to_csv(index=False), "filtered.csv", key="dl_csv")
            with b3:
                st.download_button("XLSX", buffer.getvalue(), "filtered.xlsx", key="dl_xlsx")
            with b4:
                st.download_button("XML", filtered_df.to_xml(index=False), "filtered.xml", key="dl_xml")
            st.markdown('</div>', unsafe_allow_html=True)

        st.dataframe(filtered_df.reset_index(drop=True).rename(lambda x: x + 1).rename_axis("No."))