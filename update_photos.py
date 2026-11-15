"""
Update COFOCO database and application with high-resolution, premium editorial photography
for all 6 characters and 6 curated kits.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cofoco.db")

KIT_PHOTOS = {
    "kit_arjun_precision": "https://images.unsplash.com/photo-1598289431512-b97b0917affc?auto=format&fit=crop&w=1000&q=80",
    "kit_bheema_titan": "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=1000&q=80",
    "kit_karna_resolve": "https://images.unsplash.com/photo-1574680096145-d05b474e2155?auto=format&fit=crop&w=1000&q=80",
    "kit_sita_lotus": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?auto=format&fit=crop&w=1000&q=80",
    "kit_draupadi_sovereign": "https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=1000&q=80",
    "kit_savitri_habit": "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?auto=format&fit=crop&w=1000&q=80"
}

CHAR_PHOTOS = {
    "char_arjun": "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?auto=format&fit=crop&w=1000&q=80",
    "char_bheema": "https://images.unsplash.com/photo-1583454110551-21f2fa2afe61?auto=format&fit=crop&w=1000&q=80",
    "char_karna": "https://images.unsplash.com/photo-1517963879433-6ad2b056d712?auto=format&fit=crop&w=1000&q=80",
    "char_sita": "https://images.unsplash.com/photo-1506126613408-eca07ce68773?auto=format&fit=crop&w=1000&q=80",
    "char_draupadi": "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?auto=format&fit=crop&w=1000&q=80",
    "char_savitri": "https://images.unsplash.com/photo-1541534741688-6078c6bfb5c5?auto=format&fit=crop&w=1000&q=80"
}

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Update Kits
for kid, purl in KIT_PHOTOS.items():
    cur.execute("UPDATE kits SET image_url = ? WHERE id = ?;", (purl, kid))

# Update Characters
for cid, aurl in CHAR_PHOTOS.items():
    cur.execute("UPDATE characters SET artwork_url = ? WHERE id = ?;", (aurl, cid))

conn.commit()
conn.close()

print(f"[COFOCO] Successfully updated {len(KIT_PHOTOS)} kits and {len(CHAR_PHOTOS)} characters with high-resolution photography URLs.")
