#!/usr/bin/env python3
"""Ingest bid-triage JSON (or a sample) into projects.db.

Does not scrape live pages. The watcher is the other repo's
scripts/bid_triage.py — this file only records what is new.
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "projects.db"
TRIAGE_DIR = Path("/root/xtra-hands-bid-triage/data")
TASKS = ("site-walk", "bid", "haul", "surplus log")

SAMPLE = [
    {
        "title": "Albany sidewalk restoration — sample",
        "url": "https://www.albanyny.gov/Bids.aspx#sample",
        "source": "albany_city",
        "decision": "GO",
        "margin": 0.4,
        "type": "job",
    }
]

def connect():
    cx = sqlite3.connect(DB)
    cx.execute(
        """CREATE TABLE IF NOT EXISTS events (
             id INTEGER PRIMARY KEY,
             kind TEXT,
             project_id INTEGER,
             payload TEXT)"""
    )
    cx.execute(
        """CREATE TABLE IF NOT EXISTS bids (
             url TEXT PRIMARY KEY,
             title TEXT,
             source TEXT,
             decision TEXT,
             project_id INTEGER)"""
    )
    cx.execute(
        """CREATE TABLE IF NOT EXISTS projects (
             id INTEGER PRIMARY KEY,
             name TEXT NOT NULL,
             status TEXT NOT NULL DEFAULT 'open')"""
    )
    cx.execute(
        """CREATE TABLE IF NOT EXISTS tasks (
             id INTEGER PRIMARY KEY,
             project_id INTEGER NOT NULL,
             name TEXT NOT NULL,
             status TEXT NOT NULL DEFAULT 'open')"""
    )
    return cx

def load_results():
    rows = []
    if TRIAGE_DIR.exists():
        files = sorted(TRIAGE_DIR.glob("triage_*.json"))
        for f in files:
            try:
                rows.extend(json.loads(f.read_text()))
            except Exception as e:
                print("skip", f, e)
    if "--sample" in sys.argv or not rows:
        rows = SAMPLE
        print("using sample bid (no triage JSON found)" if "--sample" not in sys.argv else "using --sample")
    return rows

def ingest(bid):
    url = bid.get("url") or ""
    title = bid.get("title") or "untitled"
    if not url:
        return None
    cx = connect()
    seen = cx.execute("SELECT project_id FROM bids WHERE url=?", (url,)).fetchone()
    if seen:
        cx.close()
        return None
    cur = cx.execute(
        "INSERT INTO projects(name, status) VALUES (?, 'open')",
        (title,),
    )
    pid = cur.lastrowid
    for name in TASKS:
        cx.execute(
            "INSERT INTO tasks(project_id, name, status) VALUES (?,?, 'open')",
            (pid, name),
        )
    cx.execute(
        "INSERT INTO bids(url, title, source, decision, project_id) VALUES (?,?,?,?,?)",
        (url, title, bid.get("source"), bid.get("decision"), pid),
    )
    cx.execute(
        "INSERT INTO events(kind, project_id, payload) VALUES ('bid_seen', ?, ?)",
        (pid, json.dumps(bid, default=str)),
    )
    cx.commit()
    cx.close()
    return pid

def main():
    new = []
    for bid in load_results():
        pid = ingest(bid)
        if pid:
            new.append((pid, bid.get("title"), bid.get("decision")))
            print(f"NEW project {pid} [{bid.get('decision')}] {bid.get('title')}")
    if not new:
        print("no new bids")
    print("db", DB)

if __name__ == "__main__":
    main()
