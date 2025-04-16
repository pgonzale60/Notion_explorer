import os
import requests
import sqlite3
import time
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
if not NOTION_TOKEN:
    NOTION_TOKEN = input("Enter your Notion integration token: ").strip()

PARENT_ID = input("Enter the parent page or database ID: ").strip()

NOTION_API_URL = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

DB_PATH = "notion_pages.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS pages (
        id TEXT PRIMARY KEY,
        parent_id TEXT,
        created_time TEXT,
        last_edited_time TEXT
    )''')
    conn.commit()
    return conn

def save_page_to_db(conn, page_id, parent_id, created_time, last_edited_time):
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO pages (id, parent_id, created_time, last_edited_time)
                 VALUES (?, ?, ?, ?)''', (page_id, parent_id, created_time, last_edited_time))
    conn.commit()

def get_page_from_db(conn, page_id):
    c = conn.cursor()
    c.execute('SELECT id, parent_id, created_time, last_edited_time FROM pages WHERE id=?', (page_id,))
    return c.fetchone()

def request_with_rate_limit(url, headers, params=None):
    while True:
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 1))
            print(f"Rate limited. Retrying after {retry_after} seconds...")
            time.sleep(retry_after)
            continue
        resp.raise_for_status()
        return resp

def get_child_pages_and_databases(parent_id):
    url = f"{NOTION_API_URL}/blocks/{parent_id}/children"
    child_pages = []
    child_databases = []
    params = {"page_size": 100}
    while True:
        resp = request_with_rate_limit(url, HEADERS, params)
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
        resp = requests.post(url, headers=HEADERS, json=payload)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 1))
            print(f"Rate limited (database query). Retrying after {retry_after} seconds...")
            time.sleep(retry_after)
            continue
        resp.raise_for_status()
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
    url = f"{NOTION_API_URL}/pages/{page_id}"
    resp = request_with_rate_limit(url, HEADERS)
    data = resp.json()
    return {
        "id": page_id,
        "created_time": data.get("created_time"),
        "last_edited_time": data.get("last_edited_time"),
    }

def is_valid_database_id(database_id):
    url = f"{NOTION_API_URL}/databases/{database_id}"
    resp = requests.get(url, headers=HEADERS)
    return resp.status_code == 200

def crawl_page_tree(conn, page_id, parent_id=None, depth=0):
    db_page = get_page_from_db(conn, page_id)
    meta = get_page_metadata(page_id)
    if db_page and db_page[3] == meta["last_edited_time"]:
        print(f"Page {page_id} unchanged since last crawl. Skipping descendants.")
        return
    save_page_to_db(conn, page_id, parent_id, meta["created_time"], meta["last_edited_time"])
    print(f"Saved page {page_id} (parent: {parent_id})")
    child_pages, child_databases = get_child_pages_and_databases(page_id)
    for child in child_pages:
        crawl_page_tree(conn, child["id"], parent_id=page_id, depth=depth+1)
    for db in child_databases:
        print(f"Entering database {db['id']} (parent: {page_id})")
        if not is_valid_database_id(db["id"]):
            print(f"Warning: Block {db['id']} is not a valid or accessible database. Skipping.")
            continue
        try:
            row_ids = get_database_rows(db["id"])
            for row_id in row_ids:
                crawl_page_tree(conn, row_id, parent_id=db["id"], depth=depth+1)
        except Exception as e:
            print(f"Error querying database {db['id']}: {e}. Skipping.")

def detect_id_type(notion_id):
    # Try database endpoint
    url_db = f"{NOTION_API_URL}/databases/{notion_id}"
    resp_db = requests.get(url_db, headers=HEADERS)
    if resp_db.status_code == 200:
        return "database"
    # Try page endpoint
    url_page = f"{NOTION_API_URL}/pages/{notion_id}"
    resp_page = requests.get(url_page, headers=HEADERS)
    if resp_page.status_code == 200:
        return "page"
    raise ValueError(f"ID {notion_id} is neither a valid page nor database ID, or you lack access.")

def main():
    conn = init_db()
    id_type = detect_id_type(PARENT_ID)
    print(f"Detected {id_type} for input ID: {PARENT_ID}")
    if id_type == "page":
        crawl_page_tree(conn, PARENT_ID)
    elif id_type == "database":
        print(f"Querying database {PARENT_ID} for rows...")
        row_ids = get_database_rows(PARENT_ID)
        for row_id in row_ids:
            crawl_page_tree(conn, row_id, parent_id=PARENT_ID)
    print("Done. All metadata saved to notion_pages.db.")

if __name__ == "__main__":
    main()
