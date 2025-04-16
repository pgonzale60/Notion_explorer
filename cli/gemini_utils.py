import os
import json
from google import genai
from dotenv import load_dotenv
from datetime import datetime
import time
from google.genai.errors import ClientError

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

# Directory containing the questions JSON files
QUESTIONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'questions'))

MODEL_NAME = "gemini-2.0-flash"

def load_questions(version=None):
    # Determine questions file
    if version is None:
        version = "1"  # default
    questions_file = os.path.join(QUESTIONS_DIR, f"questions_v{version}.json")
    with open(questions_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    instructions = data["instructions"]
    questions = data["questions"]
    questions_version = data.get("version", f"v{version}")
    return instructions, questions, questions_version

def build_prompt(note_content, instructions, questions):
    numbered = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
    prompt = f"""
{instructions}

Questions:\n{numbered}\n\nInput note:\n{note_content}\n\nOutput format:\n```json\n{{\n  \"q1\": \"Answer to question 1\",\n  ...\n  \"q12\": \"Answer to question 12\"\n}}\n```
"""
    return prompt

# Helper to parse retryDelay like '7s' or '2.5s'
def parse_retry_delay(retry_delay_str):
    if retry_delay_str.endswith('s'):
        return float(retry_delay_str[:-1])
    return 1.0

def call_gemini_api(note_content, questions_version="1", max_attempts=10):
    instructions, questions, version_str = load_questions(questions_version)
    prompt = build_prompt(note_content, instructions, questions)
    attempt = 0
    while True:
        attempt += 1
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )
            break  # Success
        except ClientError as e:
            if hasattr(e, 'response_json') and e.response_json:
                err = e.response_json.get('error', {})
                if err.get('code') == 429:
                    # Try to get retryDelay from details
                    retry_delay = 10  # fallback
                    for detail in err.get('details', []):
                        if detail.get('@type', '').endswith('RetryInfo'):
                            retry_delay_str = detail.get('retryDelay', '7s')
                            retry_delay = parse_retry_delay(retry_delay_str)
                    print(f"[Gemini] Rate limited (429). Retrying after {retry_delay} seconds (attempt {attempt})...")
                    time.sleep(retry_delay)
                    if attempt >= max_attempts:
                        raise RuntimeError(f"Max retry attempts ({max_attempts}) reached for Gemini API.")
                    continue
            raise  # Not a rate limit error, re-raise
    try:
        text = response.text.strip()
        if text.startswith('```json'):
            text = text[len('```json'):].strip()
        if text.endswith('```'):
            text = text[:-3].strip()
        result = json.loads(text)
    except Exception as e:
        result = {"error": f"Failed to parse Gemini response: {e}", "raw": response.text}
    # Always include version info, model, and execution date in output
    result["questions_version"] = version_str
    result["model"] = MODEL_NAME
    result["date_executed"] = datetime.now().isoformat()
    return result
