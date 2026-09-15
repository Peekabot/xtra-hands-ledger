ALTER TABLE quotes ADD COLUMN fulfilled_by TEXT;

CREATE TABLE IF NOT EXISTS clicks (
  id INTEGER PRIMARY KEY,
  quote_id INTEGER,
  dest TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);
