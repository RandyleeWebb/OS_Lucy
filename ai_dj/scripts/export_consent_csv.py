import sqlite3
import csv
from pathlib import Path
from datetime import datetime

# Path to the consent DB (created by init_consent_db.py)
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "consent.db"

def export_consent_csv(output_dir: Path = None):
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Consent DB not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, skit, timestamp, user_id, consent FROM consent_log")
    rows = cur.fetchall()
    conn.close()

    if output_dir is None:
        output_dir = Path(__file__).resolve().parents[2] / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    csv_path = output_dir / f"consent_log_{date_str}.csv"
    with open(csv_path, "w", newline='', encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["id", "skit", "timestamp", "user_id", "consent"])
        writer.writerows(rows)
    print(f"Exported {len(rows)} consent records to {csv_path}")

if __name__ == "__main__":
    export_consent_csv()
