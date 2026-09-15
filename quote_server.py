#!/usr/bin/env python3
"""Local demo signup. Keep iSH in the foreground."""
import cgi
import json
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from fulfill import links as fulfill_links

ROOT = Path(__file__).resolve().parent
PHOTOS = ROOT / "photos"
PHOTOS.mkdir(exist_ok=True)
DB = ROOT / "projects.db"
THANKS = (ROOT / "static" / "thanks.html").read_text()
PAGES = {
    "/": ROOT / "static" / "quote.html",
    "/quote": ROOT / "static" / "quote.html",
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
          name TEXT, phone TEXT, email TEXT,
          address TEXT, work TEXT, notes TEXT,
          photo TEXT, status TEXT DEFAULT 'new'
        );
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY,
          kind TEXT, project_id INTEGER, payload TEXT
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
        "name": form.getvalue("name", "") or "",
        "phone": form.getvalue("phone", "") or "",
        "email": form.getvalue("email", "") or "",
        "address": form.getvalue("address", "") or "",
        "work": form.getvalue("work", "") or "",
        "notes": form.getvalue("notes", "") or "",
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
    return qid, pid, fields

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="text/plain"):
        if isinstance(body, str):
            body = body.encode()
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except BrokenPipeError:
            pass
        except ConnectionResetError:
            pass

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        print("GET", path)
        if path == "/quotes":
            cx = sqlite3.connect(DB)
            cx.row_factory = sqlite3.Row
            rows = [dict(r) for r in cx.execute(
                "SELECT id,created_at,name,phone,address,work,status FROM quotes ORDER BY id DESC"
            )]
            cx.close()
            return self._send(200, json.dumps(rows, indent=2), "application/json")
        page = PAGES.get(path)
        if not page or not page.exists():
            return self._send(404, "not found\n")
        return self._send(200, page.read_bytes(), "text/html; charset=utf-8")

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        print("POST", path)
        if path not in ("/", "/quote", "/quote.html", "/log"):
            return self._send(404, "post %s not found\n" % path)
        env = {
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
        }
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ=env)
        qid, pid, fields = save_quote(form)
        urls = fulfill_links(fields.get("work"))
        html = THANKS.format(
            qid=qid, pid=pid,
            work=fields.get("work") or "",
            address=fields.get("address") or "",
            **urls,
        )
        return self._send(200, html, "text/html; charset=utf-8")

    def log_message(self, fmt, *args):
        print(fmt % args)

if __name__ == "__main__":
    init()
    print("Safari: http://127.0.0.1:8000/")
    ThreadingHTTPServer(("0.0.0.0", 8000), H).serve_forever()
