#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import cgi
import json
import sqlite3
import time

ROOT = Path(__file__).resolve().parent
PHOTOS = ROOT / "photos"
PHOTOS.mkdir(exist_ok=True)
HTML = (ROOT / "static" / "log.html").read_bytes()
DB = ROOT / "projects.db"

def init_db():
    cx = sqlite3.connect(DB)
    cx.executescript(
        """
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY,
          kind TEXT,
          project_id INTEGER,
          payload TEXT
        );
        """
    )
    cx.commit()
    cx.close()

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/log.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML)
            return
        self.send_error(404)

    def do_POST(self):
        if self.path != "/log":
            self.send_error(404)
            return
        env = {
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": self.headers.get("Content-Type"),
            "CONTENT_LENGTH": self.headers.get("Content-Length"),
        }
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ=env)
        pid = form.getvalue("project_id", "1")
        task = form.getvalue("task", "") or ""
        notes = form.getvalue("notes", "") or ""
        path = ""
        if "photo" in form:
            photo = form["photo"]
            if getattr(photo, "filename", None):
                dest = PHOTOS / f"{int(time.time())}_{Path(photo.filename).name}"
                dest.write_bytes(photo.file.read())
                path = str(dest)
        payload = json.dumps({"task": task, "notes": notes, "photo": path})
        cx = sqlite3.connect(DB)
        cx.execute(
            "INSERT INTO events(kind, project_id, payload) VALUES (?,?,?)",
            ("job_log", pid, payload),
        )
        cx.commit()
        cx.close()
        body = b"saved\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(fmt % args)

if __name__ == "__main__":
    init_db()
    print("open Safari: http://127.0.0.1:8000/")
    ThreadingHTTPServer(("0.0.0.0", 8000), H).serve_forever()
