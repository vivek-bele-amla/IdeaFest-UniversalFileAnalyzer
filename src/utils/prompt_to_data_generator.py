from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found")

client = OpenAI(api_key=api_key)


def build_prompt(user_input: str) -> str:
    """
    Build a clean prompt to ensure AI returns only the data requested.
    """
    return f"""
Generate exactly the content requested below. Do NOT include explanations, notes, or extra text.

{user_input}

Rules:
- Return ONLY the requested data
- Do NOT add "Here is..." or any commentary
- If JSON, CSV, Markdown, or text is requested, return only that format
"""


def generate_sample_data(user_input: str) -> str:
    """
    Generate AI output for any kind of content: JSON, text, CSV, Markdown, etc.
    """
    try:
        prompt = build_prompt(user_input)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0
        )

        content = response.choices[0].message.content

        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            content = "\n".join(lines)

        return content
    except Exception as e:
        return f"Failed: {e}"