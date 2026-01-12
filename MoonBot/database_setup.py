import sqlite3
import os

DB_NAME = "MoonBot/moonbot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Tabel Users (Pengguna Bot)
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        role TEXT DEFAULT 'user',  -- 'owner', 'admin', 'user', 'pending'
        status TEXT DEFAULT 'pending', -- 'active', 'banned', 'pending'
        joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Tabel Sessions (Akun Telegram yang ditambahkan User)
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        phone TEXT,
        api_id TEXT,
        api_hash TEXT,
        session_string TEXT,
        session_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )''')

    # Tabel Templates (Template Target User)
    c.execute('''CREATE TABLE IF NOT EXISTS templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        content JSON, -- List target dalam format JSON
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )''')

    conn.commit()
    conn.close()
    print(f"Database {DB_NAME} initialized.")

if __name__ == "__main__":
    init_db()
