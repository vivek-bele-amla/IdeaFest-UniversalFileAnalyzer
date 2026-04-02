import streamlit as st
import pandas as pd
from utils.loader import load_file
from utils.prompt_to_filter import prompt_to_filters

st.set_page_config(page_title="Universal File Analyzer", layout="wide")
st.title("Universal File Analyzer")
st.write("Upload any file (JSON, CSV, Excel, XML) and filter with natural language")

file = st.file_uploader("Upload a file", type=["json","csv","xlsx","xls","xml"])

def apply_ai_filters(df, ai_filters):
    filtered_df = df.copy()
    
    for f in ai_filters.get("filters", []):
        col = f.get("column")
        op = f.get("type")   # operator, fully dynamic from AI
        val = f.get("value")

        if col not in filtered_df.columns:
            continue

        # Build a pandas query dynamically based on AI output
        try:
            if val is None:
                # handle null / not null dynamically
                if op.lower() == "is null":
                    filtered_df = filtered_df[filtered_df[col].isnull()]
                elif op.lower() == "is not null":
                    filtered_df = filtered_df[~filtered_df[col].isnull()]
                else:
                    # fallback: skip unknown ops with no value
                    continue
            else:
                # dynamically create a query string
                query_str = f'`{col}` {op} @val'
                filtered_df = filtered_df.query(query_str)
        except Exception:
            # fallback if query fails: try string comparison
            filtered_df = filtered_df[filtered_df[col].astype(str).str.contains(str(val), case=False)]

    return filtered_df

if file:
    try:
        df = load_file(file)
    except Exception as e:
        st.error(f"Error loading file: {e}")
        df = None

    if df is not None and not df.empty:
        st.write(f"{df.shape[0]} Rows  {df.shape[1]} Columns")
        st.dataframe(df.head(10))

        user_prompt = st.text_area(
            "Describe your filter in natural language",
            placeholder="Example: show rows where status is failed and amount > 1000"
        )

        if st.button("Apply AI Filter") and user_prompt.strip():
            sample_data = df.head(10).to_dict(orient="records")
            ai_filters = prompt_to_filters(user_prompt, list(df.columns), sample_data=sample_data)
            ai_filtered_df = apply_ai_filters(df, ai_filters)
            st.write(f"AI matching rows: {len(ai_filtered_df)}")
            st.dataframe(ai_filtered_df)