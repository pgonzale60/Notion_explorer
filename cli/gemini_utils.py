import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
from datetime import datetime
import time
import re
from google.genai.errors import ClientError
from pydantic import BaseModel, Field
from typing import List, Optional

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

# Directory containing the questions JSON files
QUESTIONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'questions'))

MODEL_NAME = "gemini-2.0-flash"

# Pydantic models for schema validation
class Answer(BaseModel):
    answer: str = Field(description="The concise insight or response to the question")
    sources: List[str] = Field(description="List of note_id(s) where the answer was found")

def load_questions(version=None):
    """
    Load questions from the specified version JSON file.
    Auto-detects latest version if None is provided.
    """
    # Determine questions file
    if version is None:
        # Try to auto-detect latest version
        files = os.listdir(QUESTIONS_DIR)
        versions = []
        for fname in files:
            m = re.match(r'questions_v(\d+)\.json', fname)
            if m:
                versions.append(int(m.group(1)))
        if versions:
            version = str(max(versions))
        else:
            version = "1"  # default
    
    questions_file = os.path.join(QUESTIONS_DIR, f"questions_v{version}.json")
    with open(questions_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    instructions = data["instructions"]
    context_question = data.get("context_question")
    questions = data["questions"]
    questions_version = data.get("version", f"v{version}")
    return instructions, context_question, questions, questions_version

def build_pydantic_schema(context_question, questions):
    """
    Dynamically build a Pydantic model class based on the context and questions.
    """
    # Define field attributes for context and each question
    field_definitions = {}
    # Single context summary (no sources)
    if context_question:
        field_definitions["context"] = (str, Field(description=context_question))
    # Other questions (with sources)
    for i, question in enumerate(questions):
        field_name = f"q{i+1}"
        field_desc = question
        field_definitions[field_name] = (List[Answer], Field(description=field_desc))
        
    # Create a new model class dynamically
    AnalysisResponseSchema = type(
        "AnalysisResponse", 
        (BaseModel,), 
        {
            "__annotations__": {k: v[0] for k, v in field_definitions.items()},
            "__fields__": {k: v[1] for k, v in field_definitions.items()}
        }
    )
    
    return AnalysisResponseSchema

def build_prompt(note_content, instructions, context_question, questions):
    """Build the prompt for the Gemini model."""
    # Start with instructions
    prompt = instructions + "\n\n"
    # Add context question
    if context_question:
        prompt += "Context Question:\n" + f"1. {context_question}" + "\n\n"
    # Add other questions
    prompt += "Questions:\n" + "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)]) + "\n\n"
    # Add the notes
    prompt += "Input notes:\n" + note_content
    return prompt

# Helper to parse retryDelay like '7s' or '2.5s'
def parse_retry_delay(retry_delay_str):
    if not retry_delay_str:
        return 10.0  # Default fallback
    
    try:
        # Handle format like '14s'
        if isinstance(retry_delay_str, str) and 's' in retry_delay_str:
            return float(retry_delay_str.replace('s', ''))
        # Handle numeric values
        return float(retry_delay_str)
    except (ValueError, TypeError):
        return 10.0  # Default fallback

def call_gemini_api(note_content, questions_version="1", max_attempts=10):
    """
    Call the Gemini API with note content and questions.
    Uses a Pydantic schema to ensure structured responses.
    """
    # Load questions and create schema (including context)
    instructions, context_question, questions, version_str = load_questions(questions_version)
    prompt = build_prompt(note_content, instructions, context_question, questions)
    
    # Generate the schema dynamically based on the context and questions
    AnalysisResponseSchema = build_pydantic_schema(context_question, questions)
    
    # Configure generation parameters with increased token limit
    # Prepare config as a dict to include response_schema per Gemini API docs
    generation_config = {
        'response_mime_type': 'application/json',
        'response_schema': AnalysisResponseSchema, 
        'max_output_tokens': 8192,
        'temperature': 0.0,
        'top_p': 0.95,
        'top_k': 40
    }

    try:
        # Call the API with the schema in config
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=generation_config
        )
    except ClientError as e:
        error_message = str(e)
        print(f"Gemini API error: {error_message}")
        
        # Check if this is a quota/rate limit error
        if "429" in error_message and "RESOURCE_EXHAUSTED" in error_message:
            # Extract the retry delay suggestion if available
            retry_delay = "unknown"
            if hasattr(e, 'response_json') and e.response_json:
                details = e.response_json.get('error', {}).get('details', [])
                for detail in details:
                    if '@type' in detail and 'RetryInfo' in detail['@type']:
                        retry_delay = detail.get('retryDelay', 'unknown')
            
            # Create a structured error response
            return {
                "error": "API quota exceeded",
                "message": f"Gemini API quota exceeded. Suggested retry delay: {retry_delay}",
                "status_code": 429,
                "questions_version": version_str,
                "model": MODEL_NAME,
                "date_executed": datetime.now().isoformat()
            }
        
        # For other errors, return a structured error response
        return {
            "error": "API error",
            "message": error_message,
            "questions_version": version_str,
            "model": MODEL_NAME,
            "date_executed": datetime.now().isoformat()
        }
    
    # Process successful response
    try:
        # Access the parsed Pydantic object directly
        if hasattr(response, 'parsed') and response.parsed is not None:
            validated_data = response.parsed
            # If the parsed data is a list of models, convert each
            if isinstance(validated_data, list):
                result = [item.model_dump() if hasattr(item, 'model_dump') else item for item in validated_data]
            elif hasattr(validated_data, 'model_dump'):
                result = validated_data.model_dump()
            else:
                # Already a plain dict
                result = validated_data
        else:
            # Fallback if .parsed is not available (should not happen with schema)
            print("Warning: Gemini response did not contain a 'parsed' attribute. Attempting to parse text.")
            text = response.text.strip()
            if text.startswith('```json'):
                text = text[len('```json'):].strip()
            if text.endswith('```'):
                text = text[:-3].strip()

            # Attempt to parse and validate the JSON manually
            parsed_json = json.loads(text)
            validated_data = AnalysisResponseSchema.model_validate(parsed_json) 
            result = validated_data.model_dump()

    except Exception as e:
        print(f"Error processing or validating Gemini response: {e}")
        # Include the raw response text if available for debugging
        raw_response = getattr(response, 'text', str(response))
        result = {
            "error": f"Failed to process/validate Gemini response: {e}",
            "raw_response": raw_response,
            "questions_version": version_str,
            "model": MODEL_NAME,
            "date_executed": datetime.now().isoformat()
            }

    # Always include version info, model, and execution date in output
    if isinstance(result, dict):  # Ensure result is a dict before adding metadata
        result["questions_version"] = version_str
        result["model"] = MODEL_NAME
        result["date_executed"] = datetime.now().isoformat()
    
    return result
