#!/usr/bin/env python3
"""Local demo signup. Not public-facing. Keep iSH in the foreground."""
import cgi
import json
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PHOTOS = ROOT / "photos"
PHOTOS.mkdir(exist_ok=True)
DB = ROOT / "projects.db"
PAGES = {
    "/": ROOT / "static" / "quote.html",
    "/quote.html": ROOT / "static" / "quote.html",
    "/log.html": ROOT / "static" / "log.html",
}

def init():
    cx = sqlite3.connect(DB)
    cx.executescript(
        """
        CREATE TABLE IF NOT EXISTS quotes (
          id INTEGER PRIMARY KEY,
          created_at TEXT DEFAULT (datetime('now')),
          name TEXT,
          phone TEXT,
          email TEXT,
          address TEXT,
          work TEXT,
          notes TEXT,
          photo TEXT,
          status TEXT DEFAULT 'new'
        );
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY,
          kind TEXT,
          project_id INTEGER,
          payload TEXT
        );
        CREATE TABLE IF NOT EXISTS projects (
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'open'
        );
        CREATE TABLE IF NOT EXISTS tasks (
          id INTEGER PRIMARY KEY,
          project_id INTEGER NOT NULL,
          name TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'open'
        );
        """
    )
    cx.commit()
    cx.close()

def save_quote(form):
    photo_path = ""
    if "photo" in form:
        photo = form["photo"]
        if getattr(photo, "filename", None):
            dest = PHOTOS / f"quote_{int(time.time())}_{Path(photo.filename).name}"
            dest.write_bytes(photo.file.read())
            photo_path = str(dest)
    fields = {
        "name": form.getvalue("name", ""),
        "phone": form.getvalue("phone", ""),
        "email": form.getvalue("email", ""),
        "address": form.getvalue("address", ""),
        "work": form.getvalue("work", ""),
        "notes": form.getvalue("notes", ""),
        "photo": photo_path,
    }
    cx = sqlite3.connect(DB)
    cur = cx.execute(
        "INSERT INTO quotes(name,phone,email,address,work,notes,photo) VALUES (?,?,?,?,?,?,?)",
        (fields["name"], fields["phone"], fields["email"],
         fields["address"], fields["work"], fields["notes"], fields["photo"]),
    )
    qid = cur.lastrowid
    title = f"Quote {qid} — {fields['address'] or fields['name']}"
    p = cx.execute("INSERT INTO projects(name,status) VALUES (?, 'open')", (title,))
    pid = p.lastrowid
    for t in ("site-walk", "bid", "haul", "surplus log"):
        cx.execute("INSERT INTO tasks(project_id,name) VALUES (?,?)", (pid, t))
    cx.execute(
        "INSERT INTO events(kind, project_id, payload) VALUES ('quote_in', ?, ?)",
        (pid, json.dumps({"quote_id": qid, **fields})),
    )
    cx.commit()
    cx.close()
    return qid, pid

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/quotes":
            cx = sqlite3.connect(DB)
            cx.row_factory = sqlite3.Row
            rows = [dict(r) for r in cx.execute(
                "SELECT id,created_at,name,phone,address,work,status FROM quotes ORDER BY id DESC"
            )]
            body = json.dumps(rows, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
            return
        path = PAGES.get(self.path)
        if not path or not path.exists():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/quote":
            self.send_error(404)
            return
        env = {
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": self.headers.get("Content-Type"),
            "CONTENT_LENGTH": self.headers.get("Content-Length"),
        }
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ=env)
        qid, pid = save_quote(form)
        body = f"saved quote {qid} as project {pid}\n".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(fmt % args)

if __name__ == "__main__":
    init()
    print("Safari: http://127.0.0.1:8000/")
    ThreadingHTTPServer(("0.0.0.0", 8000), H).serve_forever()
