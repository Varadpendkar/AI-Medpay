# scripts/create_leads_db.py
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'leads.db')
os.makedirs(os.path.dirname(DB), exist_ok=True)
conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS leads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  profile_json TEXT,
  ip TEXT,
  source TEXT
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS recommendations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_id INTEGER,
  rank INTEGER,
  plan_id TEXT,
  plan_name TEXT,
  provider TEXT,
  model_score REAL,
  recommended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(lead_id) REFERENCES leads(id)
);
""")

conn.commit()
conn.close()
print("✅ Leads DB created at:", DB)
print("   Tables: leads, recommendations")
print("   Ready to store Get Quote submissions and recommendations.")
