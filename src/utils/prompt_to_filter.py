import os
import json
import pandas as pd
import re
from groq import Groq
from dotenv import load_dotenv, find_dotenv

dotenv_path = find_dotenv()
load_dotenv(dotenv_path)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise Exception("GROQ_API_KEY not found in .env!")

client = Groq(api_key=GROQ_API_KEY)

# SYSTEM PROMPT 
SYSTEM_PROMPT = """
You are an expert assistant that converts natural language requests into strict JSON filter rules.

Rules:
- Output must be valid JSON only.
- Detect logical operators in the user's request:
  - if user uses "and", "AND", or "&", set "logic": "AND"
  - if user uses "or", "OR", "|", set "logic": "OR"
- JSON structure must include:
{
  "logic": "<AND/OR>",        
  "filters": [
    {
      "column": "<column_name>",
      "type": "<operation>",
      "value": <value_if_applicable>
    }
  ]
}
- Allowed types: equals, not equals, contains, greater_than, less_than, is null, is not null
- Recognize synonyms:
  - equals, eq, equal → "equals"
  - not equal, neq, != → "not equals"
  - greater than, > → "greater_than"
  - less than, < → "less_than"
  - contains, includes → "contains"
- Use only columns provided.
- Do NOT include explanations, comments, or extra text outside JSON.
"""

# Utility: Extract JSON
def extract_json(text):
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return {"logic": "AND", "filters": []}
    return {"logic": "AND", "filters": []}


# Convert natural language prompt to JSON filters
def prompt_to_filters(user_prompt, columns, sample_data=None):
    data_sample_str = json.dumps(sample_data[:10], indent=2) if sample_data else ""

    full_prompt = f"Available columns: {columns}\n"
    if data_sample_str:
        full_prompt += f"Sample data:\n{data_sample_str}\n"
    full_prompt += f"User request: {user_prompt}\n"

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": full_prompt}
        ],
        temperature=0,
        max_tokens=500
    )

    content = response.choices[0].message.content.strip()
    filters = extract_json(content)
    return filters

def read_file(file_path):
    if file_path.endswith(".csv"):
        return pd.read_csv(file_path)
    elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
        return pd.read_excel(file_path)
    elif file_path.endswith(".json"):
        return pd.read_json(file_path)
    else:
        raise Exception("Unsupported file type. Only CSV, Excel, and JSON are supported.")

# Apply filters to DataFrame
def apply_filters(df, filters_json):
    df_filtered = df.copy()
    
    logic = filters_json.get("logic", "AND").upper()
    conditions = filters_json.get("filters", [])
    if not conditions:
        return df_filtered

    # Apply single condition
    def apply_condition(df, cond):
        col = cond.get("column")
        op = cond.get("type")
        val = cond.get("value")

        if col not in df.columns:
            return pd.Series([True] * len(df))  # Ignore unknown columns

        # Convert value type if needed
        col_dtype = df[col].dtype
        if pd.api.types.is_numeric_dtype(col_dtype) and isinstance(val, str):
            try:
                val = float(val)
            except:
                pass

        if op == "equals":
            return df[col] == val
        elif op == "not equals":
            return df[col] != val
        elif op == "contains":
            return df[col].astype(str).str.contains(str(val), na=False)
        elif op == "greater_than":
            return df[col] > val
        elif op == "less_than":
            return df[col] < val
        elif op == "is null":
            return df[col].isnull()
        elif op == "is not null":
            return df[col].notnull()
        else:
            return pd.Series([True] * len(df))  # Ignore unsupported operation

    # Initialize mask
    mask = apply_condition(df_filtered, conditions[0])
    for cond in conditions[1:]:
        if logic == "AND":
            mask &= apply_condition(df_filtered, cond)
        elif logic == "OR":
            mask |= apply_condition(df_filtered, cond)

    return df_filtered[mask]

# function
def analyze_file_with_nl_filter(file_path, user_prompt):
    df = read_file(file_path)
    columns = list(df.columns)

    filters_json = prompt_to_filters(
        user_prompt,
        columns,
        sample_data=df.head(10).to_dict(orient="records")
    )

    filtered_df = apply_filters(df, filters_json)

    print("JSON Filters Applied:")
    print(json.dumps(filters_json, indent=2))
    print("\nFiltered Data:")
    print(filtered_df)

    return filtered_df