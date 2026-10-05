"""Seed: cari channel Indonesia per niche via yt-dlp ytsearch (tanpa API key)."""
import os
import subprocess
import sys

from db import get_conn, init_db

BASE = os.path.dirname(os.path.abspath(__file__))
YTDLP = os.path.join(BASE, ".venv", "bin", "yt-dlp")
if not os.path.exists(YTDLP):
    YTDLP = "yt-dlp"  # fallback: pakai yang ada di PATH

NICHES = {
    "recap-film": {
        "name": "Recap Film",
        "keywords": ["alur cerita film indonesia", "recap film indonesia", "cerita film bioskop"],
    },
    "horor": {
        "name": "Horor & Misteri",
        "keywords": ["kisah horor indonesia", "cerita misteri indonesia", "penampakan hantu"],
    },
}


def ytsearch_videos(query, n=15):
    """Return list of (video_id, channel_id, channel_title)."""
    try:
        out = subprocess.run(
            [YTDLP, f"ytsearch{n}:{query}", "--flat-playlist",
             "--print", "%(id)s|%(channel_id)s|%(channel)s", "--no-warnings"],
            capture_output=True, text=True, timeout=180,
        )
    except Exception as e:
        print("ytsearch gagal:", e)
        return []
    rows = []
    for line in out.stdout.strip().splitlines():
        parts = line.split("|")
        if len(parts) >= 3 and parts[1] and parts[1] != "NA":
            rows.append((parts[0], parts[1], parts[2]))
    return rows


def seed(niche_slug=None, per_keyword=10, max_channels=12):
    init_db()
    conn = get_conn()
    for slug, info in NICHES.items():
        if niche_slug and slug != niche_slug:
            continue
        conn.execute(
            "INSERT OR IGNORE INTO niches(name, slug, seed_keywords) VALUES(?,?,?)",
            (info["name"], slug, ", ".join(info["keywords"])),
        )
        niche_id = conn.execute("SELECT id FROM niches WHERE slug=?", (slug,)).fetchone()["id"]
        seen = set()
        for kw in info["keywords"]:
            print(f"[{slug}] cari: {kw}")
            for vid, ch_id, ch_title in ytsearch_videos(kw, n=per_keyword):
                if ch_id in seen:
                    continue
                seen.add(ch_id)
                conn.execute(
                    """INSERT OR IGNORE INTO channels(channel_id, title, niche_id)
                       VALUES(?,?,?)""",
                    (ch_id, ch_title, niche_id),
                )
                if len(seen) >= max_channels:
                    break
            if len(seen) >= max_channels:
                break
        conn.commit()
        print(f"[{slug}] {len(seen)} channel tersimpan")
    conn.close()


if __name__ == "__main__":
    seed(sys.argv[1] if len(sys.argv) > 1 else None)
