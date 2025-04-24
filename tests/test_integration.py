import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import json
import tempfile
import shutil

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from notion_explorer import main


class TestNotionExplorerIntegration(unittest.TestCase):
    """Integration tests for the notion_explorer command-line interfaces"""
    
    @patch('sys.argv', ['notion_explorer.py'])  # Using no command instead of 'help'
    @patch('argparse.ArgumentParser.print_help')
    def test_main_no_command(self, mock_print_help):
        """Test that the CLI prints help when no command is provided"""
        # For this test, we just want to make sure main() completes without errors
        # and that print_help is called when no command is provided
        try:
            main()
        except SystemExit:
            # argparse might exit when help is printed, so we catch it
            pass
        
        mock_print_help.assert_called_once()
    
    @patch('sys.argv', ['notion_explorer.py', 'reset_db'])
    @patch('notion_explorer.reset_db')
    def test_reset_db_command(self, mock_reset_db):
        """Test the reset_db command"""
        main()
        mock_reset_db.assert_called_once()
    
    @patch('sys.argv', ['notion_explorer.py', 'analyze_notes', '--questions_version', '2', '--from_date', '01/01/2024'])
    @patch('notion_explorer.analyze_notes')
    def test_analyze_notes_command(self, mock_analyze_notes):
        """Test the analyze_notes command with parameters"""
        main()
        mock_analyze_notes.assert_called_once_with(questions_version='2', from_date='01/01/2024')
    
    @patch('sys.argv', ['notion_explorer.py', 'load_outputs'])
    @patch('notion_explorer.load_gemini_outputs')
    def test_load_outputs_command(self, mock_load_outputs):
        """Test the load_outputs command"""
        main()
        mock_load_outputs.assert_called_once()
    
    @patch('sys.argv', ['notion_explorer.py', 'launch_gui'])
    @patch('notion_explorer.launch_gui')
    def test_launch_gui_command(self, mock_launch_gui):
        """Test the launch_gui command"""
        main()
        mock_launch_gui.assert_called_once()
    
    @patch('sys.argv', ['notion_explorer.py', 'update_questions', '--version', '3', '--force'])
    @patch('notion_explorer.update_questions')
    def test_update_questions_command(self, mock_update_questions):
        """Test the update_questions command with parameters"""
        # Make update_questions return a tuple of (success, message) to match what main() expects
        mock_update_questions.return_value = (True, "Questions updated successfully")
        
        main()
        mock_update_questions.assert_called_once_with(version='3', force_update=True)


class TestFileSystemIntegration(unittest.TestCase):
    """Tests for filesystem operations in the Notion integration"""
    
    def setUp(self):
        """Create a temporary directory structure for testing"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test directory structure
        self.questions_dir = os.path.join(self.temp_dir, 'questions')
        self.exports_dir = os.path.join(self.temp_dir, 'notion_notes')
        self.outputs_dir = os.path.join(self.temp_dir, 'answers_to_questions_by_LLM')
        
        os.makedirs(self.questions_dir, exist_ok=True)
        os.makedirs(self.exports_dir, exist_ok=True)
        os.makedirs(self.outputs_dir, exist_ok=True)
        
        # Create a test questions file
        with open(os.path.join(self.questions_dir, 'questions_v1.json'), 'w') as f:
            json.dump({
                "version": "1",
                "instructions": "Test instructions",
                "questions": ["Test question 1", "Test question 2"]
            }, f)
            
        # Create a test exported note
        with open(os.path.join(self.exports_dir, 'test_note.md'), 'w') as f:
            f.write("# Test Note\n\nThis is test content.")
    
    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)
    
    @patch('cli.gemini_utils.QUESTIONS_DIR')
    def test_load_questions_from_filesystem(self, mock_questions_dir):
        """Test loading questions from the filesystem"""
        # Set the mock to use our temp directory
        mock_questions_dir = self.questions_dir
        
        # Import here to use the patched path
        from cli.gemini_utils import load_questions
        
        with patch('os.path.join', return_value=os.path.join(self.questions_dir, 'questions_v1.json')):
            instructions, questions, version = load_questions("1")
            
            self.assertEqual(version, "1")
            self.assertEqual(instructions, "Test instructions")
            self.assertEqual(questions, ["Test question 1", "Test question 2"])


if __name__ == "__main__":
    unittest.main()
