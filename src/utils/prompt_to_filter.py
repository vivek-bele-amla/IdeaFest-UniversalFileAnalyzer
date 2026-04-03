import os
import json
import re
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise EnvironmentError("OPENAI_API_KEY not found in .env")

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
You are a data filter assistant. Convert natural language requests into a JSON object for filtering a pandas DataFrame.

OUTPUT SCHEMA:
{
  "logic": "AND" | "OR",
  "filters": [
    {
      "column": "<exact column name from provided list>",
      "type": "equals" | "not_equals" | "greater_than" | "less_than" | "contains" | "is_null" | "is_not_null",
      "value": "<comparison value, omit for is_null / is_not_null>"
    }
  ],
  "columns": ["<col1>", "<col2>"],
  "column_pattern": {
    "type": "starts_with" | "contains",
    "value": "<pattern>"
  }
}

RULES:
1. "logic" controls how multiple filters combine. Default to "AND".
2. Filter types:
   - equals / not_equals       → exact match
   - greater_than / less_than  → numeric comparison
   - contains                  → substring match
   - is_null / is_not_null     → presence check (no value needed)
3. "not null", "has value", "exists", "present" → is_not_null
4. "null", "missing", "empty"                   → is_null
5. Column names in BOTH "filters" and "columns" MUST exactly match the provided column list character-for-character, including spaces and casing.
6. If the user requests specific columns to display → populate "columns".
7. If the user requests columns by pattern → populate "column_pattern".
8. If the user states a condition (equals, greater than, is true, less than, etc.) → populate "filters". Do NOT put conditions in "columns".
9. A request can have BOTH "columns" (display) and "filters" (conditions) at the same time.
10. Never put column selection logic inside "filters".
11. If no filters apply → return "filters": []

EXAMPLE:
Available columns: ["Product Id", "SKU", "Drop Ship Product"]
User: give me Product Id, SKU and Drop Ship Product columns where Drop Ship Product is true and Product Id less than 1000

Output:
{
  "logic": "AND",
  "filters": [
    { "column": "Drop Ship Product", "type": "equals", "value": "true" },
    { "column": "Product Id", "type": "less_than", "value": "1000" }
  ],
  "columns": ["Product Id", "SKU", "Drop Ship Product"]
}
"""

NULL_KEYWORDS = {
    "is_not_null": ["not null", "not empty", "has value", "exists", "present"],
    "is_null": ["null", "empty", "missing"],
}

FILTER_OPS = {
    "equals":       lambda df, col, val: df[col] == val,
    "not_equals":   lambda df, col, val: df[col] != val,
    "greater_than": lambda df, col, val: df[col] > val,
    "less_than":    lambda df, col, val: df[col] < val,
    "contains":     lambda df, col, val: df[col].astype(str).str.contains(str(val), case=False, na=False),
    "is_null":      lambda df, col, val: df[col].isna(),
    "is_not_null":  lambda df, col, val: df[col].notna(),
}


def read_file(file_path: str) -> pd.DataFrame:
    ext = os.path.splitext(file_path)[1].lower()
    readers = {".csv": pd.read_csv, ".xlsx": pd.read_excel, ".xls": pd.read_excel, ".json": pd.read_json}
    if ext not in readers:
        raise ValueError(f"Unsupported file type: {ext}. Use CSV, Excel, or JSON.")
    return readers[ext](file_path)


def _detect_null_intent(prompt: str) -> str | None:
    prompt_lower = prompt.lower()
    for intent, keywords in NULL_KEYWORDS.items():
        if any(kw in prompt_lower for kw in keywords):
            return intent
    return None


def _extract_json(text: str) -> dict:
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"logic": "AND", "filters": []}


def prompt_to_filters(user_prompt: str, columns: list, sample_data: list = None) -> dict:
    null_intent = _detect_null_intent(user_prompt)

    parts = [f"Available columns: {columns}"]
    if null_intent:
        parts.append(f"Detected null intent: {null_intent}")
    if sample_data:
        parts.append(f"Sample data:\n{json.dumps(sample_data[:10], indent=2)}")
    parts.append(f"User request: {user_prompt}")

    # Only change: OpenAI Responses API
    response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": "\n".join(parts)},
        ],
        store=False,
    )

    result = _extract_json(response.output_text.strip())

    if null_intent:
        for f in result.get("filters", []):
            if f.get("type") in ("is_null", "is_not_null"):
                f["type"] = null_intent

    return result


def apply_filters(df: pd.DataFrame, ai_json: dict) -> pd.DataFrame:
    filters = ai_json.get("filters", [])
    if not filters:
        return df

    logic = ai_json.get("logic", "AND").upper()
    mask = None

    for f in filters:
        col, op, val = f.get("column"), f.get("type"), f.get("value")
        if col not in df.columns or op not in FILTER_OPS:
            continue

        if op in ("greater_than", "less_than", "equals", "not_equals"):
            col_dtype = df[col].dtype
            try:
                if pd.api.types.is_integer_dtype(col_dtype):
                    val = int(val)
                elif pd.api.types.is_float_dtype(col_dtype):
                    val = float(val)
                elif pd.api.types.is_bool_dtype(col_dtype):
                    val = str(val).strip().lower() == "true"
            except (ValueError, TypeError):
                pass

        condition = FILTER_OPS[op](df, col, val)
        mask = condition if mask is None else (mask & condition if logic == "AND" else mask | condition)

    return df[mask] if mask is not None else df


def apply_column_selection(df: pd.DataFrame, ai_json: dict) -> pd.DataFrame:
    if cols := [c for c in ai_json.get("columns", []) if c in df.columns]:
        return df[cols]

    if cp := ai_json.get("column_pattern"):
        val = str(cp.get("value") or "").lower()
        if not val:
            return df
        if cp.get("type") == "starts_with":
            return df[[c for c in df.columns if c.lower().startswith(val)]]
        if cp.get("type") == "contains":
            return df[[c for c in df.columns if val in c.lower()]]

    return df


def analyze_file(file_path: str, user_prompt: str) -> pd.DataFrame:
    df = read_file(file_path)
    ai_json = prompt_to_filters(user_prompt, list(df.columns), df.head(10).to_dict(orient="records"))
    df = apply_filters(df, ai_json)
    df = apply_column_selection(df, ai_json)
    return df