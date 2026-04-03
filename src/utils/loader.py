import pandas as pd
import json
import io
import xml.etree.ElementTree as ET


def load_file(file) -> pd.DataFrame:
    name = file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(file)
    elif name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file)
    elif name.endswith(".json"):
        return _parse_json(file.read().decode("utf-8"))
    elif name.endswith(".xml"):
        return _parse_xml(file.read().decode("utf-8"))
    else:
        raise ValueError(f"Unsupported file type: {name}")

def _parse_json(text: str) -> pd.DataFrame:
    text = text.strip()
    try:
        # Standard JSON array or object
        data = json.loads(text)
        if isinstance(data, dict):
            data = [data]
        return pd.DataFrame(data)
    except json.JSONDecodeError:
        # Fallback: newline-delimited JSON (NDJSON)
        lines = [json.loads(line) for line in text.splitlines() if line.strip()]
        return pd.DataFrame(lines)


def load_text(text: str) -> pd.DataFrame:
    """Auto-detect and parse pasted JSON, CSV, or XML text."""
    text = text.strip()

    if text.startswith("{") or text.startswith("["):
        data = json.loads(text)
        if isinstance(data, dict):
            data = [data]
        return pd.DataFrame(data)

    if text.startswith("<"):
        return _parse_xml(text)

    return pd.read_csv(io.StringIO(text))


def _parse_xml(text: str) -> pd.DataFrame:
    root = ET.fromstring(text)
    rows = []
    for child in root:
        rows.append({sub.tag: sub.text for sub in child})
    if not rows:
        rows = [{sub.tag: sub.text for sub in root}]
    return pd.DataFrame(rows)