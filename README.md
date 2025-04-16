# Notion Notes Explorer

A comprehensive integration system for analyzing Notion notes using the Notion API and Gemini AI, with tools for metadata crawling, content analysis, and an interactive UI for exploration.

## Features

- **Notion API Integration**: Automatically fetch and synchronize notes from your Notion workspace
- **Metadata Crawling**: Efficiently traverse your Notion workspace and collect metadata
- **Content Analysis**: Process note content using Google's Gemini AI model
- **Question-Based Analysis**: Analyze notes using versioned sets of questions
- **Interactive Explorer UI**: Browse, filter, and view your notes and analyses in a modern web interface

## Project Structure

```
notion_integration/
├── cli/                     # Command-line interface tools
│   ├── notion_cli.py        # Main CLI logic
│   ├── gemini_utils.py      # Gemini AI integration utilities
│   └── get_notion_metadata.py # Notion metadata fetching
├── gui/                     # React-based web interface
│   ├── public/              # Static assets
│   └── src/                 # React source code
├── questions/               # Question sets for Gemini AI analysis
│   ├── questions_v1.json    # Version 1 of analysis questions
│   ├── questions_v2.json    # Version 2 of analysis questions
│   └── questions_v3.json    # Version 3 of analysis questions
├── answers_to_questions_by_LLM/ # Stored analysis results
├── notion_notes/            # Local storage for Notion notes
├── gui_backend.py           # FastAPI backend for the web interface
├── notion_explorer.py       # Entrypoint for CLI commands
└── requirements.txt         # Python dependencies
```

## Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/notion-integration.git
   cd notion-integration
   ```

2. **Set up Python environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Notion API access**:
   - Create a Notion integration at https://www.notion.so/my-integrations
   - Share your Notion pages with the integration
   - Create a `.env` file with your Notion API token:
     ```
     NOTION_TOKEN=your-notion-integration-token
     ```

4. **Install frontend dependencies**:
   ```bash
   cd gui
   npm install
   ```

## Usage

### CLI Commands

- **Reset database and fetch metadata**:
  ```bash
  python notion_explorer.py reset_db
  ```

- **Analyze notes with Gemini AI**:
  ```bash
  python notion_explorer.py analyze_notes
  ```
  
  To specify a questions version:
  ```bash
  python notion_explorer.py analyze_notes --questions_version 3
  ```

- **Load analysis results into database**:
  ```bash
  python notion_explorer.py load_outputs
  ```

### Web Interface

1. **Start the backend server**:
   ```bash
   uvicorn gui_backend:app --reload
   ```

2. **Start the frontend development server**:
   ```bash
   cd gui
   npm start
   ```

3. **Open the web interface** at http://localhost:3000

## Extending the Project

### Adding New Question Sets

1. Create a new question file in the `questions/` directory:
   ```json
   {
     "version": "v4",
     "instructions": "Instructions for the AI model...",
     "questions": [
       "Question 1?",
       "Question 2?",
       "..."
     ]
   }
   ```

2. Run the analysis with the new version:
   ```bash
   python notion_explorer.py analyze_notes --questions_version 4
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Notion API for providing access to workspace data
- Google's Gemini AI for powerful text analysis capabilities
- React and Material UI for the web interface
