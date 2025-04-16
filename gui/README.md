# Notion Notes Explorer GUI

## Quick Start

1. **Backend:**
   - Install FastAPI and Uvicorn if not already:
     ```sh
     pip install fastapi uvicorn
     ```
   - Start the backend API:
     ```sh
     uvicorn gui_backend:app --reload
     ```

2. **Frontend:**
   - Install Node.js dependencies:
     ```sh
     cd gui
     npm install
     ```
   - Start the React app:
     ```sh
     npm start
     ```
   - The app will open at [http://localhost:3000](http://localhost:3000)

## Features
- Browse notes and metadata
- View Gemini answers per note
- Select notes to see details

## Requirements
- Python 3.8+
- Node.js 16+
- FastAPI, Uvicorn, React, MUI
