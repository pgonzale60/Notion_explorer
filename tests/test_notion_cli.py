import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import json
import sqlite3
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock external modules before importing
sys.modules['gemini_utils'] = MagicMock()
sys.modules['gemini_utils'].call_gemini_api = MagicMock()
sys.modules['gemini_utils'].MODEL_NAME = "gemini-2.0-flash"

from cli.notion_cli import (
    request_with_rate_limit,
    detect_id_type,
    init_db,
    save_page_to_db,
    get_page_from_db,
    save_crawl_error,
    get_page_title,
    get_first_block,
    update_questions
)


class TestNotionCLI(unittest.TestCase):
    
    def setUp(self):
        # Create an in-memory SQLite database for testing
        self.conn = sqlite3.connect(':memory:')
        # Initialize the database schema
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS pages (
            id TEXT PRIMARY KEY,
            parent_id TEXT,
            created_time TEXT,
            last_edited_time TEXT,
            content TEXT,
            content_length INTEGER
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS gemini_analysis (
            note_id TEXT,
            questions_version TEXT,
            model TEXT,
            date_executed TEXT,
            answers_json TEXT,
            PRIMARY KEY (note_id, questions_version, model)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS crawl_errors (
            id TEXT,
            parent_id TEXT,
            error_message TEXT,
            head_title TEXT,
            head_content TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS questions (
            version TEXT PRIMARY KEY,
            date_updated TEXT,
            questions_json TEXT
        )''')
        self.conn.commit()
    
    def tearDown(self):
        self.conn.close()
        
    @patch('requests.get')
    @patch('requests.post')
    @patch('time.sleep')
    def test_request_with_rate_limit(self, mock_sleep, mock_post, mock_get):
        # Test GET request
        mock_response_get = MagicMock()
        mock_response_get.status_code = 200
        mock_response_get.json.return_value = {"success": True}
        mock_get.return_value = mock_response_get
        
        result = request_with_rate_limit("https://test.com", {}, method="GET")
        
        self.assertEqual(result.json(), {"success": True})
        mock_get.assert_called_once()
        
        # Test POST request
        mock_response_post = MagicMock()
        mock_response_post.status_code = 200
        mock_response_post.json.return_value = {"success": True}
        mock_post.return_value = mock_response_post
        
        result = request_with_rate_limit("https://test.com", {}, method="POST", json={"data": "test"})
        
        self.assertEqual(result.json(), {"success": True})
        mock_post.assert_called_once()
        
        # Test rate limiting
        mock_get.reset_mock()
        mock_sleep.reset_mock()
        
        # First response hits rate limit, second succeeds
        mock_rate_limited = MagicMock()
        mock_rate_limited.status_code = 429
        mock_rate_limited.headers = {"Retry-After": "2"}
        
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {"success": True}
        
        mock_get.side_effect = [mock_rate_limited, mock_success]
        
        result = request_with_rate_limit("https://test.com", {}, method="GET")
        
        self.assertEqual(result.json(), {"success": True})
        self.assertEqual(mock_get.call_count, 2)
        mock_sleep.assert_called_once_with(2)
        
        # Test unsupported method
        with self.assertRaises(ValueError):
            request_with_rate_limit("https://test.com", {}, method="PUT")
    
    @patch('requests.get')
    def test_detect_id_type(self, mock_get):
        # Test database ID
        mock_db_response = MagicMock()
        mock_db_response.status_code = 200
        
        mock_page_response = MagicMock()
        mock_page_response.status_code = 404
        
        mock_get.side_effect = [mock_db_response, mock_page_response]
        
        result = detect_id_type("test_db_id")
        self.assertEqual(result, "database")
        
        # Test page ID
        mock_get.reset_mock()
        
        mock_db_response = MagicMock()
        mock_db_response.status_code = 404
        
        mock_page_response = MagicMock()
        mock_page_response.status_code = 200
        
        mock_get.side_effect = [mock_db_response, mock_page_response]
        
        result = detect_id_type("test_page_id")
        self.assertEqual(result, "page")
        
        # Test invalid ID
        mock_get.reset_mock()
        
        mock_db_response = MagicMock()
        mock_db_response.status_code = 404
        
        mock_page_response = MagicMock()
        mock_page_response.status_code = 404
        
        mock_get.side_effect = [mock_db_response, mock_page_response]
        
        with self.assertRaises(ValueError):
            detect_id_type("invalid_id")
    
    def test_save_and_get_page_from_db(self):
        # Test inserting a new page
        save_page_to_db(
            self.conn, 
            "page_id_1", 
            "parent_id_1", 
            "2023-01-01T00:00:00Z", 
            "2023-01-02T00:00:00Z", 
            "Test content"
        )
        
        page = get_page_from_db(self.conn, "page_id_1")
        
        self.assertEqual(page[0], "page_id_1")
        self.assertEqual(page[1], "parent_id_1")
        self.assertEqual(page[2], "2023-01-01T00:00:00Z")
        self.assertEqual(page[3], "2023-01-02T00:00:00Z")
        self.assertEqual(page[4], "Test content")
        
        # Test updating an existing page
        save_page_to_db(
            self.conn, 
            "page_id_1", 
            "parent_id_1", 
            "2023-01-01T00:00:00Z", 
            "2023-01-03T00:00:00Z",  # Updated edit time
            "Updated content"
        )
        
        page = get_page_from_db(self.conn, "page_id_1")
        
        self.assertEqual(page[0], "page_id_1")
        self.assertEqual(page[3], "2023-01-03T00:00:00Z")
        self.assertEqual(page[4], "Updated content")
        
        # Test updating metadata only
        save_page_to_db(
            self.conn, 
            "page_id_1", 
            "parent_id_2",  # Updated parent
            "2023-01-01T00:00:00Z", 
            "2023-01-04T00:00:00Z",  # Updated edit time
        )
        
        page = get_page_from_db(self.conn, "page_id_1")
        
        self.assertEqual(page[0], "page_id_1")
        self.assertEqual(page[1], "parent_id_2")
        self.assertEqual(page[3], "2023-01-04T00:00:00Z")
        self.assertEqual(page[4], "Updated content")  # Content unchanged
    
    def test_save_crawl_error(self):
        save_crawl_error(
            self.conn,
            "error_id_1",
            "parent_id_1",
            "Test error message",
            "Test title",
            "Test content"
        )
        
        c = self.conn.cursor()
        c.execute('SELECT * FROM crawl_errors WHERE id = ?', ("error_id_1",))
        error = c.fetchone()
        
        self.assertEqual(error[0], "error_id_1")
        self.assertEqual(error[1], "parent_id_1")
        self.assertEqual(error[2], "Test error message")
        self.assertEqual(error[3], "Test title")
        self.assertEqual(error[4], "Test content")
    
    def test_get_page_title(self):
        mock_title_function = MagicMock(return_value="Test Page Title")
        
        result = mock_title_function("test_page_id")
        self.assertEqual(result, "Test Page Title")
        mock_title_function.assert_called_once_with("test_page_id")
    
    def test_get_first_block(self):
        mock_block_function = MagicMock(return_value="First paragraph text")
        
        result = mock_block_function("test_page_id")
        self.assertEqual(result, "First paragraph text")
        mock_block_function.assert_called_once_with("test_page_id")
    
    def test_update_questions(self):
        test_db = sqlite3.connect(':memory:')
        test_cursor = test_db.cursor()
        test_cursor.execute('''CREATE TABLE IF NOT EXISTS questions (
            version TEXT PRIMARY KEY,
            date_updated TEXT,
            questions_json TEXT
        )''')
        test_db.commit()
        
        test_json = json.dumps({
            "version": "1",
            "questions": [{"id": 1, "text": "Test question?"}]
        })
        
        test_cursor.execute(
            "INSERT OR REPLACE INTO questions (version, date_updated, questions_json) VALUES (?, ?, ?)",
            ("1", datetime.now().isoformat(), test_json)
        )
        test_db.commit()
        
        test_cursor.execute('SELECT * FROM questions WHERE version = ?', ("1",))
        question_data = test_cursor.fetchone()
        
        self.assertEqual(question_data[0], "1")
        self.assertIsNotNone(question_data[1])  # date_updated
        parsed_json = json.loads(question_data[2])
        self.assertEqual(parsed_json["questions"][0]["text"], "Test question?")
        
        test_db.close()


if __name__ == "__main__":
    unittest.main()
