import pytest
import os
import sys
import tempfile
import shutil
import sqlite3

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def test_db_conn():
    """Create an in-memory SQLite database with the correct schema for testing"""
    conn = sqlite3.connect(':memory:')
    c = conn.cursor()
    
    # Create pages table
    c.execute('''CREATE TABLE IF NOT EXISTS pages (
        id TEXT PRIMARY KEY,
        parent_id TEXT,
        created_time TEXT,
        last_edited_time TEXT,
        content TEXT,
        content_length INTEGER
    )''')
    
    # Create gemini_analysis table
    c.execute('''CREATE TABLE IF NOT EXISTS gemini_analysis (
        note_id TEXT,
        questions_version TEXT,
        model TEXT,
        date_executed TEXT,
        answers_json TEXT,
        PRIMARY KEY (note_id, questions_version, model)
    )''')
    
    # Create crawl_errors table
    c.execute('''CREATE TABLE IF NOT EXISTS crawl_errors (
        id TEXT,
        parent_id TEXT,
        error_message TEXT,
        head_title TEXT,
        head_content TEXT
    )''')
    
    # Create questions table
    c.execute('''CREATE TABLE IF NOT EXISTS questions (
        version TEXT PRIMARY KEY,
        date_updated TEXT,
        questions_json TEXT
    )''')
    
    conn.commit()
    
    # Insert sample data
    c.execute('''INSERT INTO pages VALUES 
               ('page1', 'parent1', '2023-01-01T00:00:00Z', '2023-01-02T00:00:00Z', 'Test content 1', 13)''')
    c.execute('''INSERT INTO pages VALUES 
               ('page2', 'parent1', '2023-01-03T00:00:00Z', '2023-01-04T00:00:00Z', 'Test content 2', 13)''')
    c.execute('''INSERT INTO pages VALUES 
               ('page3', 'parent2', '2023-01-05T00:00:00Z', '2023-01-06T00:00:00Z', 'Test content 3', 13)''')
    
    # Insert sample questions data
    questions_json = '''{
        "version": "1",
        "questions": [
            {"id": "q1", "text": "What is the main theme?"},
            {"id": "q2", "text": "What are the key insights?"}
        ]
    }'''
    c.execute('''INSERT INTO questions VALUES ('1', '2023-01-01T00:00:00Z', ?)''', (questions_json,))
    
    # Insert sample analysis data
    analysis_json = '''{
        "q1": "The main theme is testing.",
        "q2": "The key insight is that tests help ensure code quality.",
        "questions_version": "1",
        "model": "gemini-2.0-flash",
        "date_executed": "2023-01-07T00:00:00Z"
    }'''
    c.execute('''INSERT INTO gemini_analysis VALUES 
               ('page1', '1', 'gemini-2.0-flash', '2023-01-07T00:00:00Z', ?)''', (analysis_json,))
    
    conn.commit()
    
    yield conn
    
    conn.close()


@pytest.fixture
def temp_file_structure():
    """Create a temporary directory structure for testing file operations"""
    temp_dir = tempfile.mkdtemp()
    
    # Create directory structure
    os.makedirs(os.path.join(temp_dir, 'questions'), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, 'notion_notes'), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, 'answers_to_questions_by_LLM'), exist_ok=True)
    
    # Create sample files
    with open(os.path.join(temp_dir, 'questions', 'questions_v1.json'), 'w') as f:
        f.write('''{
            "version": "1",
            "instructions": "Analyze the following note",
            "questions": [
                "What is the main theme?",
                "What are the key insights?"
            ]
        }''')
    
    with open(os.path.join(temp_dir, 'notion_notes', 'sample_note.md'), 'w') as f:
        f.write('''# Sample Note
        
This is a sample note content for testing.
It contains multiple lines and some basic formatting.

- Bullet point 1
- Bullet point 2
        ''')
    
    yield temp_dir
    
    # Clean up
    shutil.rmtree(temp_dir)
