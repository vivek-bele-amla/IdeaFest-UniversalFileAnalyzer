import streamlit as st
import pandas as pd
from utils.loader import load_file
from utils.prompt_to_filter import apply_filters, apply_column_selection, prompt_to_filters  # ✅ import apply_filters

st.set_page_config(page_title="Universal File Analyzer", layout="wide")
st.title("Universal File Analyzer")

file = st.file_uploader("Upload a file", type=["json", "csv", "xlsx", "xls", "xml"])

if file:
    try:
        df = load_file(file)
    except Exception as e:
        st.error(f"Error loading file: {e}")
        df = None

    if df is not None and not df.empty:
        st.write(f"{df.shape[0]} Rows  {df.shape[1]} Columns")
        st.dataframe(df.head(10).reset_index(drop=True).rename(lambda x: x + 1))

        user_prompt = st.text_area(
            "Describe your filter in natural language",
            placeholder="Example: show rows where status is failed and amount > 1000"
        )

        if st.button("Apply AI Filter") and user_prompt.strip():
            sample_data = df.head(10).to_dict(orient="records")
            ai_json = prompt_to_filters(user_prompt, list(df.columns), sample_data=sample_data)

            # ✅ Debug is HERE, where ai_json is actually available
            with st.expander("Debug: AI Filters", expanded=False):
                st.json(ai_json)

            filtered_df = apply_filters(df, ai_json)        # ✅ use the one from utils
            filtered_df = apply_column_selection(filtered_df, ai_json)

            st.write(f"Matching rows: {len(filtered_df)}")
            st.dataframe(filtered_df.reset_index(drop=True).rename(lambda x: x + 1))