# backend/scripts/create_preauth_db.py
import sqlite3
import os

ROOT = os.path.dirname(os.path.dirname(__file__))  # backend
DATA = os.path.join(ROOT, 'data')
os.makedirs(DATA, exist_ok=True)
DB = os.path.join(DATA, 'preauth_feedback.db')

conn = sqlite3.connect(DB)
conn.execute("""
CREATE TABLE IF NOT EXISTS preauth_feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT,
  procedure_code TEXT,
  plan_id TEXT,
  estimated_oop REAL,
  actual_oop REAL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")
conn.commit()
conn.close()
print(f"✅ Created database at: {DB}")
print("   Table 'preauth_feedback' is ready")
