#!/usr/bin/env python3
import math
import sqlite3
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
    print("db ready:", DB)

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
    _add(job, "2x4-8", studs, f"{length_ft}ft wall studs")
    _add(job, "2x4-8", plates_8, "plates x3 +10%")
    _add(job, "OSB-7/16", osb, "sheathing")
    _add(job, "DW-1/2", dw, "drywall 2 sides")
    print(f"wall {length_ft}x{height_ft}: {studs} studs, {plates_8} plates, {osb} OSB, {dw} DW")

def floor(width_ft, span_ft=12, oc_in=16, job="floor"):
    n = math.ceil(width_ft * 12 / oc_in) + 1
    sku = "2x10-12" if span_ft >= 12 else "2x6-12"
    sheets = math.ceil(width_ft * span_ft * 1.15 / 32)
    _add(job, sku, n, f"{span_ft}ft span {oc_in}oc")
    _add(job, "OSB-7/16", sheets, "subfloor")
    print(f"floor {width_ft}x{span_ft}: {n} {sku}, {sheets} OSB")

def bom(job=None):
    c = _conn()
    q = """SELECT l.job, l.sku, SUM(l.qty), c.unit_cost, SUM(l.qty)*c.unit_cost, GROUP_CONCAT(l.note,' | ')
           FROM line l JOIN catalog c ON c.sku=l.sku"""
    args = ()
    if job:
        q += " WHERE l.job=?"
        args = (job,)
    q += " GROUP BY l.job, l.sku"
    rows = c.execute(q, args).fetchall()
    total = 0
    print(f"{'job':8} {'sku':10} {'qty':>6} {'$ea':>7} {'ext':>8}")
    for job, sku, qty, cost, ext, note in rows:
        total += ext
        print(f"{job:8} {sku:10} {qty:6.0f} {cost:7.2f} {ext:8.2f}  {note}")
    print(f"{'':8} {'':10} {'':6} {'TOTAL':>7} {total:8.2f}")
    c.close()

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
