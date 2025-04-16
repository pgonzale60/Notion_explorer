import os
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

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
