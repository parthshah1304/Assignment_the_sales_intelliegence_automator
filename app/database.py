import sqlite3
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.config import settings

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DATABASE_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        input_raw TEXT NOT NULL,
        company_name TEXT,
        website TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        error_message TEXT,
        company_overview TEXT,
        core_products_services TEXT,
        target_customer TEXT,
        b2b_decision TEXT,
        b2b_confidence REAL,
        b2b_reasoning TEXT,
        sales_questions TEXT,
        key_signals TEXT,
        scraped_pages TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()

def create_lead(input_raw: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO leads (input_raw, status, created_at, updated_at)
        VALUES (?, 'pending', ?, ?)
    """, (input_raw.strip(), now, now))
    lead_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return lead_id

def get_lead(lead_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return _row_to_dict(row)

def list_leads(b2b_filter: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM leads WHERE 1=1"
    params = []
    
    if b2b_filter and b2b_filter.lower() in ("yes", "no"):
        query += " AND LOWER(b2b_decision) = ?"
        params.append(b2b_filter.lower())
        
    if search:
        search_pattern = f"%{search}%"
        query += " AND (input_raw LIKE ? OR company_name LIKE ? OR company_overview LIKE ?)"
        params.extend([search_pattern, search_pattern, search_pattern])
        
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]

def update_lead_status(lead_id: int, status: str, error_message: Optional[str] = None):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE leads 
        SET status = ?, error_message = ?, updated_at = ?
        WHERE id = ?
    """, (status, error_message, now, lead_id))
    conn.commit()
    conn.close()

def update_lead_brief(
    lead_id: int,
    company_name: str,
    website: Optional[str],
    company_overview: str,
    core_products_services: str,
    target_customer: str,
    b2b_decision: str,
    b2b_confidence: float,
    b2b_reasoning: str,
    sales_questions: List[str],
    key_signals: List[str],
    scraped_pages: List[Dict[str, Any]]
):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE leads 
        SET company_name = ?,
            website = ?,
            company_overview = ?,
            core_products_services = ?,
            target_customer = ?,
            b2b_decision = ?,
            b2b_confidence = ?,
            b2b_reasoning = ?,
            sales_questions = ?,
            key_signals = ?,
            scraped_pages = ?,
            status = 'completed',
            error_message = NULL,
            updated_at = ?
        WHERE id = ?
    """, (
        company_name,
        website,
        company_overview,
        core_products_services,
        target_customer,
        b2b_decision,
        b2b_confidence,
        b2b_reasoning,
        json.dumps(sales_questions),
        json.dumps(key_signals),
        json.dumps(scraped_pages),
        now,
        lead_id
    ))
    conn.commit()
    conn.close()

def delete_lead(lead_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def clear_all_leads():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM leads")
    conn.commit()
    conn.close()

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row["value"]
    return default

def set_setting(key: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, value))
    conn.commit()
    conn.close()

def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    if d.get("sales_questions"):
        try:
            d["sales_questions"] = json.loads(d["sales_questions"])
        except Exception:
            d["sales_questions"] = []
    else:
        d["sales_questions"] = []
        
    if d.get("key_signals"):
        try:
            d["key_signals"] = json.loads(d["key_signals"])
        except Exception:
            d["key_signals"] = []
    else:
        d["key_signals"] = []

    if d.get("scraped_pages"):
        try:
            d["scraped_pages"] = json.loads(d["scraped_pages"])
        except Exception:
            d["scraped_pages"] = []
    else:
        d["scraped_pages"] = []
        
    return d
