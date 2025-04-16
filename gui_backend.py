import os
import sqlite3
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

DB_PATH = "notion_pages.db"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Note(BaseModel):
    id: str
    parent_id: Optional[str]
    created_time: Optional[str]
    last_edited_time: Optional[str]
    content: Optional[str]

class GeminiAnswer(BaseModel):
    note_id: str
    questions_version: str
    model: str
    date_executed: Optional[str]
    answers_json: dict

class QuestionVersion(BaseModel):
    version: str
    date_updated: str
    
class QuestionData(BaseModel):
    version: str
    instructions: str
    questions: List[str]
    date_updated: str

@app.get("/notes", response_model=List[Note])
def get_notes():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, parent_id, created_time, last_edited_time, content FROM pages")
    notes = [Note(id=row[0], parent_id=row[1], created_time=row[2], last_edited_time=row[3], content=row[4]) for row in c.fetchall()]
    conn.close()
    return notes

@app.get("/note/{note_id}", response_model=Note)
def get_note(note_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, parent_id, created_time, last_edited_time, content FROM pages WHERE id=?", (note_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Note not found")
    return Note(id=row[0], parent_id=row[1], created_time=row[2], last_edited_time=row[3], content=row[4])

@app.get("/answers/{note_id}", response_model=List[GeminiAnswer])
def get_answers(note_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT note_id, questions_version, model, date_executed, answers_json FROM gemini_analysis WHERE note_id=?", (note_id,))
    answers = [GeminiAnswer(note_id=row[0], questions_version=row[1], model=row[2], date_executed=row[3], answers_json=eval(row[4]) if isinstance(row[4], str) else row[4]) for row in c.fetchall()]
    conn.close()
    return answers

@app.get("/answers_index")
def get_answers_index():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT note_id FROM gemini_analysis")
    ids = [row[0] for row in c.fetchall()]
    conn.close()
    return ids

@app.get("/note_versions_index")
def get_note_versions_index():
    """
    Returns a mapping of note_id -> list of available question versions
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT note_id, questions_version FROM gemini_analysis")
    
    # Build a mapping of note_id -> list of versions
    version_map = {}
    for row in c.fetchall():
        note_id, version = row
        if note_id not in version_map:
            version_map[note_id] = []
        version_map[note_id].append(version)
    
    conn.close()
    return version_map

@app.get("/hierarchy")
def get_hierarchy():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, parent_id FROM pages")
    rows = c.fetchall()
    conn.close()
    # Build a dict of id -> children
    from collections import defaultdict
    tree = defaultdict(list)
    for id, parent_id in rows:
        tree[parent_id].append(id)
    return tree

# New endpoints for questions data

@app.get("/question_versions", response_model=List[QuestionVersion])
def get_question_versions():
    """
    Get all available question versions from the database
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT version, date_updated FROM questions ORDER BY version DESC")
    versions = [QuestionVersion(version=row[0], date_updated=row[1]) for row in c.fetchall()]
    conn.close()
    return versions

@app.get("/questions/{version}", response_model=QuestionData)
def get_questions_by_version(version: str):
    """
    Get questions for a specific version
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT version, date_updated, questions_json FROM questions WHERE version=?", (version,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Question version {version} not found")
    
    version_str, date_updated, questions_json = row
    
    # Parse the JSON string
    try:
        data = json.loads(questions_json)
        return QuestionData(
            version=version_str,
            date_updated=date_updated,
            instructions=data.get("instructions", ""),
            questions=data.get("questions", [])
        )
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Invalid JSON data for question version {version}")

@app.get("/latest_question_version")
def get_latest_question_version():
    """
    Get the latest question version
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT version FROM questions ORDER BY version DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    
    if not row:
        return {"version": None}
    return {"version": row[0]}
