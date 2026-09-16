#!/usr/bin/env python3
import io
import math
import sqlite3
import sys
from pathlib import Path

DB = str(Path(__file__).resolve().parent / "takeoff.db")

def _conn():
    return sqlite3.connect(DB)

def init(reset=False):
    c = _conn()
    if reset:
        c.executescript("DROP TABLE IF EXISTS catalog; DROP TABLE IF EXISTS line;")
    c.executescript("""
    CREATE TABLE IF NOT EXISTS catalog (
      sku TEXT PRIMARY KEY, name TEXT, category TEXT,
      length_ft REAL, coverage_sf REAL, waste_pct REAL, unit_cost REAL);
    CREATE TABLE IF NOT EXISTS line (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      job TEXT, sku TEXT, qty REAL, note TEXT);
    """)
    c.executemany("INSERT OR REPLACE INTO catalog VALUES (?,?,?,?,?,?,?)", [
        ("2x4-8", "2x4x8 stud/plate", "lumber", 8, None, 0.10, 3.48),
        ("2x4-10", "2x4x10", "lumber", 10, None, 0.10, 4.58),
        ("2x4-12", "2x4x12", "lumber", 12, None, 0.10, 5.48),
        ("2x6-12", "2x6x12 joist", "lumber", 12, None, 0.10, 9.98),
        ("2x10-12", "2x10x12 joist", "lumber", 12, None, 0.10, 16.48),
        ("OSB-7/16", "7/16 OSB 4x8", "sheet", None, 32, 0.15, 14.98),
        ("DW-1/2", "1/2 drywall 4x8", "sheet", None, 32, 0.15, 13.48),
    ])
    c.commit()
    c.close()

def _add(job, sku, qty, note=""):
    c = _conn()
    c.execute("INSERT INTO line(job,sku,qty,note) VALUES (?,?,?,?)", (job, sku, qty, note))
    c.commit()
    c.close()

def wall(length_ft, height_ft=8, oc_in=16, job="wall"):
    studs = math.ceil(length_ft * 12 / oc_in) + 1 + 2
    plates_8 = math.ceil(3 * length_ft / 8 * 1.10)
    area = length_ft * height_ft
    osb = math.ceil(area * 1.15 / 32)
    dw = math.ceil(area * 2 * 1.15 / 32)
    _add(job, "2x4-8", studs, "%sft wall studs" % length_ft)
    _add(job, "2x4-8", plates_8, "plates x3 +10%")
    _add(job, "OSB-7/16", osb, "sheathing")
    _add(job, "DW-1/2", dw, "drywall 2 sides")

def floor(width_ft, span_ft=12, oc_in=16, job="floor"):
    n = math.ceil(width_ft * 12 / oc_in) + 1
    sku = "2x10-12" if span_ft >= 12 else "2x6-12"
    sheets = math.ceil(width_ft * span_ft * 1.15 / 32)
    _add(job, sku, n, "%sft span %soc" % (span_ft, oc_in))
    _add(job, "OSB-7/16", sheets, "subfloor")

def bom_text(job=None):
    c = _conn()
    q = """SELECT l.job, l.sku, SUM(l.qty), c.unit_cost, SUM(l.qty)*c.unit_cost, GROUP_CONCAT(l.note,' | ')
           FROM line l JOIN catalog c ON c.sku=l.sku"""
    args = ()
    if job:
        q += " WHERE l.job=?"
        args = (job,)
    q += " GROUP BY l.job, l.sku"
    rows = c.execute(q, args).fetchall()
    c.close()
    if not rows:
        return ""
    lines = ["%s %s  qty %.0f  $%.2f" % (r[0], r[1], r[2], r[4]) for r in rows]
    total = sum(r[4] for r in rows)
    lines.append("TOTAL $%.2f  (catalog stand-in prices)" % total)
    return "\n".join(lines)

def bom(job=None):
    print(bom_text(job) or "(no lines)")

def for_quote(qid, wall_ft=None, wall_h=None, floor_w=None, floor_span=None):
    init()
    job = "q%s" % qid
    ran = False
    if wall_ft:
        wall(float(wall_ft), float(wall_h or 8), job=job)
        ran = True
    if floor_w:
        floor(float(floor_w), float(floor_span or 12), job=job)
        ran = True
    if not ran:
        return ""
    text = bom_text(job)
    return "<pre>%s</pre>" % text.replace("<", "") if text else ""

def clear():
    c = _conn()
    c.execute("DELETE FROM line")
    c.commit()
    c.close()

if __name__ == "__main__":
    init()
    clear()
    wall(24, 8)
    wall(16, 8)
    floor(16, 12)
    bom()
