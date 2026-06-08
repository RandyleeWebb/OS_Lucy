import sqlite3
from pathlib import Path
import os

def init_consent_db(db_path: Path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS consent_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skit TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            user_id TEXT,
            consent INTEGER NOT NULL CHECK (consent IN (0,1))
        )
    ''')
    conn.commit()
    conn.close()
    print(f"Consent DB initialized at {db_path}")

if __name__ == "__main__":
    # Ensure data directory exists
    data_dir = Path(__file__).resolve().parents[2] / "data"
    os.makedirs(data_dir, exist_ok=True)
    db_path = data_dir / "consent.db"
    init_consent_db(db_path)
