import unittest
import pytest
from unittest.mock import patch, MagicMock
import os
import sys
import json
from fastapi.testclient import TestClient

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from gui_backend import app


class TestGUIBackend(unittest.TestCase):
    
    def setUp(self):
        self.client = TestClient(app)
    
    @patch('gui_backend.sqlite3.connect')
    def test_get_notes(self, mock_connect):
        # Mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock query results
        mock_cursor.fetchall.return_value = [
            ('note1', 'parent1', '2023-01-01', '2023-01-02', 'Test content 1'),
            ('note2', 'parent2', '2023-01-03', '2023-01-04', 'Test content 2')
        ]
        
        # Call the endpoint
        response = self.client.get('/notes')
        
        # Check the response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['id'], 'note1')
        self.assertEqual(data[0]['parent_id'], 'parent1')
        self.assertEqual(data[1]['id'], 'note2')
        self.assertEqual(data[1]['content'], 'Test content 2')
        
        # Verify the mock was called correctly
        mock_cursor.execute.assert_called_once_with(
            "SELECT id, parent_id, created_time, last_edited_time, content FROM pages"
        )
    
    @patch('gui_backend.sqlite3.connect')
    def test_get_note(self, mock_connect):
        # Mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock query results - found
        mock_cursor.fetchone.return_value = ('note1', 'parent1', '2023-01-01', '2023-01-02', 'Test content')
        
        # Call the endpoint
        response = self.client.get('/note/note1')
        
        # Check the response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['id'], 'note1')
        self.assertEqual(data['parent_id'], 'parent1')
        self.assertEqual(data['content'], 'Test content')
        
        # Verify the mock was called correctly
        mock_cursor.execute.assert_called_once_with(
            "SELECT id, parent_id, created_time, last_edited_time, content FROM pages WHERE id=?", 
            ('note1',)
        )
        
        # Test not found case
        mock_cursor.fetchone.return_value = None
        
        response = self.client.get('/note/nonexistent')
        
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], 'Note not found')
    
    @patch('gui_backend.sqlite3.connect')
    def test_get_answers(self, mock_connect):
        # Mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock query results
        answers_json = json.dumps({
            "q1": "Test answer 1",
            "q2": "Test answer 2",
            "questions_version": "1",
            "model": "gemini-2.0-flash",
            "date_executed": "2023-01-07T00:00:00Z"
        })
        mock_cursor.fetchall.return_value = [
            ('note1', '1', 'gemini-2.0-flash', '2023-01-07T00:00:00Z', answers_json)
        ]
        
        # Call the endpoint
        response = self.client.get('/answers/note1')
        
        # Check the response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['note_id'], 'note1')
        self.assertEqual(data[0]['questions_version'], '1')
        self.assertEqual(data[0]['model'], 'gemini-2.0-flash')
        self.assertEqual(data[0]['answers_json']['q1'], 'Test answer 1')
        
        # Verify the mock was called correctly
        mock_cursor.execute.assert_called_once_with(
            "SELECT note_id, questions_version, model, date_executed, answers_json FROM gemini_analysis WHERE note_id=?", 
            ('note1',)
        )
    
    @patch('gui_backend.sqlite3.connect')
    def test_get_answers_index(self, mock_connect):
        # Mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock query results
        mock_cursor.fetchall.return_value = [('note1',), ('note2',), ('note3',)]
        
        # Call the endpoint
        response = self.client.get('/answers_index')
        
        # Check the response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, ['note1', 'note2', 'note3'])
        
        # Verify the mock was called correctly
        mock_cursor.execute.assert_called_once_with(
            "SELECT DISTINCT note_id FROM gemini_analysis"
        )
    
    @patch('gui_backend.sqlite3.connect')
    def test_get_note_versions_index(self, mock_connect):
        # Mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock query results
        mock_cursor.fetchall.return_value = [
            ('note1', '1'),
            ('note1', '2'),
            ('note2', '1')
        ]
        
        # Call the endpoint
        response = self.client.get('/note_versions_index')
        
        # Check the response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['note1'], ['1', '2'])
        self.assertEqual(data['note2'], ['1'])
        
        # Verify the mock was called correctly
        mock_cursor.execute.assert_called_once_with(
            "SELECT note_id, questions_version FROM gemini_analysis"
        )
    
    @patch('gui_backend.sqlite3.connect')
    def test_get_hierarchy(self, mock_connect):
        # Mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock query results (id, parent_id)
        mock_cursor.fetchall.return_value = [
            ('child1', 'parent1'),
            ('child2', 'parent1'),
            ('child3', 'parent2')
        ]
        
        # Call the endpoint
        response = self.client.get('/hierarchy')
        
        # Check the response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['parent1'], ['child1', 'child2'])
        self.assertEqual(data['parent2'], ['child3'])
        
        # Verify the mock was called correctly
        mock_cursor.execute.assert_called_once_with(
            "SELECT id, parent_id FROM pages"
        )
    
    @patch('gui_backend.sqlite3.connect')
    def test_get_question_versions(self, mock_connect):
        # Mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock query results
        mock_cursor.fetchall.return_value = [
            ('2', '2023-01-02'),
            ('1', '2023-01-01')
        ]
        
        # Call the endpoint
        response = self.client.get('/question_versions')
        
        # Check the response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['version'], '2')
        self.assertEqual(data[0]['date_updated'], '2023-01-02')
        self.assertEqual(data[1]['version'], '1')
        
        # Verify the mock was called correctly
        mock_cursor.execute.assert_called_once_with(
            "SELECT version, date_updated FROM questions ORDER BY version DESC"
        )
    
    @patch('gui_backend.sqlite3.connect')
    def test_get_questions_by_version(self, mock_connect):
        # Mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock query results
        questions_json = json.dumps({
            "instructions": "Test instructions",
            "questions": ["Q1", "Q2", "Q3"]
        })
        mock_cursor.fetchone.return_value = ('1', '2023-01-01', questions_json)
        
        # Call the endpoint
        response = self.client.get('/questions/1')
        
        # Check the response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['version'], '1')
        self.assertEqual(data['date_updated'], '2023-01-01')
        self.assertEqual(data['instructions'], 'Test instructions')
        self.assertEqual(data['questions'], ["Q1", "Q2", "Q3"])
        
        # Verify the mock was called correctly
        mock_cursor.execute.assert_called_once_with(
            "SELECT version, date_updated, questions_json FROM questions WHERE version=?", 
            ('1',)
        )
        
        # Test not found case
        mock_cursor.fetchone.return_value = None
        
        response = self.client.get('/questions/nonexistent')
        
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], 'Question version nonexistent not found')
    
    @patch('gui_backend.sqlite3.connect')
    def test_get_latest_question_version(self, mock_connect):
        # Mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock query results - found
        mock_cursor.fetchone.return_value = ('2',)
        
        # Call the endpoint
        response = self.client.get('/latest_question_version')
        
        # Check the response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['version'], '2')
        
        # Verify the mock was called correctly
        mock_cursor.execute.assert_called_once_with(
            "SELECT version FROM questions ORDER BY version DESC LIMIT 1"
        )
        
        # Test not found case
        mock_cursor.fetchone.return_value = None
        
        response = self.client.get('/latest_question_version')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['version'], None)


if __name__ == "__main__":
    unittest.main()
