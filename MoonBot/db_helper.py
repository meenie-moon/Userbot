import sqlite3
import json
from .config import DB_NAME, OWNER_ID

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Auto-Migration: Pastikan kolom total_broadcasts ada di users
    try:
        c.execute("SELECT total_broadcasts FROM users LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE users ADD COLUMN total_broadcasts INTEGER DEFAULT 0")
        conn.commit()

    # Auto-Migration: Pastikan kolom is_default ada di sessions
    try:
        c.execute("SELECT is_default FROM sessions LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE sessions ADD COLUMN is_default INTEGER DEFAULT 0")
        conn.commit()
        
    return conn

# --- USER MANAGEMENT ---

def check_user_status(user_id):
    """
    Returns: 'active', 'pending', 'banned', or None (if not exists)
    """
    conn = get_connection()
    c = conn.cursor()
    
    # Auto-add owner if not exists
    if user_id == OWNER_ID:
        c.execute("SELECT status FROM users WHERE user_id=?", (user_id,))
        res = c.fetchone()
        if not res:
            c.execute("INSERT INTO users (user_id, role, status, total_broadcasts) VALUES (?, 'owner', 'active', 0)", (user_id,))
            conn.commit()
            return 'active'
        return res[0]

    c.execute("SELECT status FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def request_access(user_id):
    conn = get_connection()
    c = conn.cursor()
    # Insert ignore if exists
    c.execute("INSERT OR IGNORE INTO users (user_id, role, status, total_broadcasts) VALUES (?, 'user', 'pending', 0)", (user_id,))
    conn.commit()
    conn.close()

def get_pending_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE status='pending'")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def approve_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET status='active' WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def block_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET status='banned' WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def revoke_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET status='pending' WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_all_active_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE status='active' OR role='owner'")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def increment_broadcast_count(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET total_broadcasts = total_broadcasts + 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

# --- SESSION MANAGEMENT ---

def add_session(user_id, phone, session_string, api_id, api_hash, name):
    conn = get_connection()
    c = conn.cursor()
    
    # Cek apakah ini akun pertama?
    c.execute("SELECT COUNT(*) FROM sessions WHERE user_id=?", (user_id,))
    count = c.fetchone()[0]
    is_default = 1 if count == 0 else 0
    
    c.execute("""
        INSERT INTO sessions (user_id, phone, session_string, api_id, api_hash, session_name, is_default)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, phone, session_string, api_id, api_hash, name, is_default))
    conn.commit()
    conn.close()

def get_user_sessions(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, session_name, phone, is_default FROM sessions WHERE user_id=?", (user_id,))
    sessions = []
    for row in c.fetchall():
        sessions.append({
            'id': row[0],
            'name': row[1],
            'phone': row[2],
            'is_default': row[3]
        })
    conn.close()
    return sessions

def set_default_session(user_id, session_id):
    conn = get_connection()
    c = conn.cursor()
    # Reset semua jadi 0
    c.execute("UPDATE sessions SET is_default=0 WHERE user_id=?", (user_id,))
    # Set yang dipilih jadi 1
    c.execute("UPDATE sessions SET is_default=1 WHERE id=? AND user_id=?", (session_id, user_id))
    conn.commit()
    conn.close()

def get_active_session_name(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT session_name FROM sessions WHERE user_id=? AND is_default=1", (user_id,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else "Tidak Ada"

def get_session_data(session_id):
    conn = get_connection()
    c = conn.cursor()
    # Update: Ambil session_name dan is_default juga
    c.execute("SELECT session_string, api_id, api_hash, phone, session_name, is_default FROM sessions WHERE id=?", (session_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            'session_string': row[0], 
            'api_id': row[1], 
            'api_hash': row[2], 
            'phone': row[3],
            'name': row[4],
            'is_default': row[5]
        }
    return None

def delete_session(session_id, user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE id=? AND user_id=?", (session_id, user_id))
    # Jika yang dihapus adalah default, set default baru ke yg lain jika ada
    c.execute("SELECT id FROM sessions WHERE user_id=? LIMIT 1", (user_id,))
    res = c.fetchone()
    if res:
        c.execute("UPDATE sessions SET is_default=1 WHERE id=?", (res[0],))
    conn.commit()
    conn.close()

# --- TEMPLATE MANAGEMENT ---

def add_template(user_id, name, content_list):
    conn = get_connection()
    c = conn.cursor()
    content_json = json.dumps(content_list)
    c.execute("INSERT INTO templates (user_id, name, content) VALUES (?, ?, ?)", (user_id, name, content_json))
    conn.commit()
    conn.close()

def update_template_content(template_id, user_id, new_content_list):
    conn = get_connection()
    c = conn.cursor()
    content_json = json.dumps(new_content_list)
    c.execute("UPDATE templates SET content=? WHERE id=? AND user_id=?", (content_json, template_id, user_id))
    conn.commit()
    conn.close()

def get_user_templates(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, content FROM templates WHERE user_id=?", (user_id,))
    templates = []
    for row in c.fetchall():
        templates.append({
            'id': row[0],
            'name': row[1],
            'content': json.loads(row[2])
        })
    conn.close()
    return templates

def delete_template(template_id, user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM templates WHERE id=? AND user_id=?", (template_id, user_id))
    conn.commit()
    conn.close()

def get_user_stats(user_id):
    conn = get_connection()
    c = conn.cursor()
    
    # Hitung Sesi (Userbot)
    c.execute("SELECT COUNT(*) FROM sessions WHERE user_id=?", (user_id,))
    session_count = c.fetchone()[0]
    
    # Hitung Template
    c.execute("SELECT COUNT(*) FROM templates WHERE user_id=?", (user_id,))
    tpl_count = c.fetchone()[0]
    
    # Hitung Total Broadcast (dari kolom user)
    # Handle jika kolom null (user lama)
    c.execute("SELECT total_broadcasts FROM users WHERE user_id=?", (user_id,))
    res = c.fetchone()
    bc_count = res[0] if res and res[0] else 0
    
    conn.close()
    
    return {
        'sessions': session_count,
        'templates': tpl_count,
        'broadcasts': bc_count
    }