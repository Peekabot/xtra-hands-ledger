#!/usr/bin/env python3
"""Next slice after run_test.sh passes. Still no Lupa."""
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parent / "projects.db"

def complete_named(project_id: int, name: str) -> bool:
    cx = sqlite3.connect(DB)
    cx.row_factory = sqlite3.Row
    row = cx.execute(
        "SELECT id, status FROM tasks WHERE project_id=? AND name=?",
        (project_id, name),
    ).fetchone()
    if not row or row["status"] == "done":
        cx.close()
        return False
    cx.execute("UPDATE tasks SET status='done' WHERE id=?", (row["id"],))
    open_n = cx.execute(
        "SELECT COUNT(*) FROM tasks WHERE project_id=? AND status='open'",
        (project_id,),
    ).fetchone()[0]
    if open_n == 0:
        cx.execute("UPDATE projects SET status='done' WHERE id=?", (project_id,))
    cx.commit()
    cx.close()
    return True

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python3 complete_named.py PROJECT_ID TASK_NAME")
        sys.exit(2)
    ok = complete_named(int(sys.argv[1]), sys.argv[2])
    print("updated" if ok else "no-op")
