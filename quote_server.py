#!/usr/bin/env python3
"""Local demo signup. Keep iSH in the foreground."""
import cgi
import json
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fulfill import links as fulfill_links
from stripe_pay import create_link, static_link
from takeoff import for_quote

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

def connect():
    cx = sqlite3.connect(DB)
    cx.row_factory = sqlite3.Row
    return cx

def init():
    cx = connect()
    cx.executescript(
        """
        CREATE TABLE IF NOT EXISTS quotes (
          id INTEGER PRIMARY KEY,
          created_at TEXT DEFAULT (datetime('now')),
          name TEXT, phone TEXT, email TEXT,
          address TEXT, work TEXT, notes TEXT,
          photo TEXT, status TEXT DEFAULT 'new',
          fulfilled_by TEXT,
          amount TEXT
        );
        CREATE TABLE IF NOT EXISTS clicks (
          id INTEGER PRIMARY KEY,
          quote_id INTEGER,
          dest TEXT,
          created_at TEXT DEFAULT (datetime('now'))
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
    cols = [r[1] for r in cx.execute("PRAGMA table_info(quotes)")]
    if "fulfilled_by" not in cols:
        cx.execute("ALTER TABLE quotes ADD COLUMN fulfilled_by TEXT")
    if "amount" not in cols:
        cx.execute("ALTER TABLE quotes ADD COLUMN amount TEXT")
    cx.commit()
    cx.close()

def cents_from(amount):
    try:
        return int(round(float(amount) * 100))
    except (TypeError, ValueError):
        return 0

def pay_block(qid):
    if static_link() or cents_from(_amount(qid)):
        return (
            '<a class="btn" href="/pay?qid=%s&to=direct">Pay my quote '
            "(Apple Pay / card)</a>" % qid
        )
    return '<p class="fine">Direct pay: set STRIPE_PAYMENT_LINK or STRIPE_SECRET_KEY.</p>'

def _amount(qid):
    cx = connect()
    row = cx.execute("SELECT amount FROM quotes WHERE id=?", (qid,)).fetchone()
    cx.close()
    return (row["amount"] if row else "") or ""

def _num(form, key):
    v = form.getvalue(key, "") or ""
    try:
        x = float(v)
        return x if x > 0 else None
    except (TypeError, ValueError):
        return None

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
        "amount": form.getvalue("amount", "") or "",
    }
    cx = connect()
    cur = cx.execute(
        "INSERT INTO quotes(name,phone,email,address,work,notes,photo,amount) VALUES (?,?,?,?,?,?,?,?)",
        (fields["name"], fields["phone"], fields["email"],
         fields["address"], fields["work"], fields["notes"], fields["photo"], fields["amount"]),
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
    bom = for_quote(
        qid,
        wall_ft=_num(form, "wall_ft"),
        wall_h=_num(form, "wall_h"),
        floor_w=_num(form, "floor_w"),
        floor_span=_num(form, "floor_span"),
    )
    return qid, pid, fields, bom

def log_click(qid, dest):
    dest = (dest or "")[:32]
    if dest not in ("taskrabbit", "fiverr", "direct"):
        return None
    cx = connect()
    work = ""
    amount = ""
    if qid:
        row = cx.execute("SELECT work, amount FROM quotes WHERE id=?", (qid,)).fetchone()
        if row:
            work = row["work"] or ""
            amount = row["amount"] or ""
        cx.execute("INSERT INTO clicks(quote_id, dest) VALUES (?,?)", (qid, dest))
        prev = cx.execute("SELECT fulfilled_by FROM quotes WHERE id=?", (qid,)).fetchone()
        old = (prev["fulfilled_by"] if prev and prev["fulfilled_by"] else "")
        parts = [p for p in old.split(",") if p]
        if dest not in parts:
            parts.append(dest)
        cx.execute("UPDATE quotes SET fulfilled_by=? WHERE id=?", (",".join(parts), qid))
    cx.commit()
    cx.close()
    if dest == "direct":
        return create_link(cents_from(amount), qid, work)
    urls = fulfill_links(work)
    return urls["tr_url"] if dest == "taskrabbit" else urls["fv_url"]

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
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _redirect(self, url):
        try:
            self.send_response(302)
            self.send_header("Location", url)
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        qs = parse_qs(u.query)
        print("GET", path)
        if path in ("/out", "/pay"):
            qid = (qs.get("qid") or [""])[0]
            dest = (qs.get("to") or ["direct" if path == "/pay" else ""])[0]
            if path == "/pay":
                dest = "direct"
            try:
                qid = int(qid)
            except ValueError:
                qid = 0
            url = log_click(qid, dest) or "/"
            return self._redirect(url)
        if path == "/quotes":
            cx = connect()
            rows = [dict(r) for r in cx.execute(
                "SELECT id,created_at,name,phone,address,work,status,fulfilled_by,amount FROM quotes ORDER BY id DESC"
            )]
            clicks = [dict(r) for r in cx.execute(
                "SELECT quote_id, dest, created_at FROM clicks ORDER BY id DESC LIMIT 50"
            )]
            cx.close()
            return self._send(200, json.dumps({"quotes": rows, "clicks": clicks}, indent=2), "application/json")
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
        qid, pid, fields, bom = save_quote(form)
        html = THANKS.format(
            qid=qid, pid=pid,
            work=fields.get("work") or "",
            address=fields.get("address") or "",
            pay_block=pay_block(qid),
            bom_block=bom or "",
        )
        return self._send(200, html, "text/html; charset=utf-8")

    def log_message(self, fmt, *args):
        print(fmt % args)

if __name__ == "__main__":
    init()
    print("Safari: http://127.0.0.1:8000/")
    print("Stripe:", "on" if static_link() else "set STRIPE_PAYMENT_LINK or STRIPE_SECRET_KEY")
    ThreadingHTTPServer(("0.0.0.0", 8000), H).serve_forever()
