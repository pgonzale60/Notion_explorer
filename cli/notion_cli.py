import os
import requests
import sqlite3
import time
import argparse
from dotenv import load_dotenv
import csv
import glob
import json
from gemini_utils import call_gemini_api, MODEL_NAME
import re

# --- Setup ---
load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
if not NOTION_TOKEN:
    NOTION_TOKEN = input("Enter your Notion integration token: ").strip()
NOTION_API_URL = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}
DB_PATH = "notion_pages.db"
EXPORTS_DIR = "notion_notes"
OUTPUTS_DIR = "answers_to_questions_by_LLM"

# --- Utilities ---
def request_with_rate_limit(url, headers, method="GET", json=None, params=None):
    while True:
        if method == "GET":
            resp = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=json)
        else:
            raise ValueError("Unsupported HTTP method")
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 1))
            print(f"Rate limited. Retrying after {retry_after} seconds...")
            time.sleep(retry_after)
            continue
        resp.raise_for_status()
        return resp

def detect_id_type(notion_id):
    url_db = f"{NOTION_API_URL}/databases/{notion_id}"
    resp_db = requests.get(url_db, headers=HEADERS)
    if resp_db.status_code == 200:
        return "database"
    url_page = f"{NOTION_API_URL}/pages/{notion_id}"
    resp_page = requests.get(url_page, headers=HEADERS)
    if resp_page.status_code == 200:
        return "page"
    raise ValueError(f"ID {notion_id} is neither a valid page nor database ID, or you lack access.")

# --- DB Functions (for crawl_metadata) ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Add content column if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS pages (
        id TEXT PRIMARY KEY,
        parent_id TEXT,
        created_time TEXT,
        last_edited_time TEXT,
        content TEXT
    )''')
    # If upgrading from an older DB, add content column if missing
    c.execute("PRAGMA table_info(pages)")
    columns = [row[1] for row in c.fetchall()]
    if 'content' not in columns:
        c.execute('ALTER TABLE pages ADD COLUMN content TEXT')
    # --- New: Gemini analysis table ---
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
    conn.commit()
    return conn

def save_page_to_db(conn, page_id, parent_id, created_time, last_edited_time, content=None):
    c = conn.cursor()
    # Fetch existing content if present
    c.execute('SELECT content FROM pages WHERE id=?', (page_id,))
    row = c.fetchone()
    if content is None and row is not None:
        # Preserve existing content if new content is None
        content = row[0]
    c.execute('''INSERT OR REPLACE INTO pages (id, parent_id, created_time, last_edited_time, content)
                 VALUES (?, ?, ?, ?, ?)''', (page_id, parent_id, created_time, last_edited_time, content))
    conn.commit()

def get_page_from_db(conn, page_id):
    c = conn.cursor()
    c.execute('SELECT id, parent_id, created_time, last_edited_time, content FROM pages WHERE id=?', (page_id,))
    return c.fetchone()

def save_crawl_error(conn, id, parent_id, error_message, head_title, head_content):
    c = conn.cursor()
    c.execute('''INSERT INTO crawl_errors (id, parent_id, error_message, head_title, head_content)
                 VALUES (?, ?, ?, ?, ?)''', (id, parent_id, error_message, head_title, head_content))
    conn.commit()

def is_valid_database_id(database_id):
    url = f"{NOTION_API_URL}/databases/{database_id}"
    resp = requests.get(url, headers=HEADERS)
    return resp.status_code == 200

def get_child_pages_and_databases(parent_id):
    url = f"{NOTION_API_URL}/blocks/{parent_id}/children"
    child_pages = []
    child_databases = []
    params = {"page_size": 100}
    while True:
        resp = request_with_rate_limit(url, HEADERS, params=params)
        data = resp.json()
        for child in data.get("results", []):
            if child.get("type") == "child_page":
                child_pages.append({
                    "id": child["id"],
                    "title": child["child_page"].get("title", "")
                })
            elif child.get("type") == "child_database":
                child_databases.append({
                    "id": child["id"],
                    "title": child["child_database"].get("title", "")
                })
        next_cursor = data.get("next_cursor")
        if next_cursor:
            params["start_cursor"] = next_cursor
        else:
            break
    return child_pages, child_databases

def get_database_rows(database_id):
    url = f"{NOTION_API_URL}/databases/{database_id}/query"
    rows = []
    payload = {"page_size": 100}
    while True:
        resp = request_with_rate_limit(url, HEADERS, method="POST", json=payload)
        data = resp.json()
        for result in data.get("results", []):
            if result["object"] == "page":
                rows.append(result["id"])
        next_cursor = data.get("next_cursor")
        if next_cursor:
            payload["start_cursor"] = next_cursor
        else:
            break
    return rows

def get_page_metadata(page_id):
    id_type = detect_id_type(page_id)
    if id_type == "database":
        url = f"{NOTION_API_URL}/databases/{page_id}"
    else:
        url = f"{NOTION_API_URL}/pages/{page_id}"
    resp = request_with_rate_limit(url, HEADERS)
    data = resp.json()
    return {
        "id": page_id,
        "created_time": data.get("created_time"),
        "last_edited_time": data.get("last_edited_time"),
    }

def crawl_metadata(conn, page_id, parent_id=None, depth=0, resume_incomplete=False):
    try:
        meta = get_page_metadata(page_id)
    except Exception as e:
        save_crawl_error(conn, page_id, parent_id, str(e), "NA", "NA")
        save_page_to_db(conn, page_id, parent_id, "NA", "NA")
        print(f"Error fetching metadata for {page_id}: {e}")
        return
    db_page = get_page_from_db(conn, page_id)
    if not resume_incomplete and db_page and db_page[3] == meta["last_edited_time"]:
        print(f"Page {page_id} unchanged since last crawl. Skipping descendants.")
        return
    # Only update content if we have a value for it (should be rare here, but for safety)
    save_page_to_db(conn, page_id, parent_id, meta["created_time"], meta["last_edited_time"], db_page[4] if db_page else None)
    print(f"Saved page {page_id} (parent: {parent_id})")
    child_pages, child_databases = get_child_pages_and_databases(page_id)
    for child in child_pages:
        db_child = get_page_from_db(conn, child["id"])
        if resume_incomplete and db_child is not None and db_child[1] == page_id:
            print(f"Child page {child['id']} already crawled. Skipping.")
            continue
        elif not resume_incomplete and db_child and db_child[1] == page_id:
            print(f"Child page {child['id']} already crawled. Skipping.")
            continue
        crawl_metadata(conn, child["id"], parent_id=page_id, depth=depth+1, resume_incomplete=resume_incomplete)
    for db in child_databases:
        db_db = get_page_from_db(conn, db["id"])
        if resume_incomplete and db_db is not None and db_db[1] == page_id:
            print(f"Child database {db['id']} already crawled. Skipping.")
            continue
        elif not resume_incomplete and db_db and db_db[1] == page_id:
            print(f"Child database {db['id']} already crawled. Skipping.")
            continue
        print(f"Entering database {db['id']} (parent: {page_id})")
        if not is_valid_database_id(db["id"]):
            print(f"Warning: Block {db['id']} is not a valid or accessible database. Skipping.")
            try:
                title = get_database_title(db["id"])
            except Exception:
                title = "NA"
            try:
                first_row = get_first_db_row(db["id"])
            except Exception:
                first_row = "NA"
            save_page_to_db(conn, db["id"], page_id, "NA", "NA")
            save_crawl_error(conn, db["id"], page_id, "Not accessible or cross-workspace DB", str(title), str(first_row))
            continue
        try:
            row_ids = get_database_rows(db["id"])
            for row_id in row_ids:
                db_row = get_page_from_db(conn, row_id)
                if resume_incomplete and db_row is not None and db_row[1] == db["id"]:
                    print(f"Database row {row_id} already crawled. Skipping.")
                    continue
                elif not resume_incomplete and db_row and db_row[1] == db["id"]:
                    print(f"Database row {row_id} already crawled. Skipping.")
                    continue
                crawl_metadata(conn, row_id, parent_id=db["id"], depth=depth+1, resume_incomplete=resume_incomplete)
        except Exception as e:
            print(f"Error querying database {db['id']}: {e}. Skipping.")
            try:
                title = get_database_title(db["id"])
            except Exception:
                title = "NA"
            try:
                first_row = get_first_db_row(db["id"])
            except Exception:
                first_row = "NA"
            save_page_to_db(conn, db["id"], page_id, "NA", "NA")
            save_crawl_error(conn, db["id"], page_id, str(e), str(title), str(first_row))

# --- New: Extract head info ---
def get_page_title(page_id):
    url = f"{NOTION_API_URL}/pages/{page_id}"
    resp = request_with_rate_limit(url, HEADERS)
    data = resp.json()
    # Find the title property (usually 'title' or first title property)
    props = data.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            title_arr = prop["title"]
            if title_arr:
                return ''.join([t.get("plain_text", "") for t in title_arr])
    return "(No title found)"

def get_first_block(page_id):
    url = f"{NOTION_API_URL}/blocks/{page_id}/children?page_size=1"
    resp = request_with_rate_limit(url, HEADERS)
    data = resp.json()
    results = data.get("results", [])
    return results[0] if results else None

def get_database_title(database_id):
    url = f"{NOTION_API_URL}/databases/{database_id}"
    resp = request_with_rate_limit(url, HEADERS)
    data = resp.json()
    title_arr = data.get("title", [])
    if title_arr:
        return ''.join([t.get("plain_text", "") for t in title_arr])
    return "(No title found)"

def get_first_db_row(database_id):
    url = f"{NOTION_API_URL}/databases/{database_id}/query"
    payload = {"page_size": 1}
    resp = request_with_rate_limit(url, HEADERS, method="POST", json=payload)
    data = resp.json()
    results = data.get("results", [])
    return results[0] if results else None

# --- New: Integrate exported page contents ---
def integrate_exports():
    conn = init_db()
    notion_id_pattern = re.compile(r"[0-9a-fA-F]{32}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
    notes_added = 0
    def extract_notion_id_from_name(name):
        parts = name.rsplit(" ", 1)
        if len(parts) == 2 and notion_id_pattern.fullmatch(parts[1]):
            return parts[1]
        return None
    def ensure_parent_in_db(dir_path):
        parent_dir = os.path.dirname(dir_path)
        entry = os.path.basename(dir_path)
        parent_id = extract_notion_id_from_name(entry)
        if not parent_id:
            return None
        c = conn.cursor()
        c.execute('SELECT id FROM pages WHERE id=?', (parent_id,))
        if c.fetchone():
            return parent_id
        parent_parent_id = ensure_parent_in_db(parent_dir)
        save_page_to_db(conn, parent_id, parent_parent_id, None, None, None)
        return parent_id

    for entry in os.listdir(EXPORTS_DIR):
        entry_path = os.path.join(EXPORTS_DIR, entry)
        if os.path.isdir(entry_path):
            parent_id = extract_notion_id_from_name(entry)
            if parent_id:
                parent_id = ensure_parent_in_db(entry_path)
            else:
                parent_id = None
            md_files = glob.glob(os.path.join(entry_path, "*.md"))
            for md_file in md_files:
                filename = os.path.basename(md_file)
                if not filename.endswith(".md"):
                    continue
                # Extract unique ID: after last space, before .md
                parts = filename[:-3].rsplit(" ", 1)
                if len(parts) != 2:
                    continue  # skip files not matching pattern
                unique_id = parts[1]
                with open(md_file, encoding="utf-8") as f:
                    content = f.read().strip()
                if not content:
                    continue  # skip empty notes
                # Check if note already exists in DB
                c = conn.cursor()
                c.execute('SELECT id, content FROM pages WHERE id=?', (unique_id,))
                row = c.fetchone()
                if row:
                    # If content is missing/empty, update it
                    if not row[1] or row[1].strip() == "":
                        save_page_to_db(conn, unique_id, parent_id, None, None, content)
                        notes_added += 1
                    continue
                # Insert new note
                save_page_to_db(conn, unique_id, parent_id, None, None, content)
                notes_added += 1
    print(f"Integrated {notes_added} notes from markdown exports.")

# --- New: Batch Gemini Processing ---
def batch_gemini(questions_version="1"):
    from gemini_utils import MODEL_NAME
    conn = init_db()
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    c = conn.cursor()
    c.execute('SELECT id, content FROM pages WHERE content IS NOT NULL AND TRIM(content) != ""')
    notes = c.fetchall()
    print(f"Processing {len(notes)} notes with Gemini (questions_v{questions_version}, model={MODEL_NAME})...")
    for note_id, content in notes:
        output_path = os.path.join(OUTPUTS_DIR, f"gemini_{note_id}_v{questions_version}_{MODEL_NAME}.json")
        # Check if this note/version/model has already been processed
        if os.path.exists(output_path):
            try:
                with open(output_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                print(f"existing.questions_version={existing.get('questions_version')}, expected_version=v{questions_version}")
                print(f"existing.model={existing.get('model')}, expected_model={MODEL_NAME}")
                if (str(existing.get("questions_version")) == f"v{questions_version}" and
                    existing.get("model") == MODEL_NAME):
                    print(f"Skipping {note_id}: already processed with questions_v{questions_version}, model={MODEL_NAME}.")
                    continue
            except Exception:
                print(f"Warning: Could not verify version/model for {output_path}, skipping overwrite.")
                continue
        print(f"Processing note {note_id}...")
        result = call_gemini_api(content, questions_version)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Done. Results saved in {OUTPUTS_DIR}/.")

# --- Load Gemini outputs into DB ---
def load_gemini_outputs():
    conn = init_db()
    count = 0
    for fname in os.listdir(OUTPUTS_DIR):
        if not fname.startswith("gemini_") or not fname.endswith(".json"):
            continue
        # Parse note_id, version, model from filename
        try:
            base = fname[len("gemini_"):-len(".json")]
            parts = base.split("_v")
            note_id = parts[0]
            rem = parts[1]
            version, model = rem.split("_", 1)
            model = model.replace("_", "-")  # just in case
        except Exception:
            print(f"Skipping {fname}: could not parse identifiers.")
            continue
        fpath = os.path.join(OUTPUTS_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        date_executed = data.get("date_executed")
        # Remove meta fields from answers_json
        answers = {k: v for k, v in data.items() if k not in ("questions_version", "model", "date_executed")}
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO gemini_analysis (note_id, questions_version, model, date_executed, answers_json)
                     VALUES (?, ?, ?, ?, ?)''',
                  (note_id, f"v{version}", model, date_executed, json.dumps(answers, ensure_ascii=False)))
        count += 1
    conn.commit()
    print(f"Loaded {count} Gemini outputs into the DB.")

# --- 1. RESET_DB ---
def reset_db():
    """
    Integrate Notion notes, update DB with new IDs, and fetch missing metadata from Notion API
    """
    integrate_exports()
    conn = init_db()
    c = conn.cursor()
    c.execute('SELECT id, parent_id FROM pages WHERE created_time IS NULL OR last_edited_time IS NULL')
    missing = c.fetchall()
    for page_id, parent_id in missing:
        crawl_metadata(conn, page_id, parent_id=parent_id)
    print("DB reset and metadata fetched.")

# --- 2. ANALYZE_NOTES ---
def analyze_notes(questions_version=None):
    from cli.gemini_utils import load_questions
    if questions_version is None:
        # Use latest version by inspecting questions directory
        files = os.listdir(os.path.join(os.path.dirname(__file__), '../questions'))
        versions = []
        for fname in files:
            m = re.match(r'questions_v(\d+)\.json', fname)
            if m:
                versions.append(int(m.group(1)))
        if versions:
            questions_version = str(max(versions))
        else:
            questions_version = "1"
    conn = init_db()
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    c = conn.cursor()
    c.execute('SELECT id, content FROM pages WHERE content IS NOT NULL AND TRIM(content) != ""')
    notes = c.fetchall()
    for note_id, content in notes:
        output_path = os.path.join(OUTPUTS_DIR, f"gemini_{note_id}_v{questions_version}_{MODEL_NAME}.json")
        if os.path.exists(output_path):
            try:
                with open(output_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                if (str(existing.get("questions_version")) == f"v{questions_version}" and
                    existing.get("model") == MODEL_NAME):
                    continue
            except Exception as e:
                continue
        result = call_gemini_api(content, questions_version)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    print("Gemini analysis complete.")

# --- 3. LOAD_GEMINI_OUTPUTS ---
def load_gemini_outputs():
    conn = init_db()
    count = 0
    for fname in os.listdir(OUTPUTS_DIR):
        if not fname.startswith("gemini_") or not fname.endswith(".json"):
            continue
        try:
            base = fname[len("gemini_"):-len(".json")]
            parts = base.split("_v")
            note_id = parts[0]
            rem = parts[1]
            version, model = rem.split("_", 1)
            model = model.replace("_", "-")
        except Exception:
            continue
        fpath = os.path.join(OUTPUTS_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        date_executed = data.get("date_executed")
        answers = {k: v for k, v in data.items() if k not in ("questions_version", "model", "date_executed")}
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO gemini_analysis (note_id, questions_version, model, date_executed, answers_json)
                     VALUES (?, ?, ?, ?, ?)''',
                  (note_id, f"v{version}", model, date_executed, json.dumps(answers, ensure_ascii=False)))
        count += 1
    conn.commit()
    print(f"Loaded {count} Gemini outputs into the DB.")

# --- 4. LAUNCH_GUI ---
def launch_gui():
    print("Launching GUI (to be implemented)...")

# --- Move legacy CLI logic to cli/legacy/ ---
# (Remove the main() CLI entrypoint and argument parsing from this file)
