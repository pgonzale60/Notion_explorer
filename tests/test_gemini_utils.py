import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the google.genai module before importing
sys.modules['google'] = MagicMock()
sys.modules['google.genai'] = MagicMock()
sys.modules['google.genai.errors'] = MagicMock()
sys.modules['google.genai.errors'].ClientError = Exception

# Now import the modules
from cli.gemini_utils import parse_retry_delay


class TestGeminiUtils(unittest.TestCase):
    
    @patch('os.path.join')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, 
           read_data='{"instructions": "Test instructions", "questions": ["Q1", "Q2"], "version": "v1"}')
    @patch('cli.gemini_utils.load_dotenv')
    def test_load_questions(self, mock_load_dotenv, mock_open, mock_join):
        # Import the function inside the test to avoid module import issues
        with patch.dict('sys.modules', {'google': MagicMock(), 'google.genai': MagicMock()}):
            from cli.gemini_utils import load_questions
            
        mock_join.return_value = "/mock/path/questions_v1.json"
        
        instructions, questions, version = load_questions("1")
        
        self.assertEqual(instructions, "Test instructions")
        self.assertEqual(questions, ["Q1", "Q2"])
        self.assertEqual(version, "v1")
        mock_open.assert_called_once()

    @patch('cli.gemini_utils.load_dotenv')
    def test_build_prompt(self, mock_load_dotenv):
        # Import the function inside the test
        with patch.dict('sys.modules', {'google': MagicMock(), 'google.genai': MagicMock()}):
            from cli.gemini_utils import build_prompt
            
        note_content = "This is a test note"
        instructions = "Follow these instructions"
        questions = ["First question?", "Second question?"]
        
        prompt = build_prompt(note_content, instructions, questions)
        
        self.assertIn("Follow these instructions", prompt)
        self.assertIn("1. First question?", prompt)
        self.assertIn("2. Second question?", prompt)
        self.assertIn("This is a test note", prompt)
        self.assertIn("```json", prompt)

    def test_parse_retry_delay(self):
        self.assertEqual(parse_retry_delay("5s"), 5.0)
        self.assertEqual(parse_retry_delay("2.5s"), 2.5)
        self.assertEqual(parse_retry_delay(10), 10.0)
        self.assertEqual(parse_retry_delay(None), 10.0)  # Default
        self.assertEqual(parse_retry_delay("invalid"), 10.0)  # Default for invalid

    @patch('cli.gemini_utils.load_dotenv')
    @patch('cli.gemini_utils.client')
    @patch('cli.gemini_utils.load_questions')
    @patch('cli.gemini_utils.datetime')
    def test_call_gemini_api_success(self, mock_datetime, mock_load_questions, mock_client, mock_load_dotenv):
        # Import the function inside the test
        with patch.dict('sys.modules', {'google': MagicMock(), 'google.genai': MagicMock(), 'google.genai.errors': MagicMock()}):
            from cli.gemini_utils import call_gemini_api
            
        # Setup mock responses
        mock_load_questions.return_value = ("Test instructions", ["Q1", "Q2"], "v1")
        
        mock_response = MagicMock()
        mock_response.text = '```json\n{"q1": "Answer 1", "q2": "Answer 2"}\n```'
        mock_client.models.generate_content.return_value = mock_response
        
        # Mock datetime
        mock_now = MagicMock()
        mock_now.isoformat.return_value = "2023-01-07T00:00:00Z"
        mock_datetime.now.return_value = mock_now
        
        # Call the function
        result = call_gemini_api("Test note content")
        
        # Verify results
        self.assertEqual(result["q1"], "Answer 1")
        self.assertEqual(result["q2"], "Answer 2")
        self.assertEqual(result["questions_version"], "v1")
        self.assertEqual(result["model"], "gemini-2.0-flash")
        self.assertEqual(result["date_executed"], "2023-01-07T00:00:00Z")
        
        # Verify mock was called correctly
        mock_client.models.generate_content.assert_called_once()

    @patch('cli.gemini_utils.load_dotenv')
    @patch('cli.gemini_utils.client')
    @patch('cli.gemini_utils.load_questions')
    @patch('cli.gemini_utils.datetime')
    def test_call_gemini_api_quota_exceeded(self, mock_datetime, mock_load_questions, mock_client, mock_load_dotenv):
        # Import the function inside the test
        with patch.dict('sys.modules', {'google': MagicMock(), 'google.genai': MagicMock(), 'google.genai.errors': MagicMock()}):
            from cli.gemini_utils import call_gemini_api
            
        # Setup mocks
        mock_load_questions.return_value = ("Test instructions", ["Q1", "Q2"], "v1")
        
        # Mock datetime
        mock_now = MagicMock()
        mock_now.isoformat.return_value = "2023-01-07T00:00:00Z"
        mock_datetime.now.return_value = mock_now
        
        # Create a ClientError with quota exceeded
        error = Exception("429 RESOURCE_EXHAUSTED")
        error.response_json = {
            "error": {
                "details": [
                    {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "30s"}
                ]
            }
        }
        mock_client.models.generate_content.side_effect = error
        
        # Call the function
        result = call_gemini_api("Test note content")
        
        # Verify results
        self.assertIn("error", result)
        self.assertIn("API quota exceeded", result["error"])
        self.assertEqual(result["questions_version"], "v1")
        self.assertEqual(result["model"], "gemini-2.0-flash")
        self.assertEqual(result["date_executed"], "2023-01-07T00:00:00Z")

    @patch('cli.gemini_utils.load_dotenv')
    @patch('cli.gemini_utils.client')
    @patch('cli.gemini_utils.load_questions')
    @patch('cli.gemini_utils.datetime')
    def test_call_gemini_api_invalid_response(self, mock_datetime, mock_load_questions, mock_client, mock_load_dotenv):
        # Import the function inside the test
        with patch.dict('sys.modules', {'google': MagicMock(), 'google.genai': MagicMock(), 'google.genai.errors': MagicMock()}):
            from cli.gemini_utils import call_gemini_api
            
        # Setup mocks
        mock_load_questions.return_value = ("Test instructions", ["Q1", "Q2"], "v1")
        
        # Mock datetime
        mock_now = MagicMock()
        mock_now.isoformat.return_value = "2023-01-07T00:00:00Z"
        mock_datetime.now.return_value = mock_now
        
        mock_response = MagicMock()
        mock_response.text = 'Not valid JSON'
        mock_client.models.generate_content.return_value = mock_response
        
        # Call the function
        result = call_gemini_api("Test note content")
        
        # Verify results
        self.assertIn("error", result)
        self.assertIn("Failed to parse Gemini response", result["error"])
        self.assertEqual(result["raw"], "Not valid JSON")
        self.assertEqual(result["questions_version"], "v1")
        self.assertEqual(result["model"], "gemini-2.0-flash")
        self.assertEqual(result["date_executed"], "2023-01-07T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
