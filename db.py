import os
import sqlite3
from datetime import datetime
from config import DATA_DIR

DB_NAME = os.path.join(DATA_DIR, "CopilotAgentDocs.db")


# ==============================
# DB CONNECTION
# ==============================

def get_connection():
    return sqlite3.connect(DB_NAME)


# ==============================
# CREATE TABLES
# ==============================

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # Documents table (static info)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        doc_id TEXT PRIMARY KEY,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_type TEXT,
        created_at TEXT
    )
    """)

    # Document versions (dynamic info)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS document_versions (
        version_id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id TEXT,
        version INTEGER,
        uploaded_by TEXT,
        uploaded_at TEXT,
        file_size INTEGER,
        FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
    )
    """)

    conn.commit()
    conn.close()

    print("✅ Tables created")


# ==============================
# INSERT DOCUMENT
# ==============================

def insert_document(doc_id, file_name, file_path, file_type):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO documents (doc_id, file_name, file_path, file_type, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (
        doc_id,
        file_name,
        file_path,
        file_type,
        datetime.utcnow().isoformat()
    ))

    conn.commit()
    conn.close()


# ==============================
# INSERT VERSION
# ==============================

def insert_document_version(doc_id, version, uploaded_by, file_size):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO document_versions (doc_id, version, uploaded_by, uploaded_at, file_size)
    VALUES (?, ?, ?, ?, ?)
    """, (
        doc_id,
        version,
        uploaded_by,
        datetime.utcnow().isoformat(),
        file_size
    ))

    conn.commit()
    conn.close()


# ==============================
# GET LATEST VERSION
# ==============================

def get_latest_version(doc_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT MAX(version) FROM document_versions WHERE doc_id = ?
    """, (doc_id,))

    result = cursor.fetchone()[0]
    conn.close()

    return result if result else 0


# ==============================
# GET DOCUMENT
# ==============================

def get_document(doc_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM documents WHERE doc_id = ?
    """, (doc_id,))

    doc = cursor.fetchone()
    conn.close()

    return doc
