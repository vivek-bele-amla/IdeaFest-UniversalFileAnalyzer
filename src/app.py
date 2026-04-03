import streamlit as st

pg = st.navigation([
    st.Page("pages/universal_file_analyzer.py", title="File Analyzer"),
    st.Page("pages/file_compare.py", title="File Comparer"),
    st.Page("pages/data_generator.py", title="Data Generator"),
    st.Page("pages/data_converter.py", title="Data Converter"),
])

pg.run()