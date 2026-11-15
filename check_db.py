import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "cofoco.db")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("--- KITS ---")
for k in cur.execute("SELECT id, name, image_url FROM kits").fetchall():
    print(k["id"], k["name"], k["image_url"])

print("\n--- CHARACTERS ---")
for c in cur.execute("SELECT id, name, artwork_url FROM characters").fetchall():
    print(c["id"], c["name"], c["artwork_url"])

conn.close()

