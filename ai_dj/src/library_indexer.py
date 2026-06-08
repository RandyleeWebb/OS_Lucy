import os
import sqlite3
from pathlib import Path

MUSIC_ROOT = Path(__file__).resolve().parents[2] / 'docker' / 'navidrome' / 'music'
DB_PATH = Path(__file__).resolve().parents[2] / 'data' / 'library_index.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            title TEXT,
            artist TEXT,
            album TEXT,
            duration INTEGER,
            genre TEXT
        )
    ''')
    conn.commit()
    conn.close()

def index_music():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for root, _, files in os.walk(MUSIC_ROOT):
        for f in files:
            if f.lower().endswith(('.mp3', '.flac', '.wav', '.ogg')):
                full_path = Path(root) / f
                # Simple metadata extraction using mutagen if available
                title = artist = album = genre = None
                duration = None
                try:
                    from mutagen import File
                    audio = File(full_path)
                    if audio:
                        duration = int(audio.info.length)
                        tags = audio.tags
                        if tags:
                            title = tags.get('TIT2', [None])[0]
                            artist = tags.get('TPE1', [None])[0]
                            album = tags.get('TALB', [None])[0]
                            genre = tags.get('TCON', [None])[0]
                except Exception:
                    pass
                cur.execute('''
                    INSERT INTO tracks (path, title, artist, album, duration, genre)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (str(full_path), title, artist, album, duration, genre))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    os.makedirs(DB_PATH.parent, exist_ok=True)
    init_db()
    index_music()
    print(f"Indexed music library into {DB_PATH}")
