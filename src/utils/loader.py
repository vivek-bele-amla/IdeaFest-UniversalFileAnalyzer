import pandas as pd
import json
import xml.etree.ElementTree as ET

def load_file(file):
    ext = file.name.split(".")[-1].lower()
    try:
        if ext in ["xlsx", "xls"]:
            return pd.read_excel(file)
        elif ext == "csv":
            return pd.read_csv(file)
        elif ext == "json":
            return load_json(file)
        elif ext == "xml":
            return load_xml(file)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    except Exception as e:
        print("Error loading file:", e)
        return None

def load_json(file):
    content = file.read().decode("utf-8").strip()
    file.seek(0)
    records = []
    try:
        data = json.loads(content)
        if isinstance(data, list):
            records.extend(data)
        elif isinstance(data, dict):
            records.append(data)
    except json.JSONDecodeError:
        # line-delimited JSON
        for line in content.splitlines():
            try:
                records.append(json.loads(line))
            except:
                continue
    if not records:
        raise ValueError("JSON file is empty or invalid")
    return pd.json_normalize(records)

def load_xml(file):
    tree = ET.parse(file)
    root = tree.getroot()
    records = []
    for child in root:
        record = {elem.tag: elem.text for elem in child}
        records.append(record)
    if not records:
        raise ValueError("XML file is empty or invalid")
    return pd.DataFrame(records)