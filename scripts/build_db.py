#!/usr/bin/env python3
"""
Build pipeline: apartamente_bucuresti.json → SQLite → docs/data/listings.json

Usage:
    python3 scripts/build_db.py          # build DB + export site data
    python3 scripts/build_db.py --serve   # build + start local server on :8080
"""

import json
import sqlite3
import os
import sys
import tempfile
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = ROOT / "data" / "apartamente_bucuresti.json"
DB_PATH = ROOT / "data" / "apartamente.db"
SITE_DATA_PATH = ROOT / "docs" / "data" / "listings.json"


def create_schema(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS listings (
            id TEXT PRIMARY KEY, price_eur INTEGER, area_mp REAL,
            price_per_mp INTEGER, zone TEXT, sub_zone TEXT, sector INTEGER,
            year_built INTEGER, floor TEXT, renovated TEXT, furnished TEXT,
            seismic_risk TEXT DEFAULT 'none', seismic_note TEXT, url TEXT,
            source TEXT DEFAULT 'storia', first_seen TEXT, last_seen TEXT,
            status TEXT DEFAULT 'active', notes TEXT
        );
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, listing_id TEXT NOT NULL,
            date TEXT NOT NULL, price_eur INTEGER NOT NULL,
            FOREIGN KEY (listing_id) REFERENCES listings(id),
            UNIQUE(listing_id, date)
        );
        CREATE TABLE IF NOT EXISTS eliminated (
            id TEXT PRIMARY KEY, price_eur INTEGER, area_mp REAL,
            zone TEXT, sub_zone TEXT, reason TEXT, year_built INTEGER,
            url TEXT, source TEXT DEFAULT 'storia', eliminated_date TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_zone ON listings(zone);
        CREATE INDEX IF NOT EXISTS idx_status ON listings(status);
        CREATE INDEX IF NOT EXISTS idx_price ON listings(price_eur);
        CREATE INDEX IF NOT EXISTS idx_ph ON price_history(listing_id);
    """)


def import_json(conn, data):
    cur = conn.cursor()
    for l in data.get("listings", []):
        cur.execute(
            "INSERT OR REPLACE INTO listings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (l["id"], l.get("price_eur"), l.get("area_mp"), l.get("price_per_mp"),
             l.get("zone", ""), l.get("sub_zone", ""), l.get("sector"),
             l.get("year_built"), l.get("floor"), l.get("renovated"),
             l.get("furnished"), l.get("seismic_risk", "none"),
             l.get("seismic_note"), l.get("url"), "storia",
             l.get("first_seen"), l.get("last_seen"),
             l.get("status", "active"), l.get("notes")))
        for ph in l.get("price_history", []):
            price = ph.get("price") or ph.get("new_price")
            if price:
                cur.execute(
                    "INSERT OR IGNORE INTO price_history (listing_id, date, price_eur) VALUES (?,?,?)",
                    (l["id"], ph["date"], price))

    for e in data.get("eliminated", []):
        cur.execute(
            "INSERT OR REPLACE INTO eliminated VALUES (?,?,?,?,?,?,?,?,?,?)",
            (e["id"], e.get("price_eur"), e.get("area_mp"),
             e.get("zone", ""), e.get("sub_zone", ""),
             e.get("reason", ""), e.get("year_built"), e.get("url"),
             "storia", None))
    conn.commit()
    print(f"Imported: {len(data.get('listings', []))} listings, "
          f"{len(data.get('eliminated', []))} eliminated")


def export_site_data(conn):
    cur = conn.cursor()
    cur.execute("""SELECT id, price_eur, area_mp, price_per_mp, zone, sub_zone,
        sector, seismic_risk, url, source, first_seen, last_seen, status, notes
        FROM listings WHERE status='active' ORDER BY price_per_mp""")
    cols = [d[0] for d in cur.description]
    active = [dict(zip(cols, r)) for r in cur.fetchall()]

    for listing in active:
        cur.execute("SELECT date, price_eur FROM price_history WHERE listing_id=? ORDER BY date",
                    (listing["id"],))
        listing["price_history"] = [{"date": r[0], "price": r[1]} for r in cur.fetchall()]
        ph = listing["price_history"]
        if len(ph) >= 2:
            listing["price_change"] = ph[-1]["price"] - ph[-2]["price"]
            listing["price_change_pct"] = round(
                (ph[-1]["price"] - ph[-2]["price"]) / ph[-2]["price"] * 100, 1)
        else:
            listing["price_change"] = 0
            listing["price_change_pct"] = 0

    cur.execute("SELECT id,price_eur,area_mp,zone,sub_zone,reason,year_built,url,source,eliminated_date FROM eliminated ORDER BY zone")
    elim_cols = [d[0] for d in cur.description]
    eliminated = [dict(zip(elim_cols, r)) for r in cur.fetchall()]

    cur.execute("SELECT COUNT(*) FROM listings WHERE status='active'")
    total_active = cur.fetchone()[0]
    cur.execute("SELECT MIN(price_eur),MAX(price_eur),ROUND(AVG(price_eur)) FROM listings WHERE status='active'")
    pmin, pmax, pavg = cur.fetchone()
    cur.execute("SELECT zone,COUNT(*) FROM listings WHERE status='active' GROUP BY zone ORDER BY COUNT(*) DESC")
    zones = [{"zone": r[0], "count": r[1]} for r in cur.fetchall()]

    site_data = {
        "generated": "",
        "stats": {"active": total_active, "price_min": pmin, "price_max": pmax,
                  "price_avg": int(pavg or 0), "zones": len(zones)},
        "zone_distribution": zones,
        "listings": active,
        "eliminated": eliminated
    }

    os.makedirs(SITE_DATA_PATH.parent, exist_ok=True)
    with open(SITE_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(site_data, f, ensure_ascii=False, indent=2)
    print(f"Exported: {len(active)} active, {len(eliminated)} eliminated → {SITE_DATA_PATH}")


def main():
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    # Build SQLite in temp dir (avoids locking issues on some mounts),
    # then copy to final location
    tmp_db = os.path.join(tempfile.gettempdir(), "apartamente_build.db")
    if os.path.exists(tmp_db):
        os.remove(tmp_db)

    conn = sqlite3.connect(tmp_db)
    create_schema(conn)
    import_json(conn, data)
    export_site_data(conn)
    conn.close()

    shutil.copy2(tmp_db, str(DB_PATH))
    os.remove(tmp_db)
    print(f"\nDone! DB at {DB_PATH}")

    if "--serve" in sys.argv:
        import http.server
        os.chdir(str(ROOT / "docs"))
        print("\nServing at http://localhost:8080")
        http.server.HTTPServer(("", 8080), http.server.SimpleHTTPRequestHandler).serve_forever()


if __name__ == "__main__":
    main()
