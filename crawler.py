"""Crawler: RSS (deteksi upload, gratis tanpa API key) + yt-dlp (statistik views/likes)."""
import feedparser
import json
import os
import subprocess
import sys
import time

from db import get_conn, init_db

BASE = os.path.dirname(os.path.abspath(__file__))
YTDLP = os.path.join(BASE, ".venv", "bin", "yt-dlp")
if not os.path.exists(YTDLP):
    YTDLP = "yt-dlp"  # fallback: pakai yang ada di PATH


def fetch_rss(channel_id):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    return feedparser.parse(url)


def crawl_channel_rss(channel_row, max_videos=15):
    """Ambil video terbaru channel dari RSS, simpan ke DB. Return jumlah video baru."""
    feed = fetch_rss(channel_row["channel_id"])
    if feed.bozo and not feed.entries:
        print(f"  RSS gagal: {channel_row['title']}")
        return 0
    conn = get_conn()
    cur = conn.cursor()
    new = 0
    for e in feed.entries[:max_videos]:
        vid = e.get("yt_videoid")
        if not vid:
            continue
        thumb = ""
        if e.get("media_thumbnail"):
            thumb = e["media_thumbnail"][0].get("url", "")
        # thumbnail resolusi lebih besar
        thumb = thumb.replace("hqdefault", "mqdefault")
        cur.execute(
            """INSERT INTO videos(video_id, channel_id, title, description, thumbnail_url, published_at)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(video_id) DO UPDATE SET
                 title=excluded.title, thumbnail_url=excluded.thumbnail_url""",
            (vid, channel_row["channel_id"], e.get("title", "") or "",
             (e.get("summary", "") or "")[:500], thumb, e.get("published", "") or ""),
        )
        if cur.rowcount:
            new += 1
    cur.execute("UPDATE channels SET last_crawled_at=datetime('now') WHERE id=?",
                (channel_row["id"],))
    conn.commit()
    conn.close()
    return new


def fetch_stats_ytdlp(video_id, timeout=60):
    """Ambil views/likes/comments/duration via yt-dlp (tanpa API key)."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        out = subprocess.run(
            [YTDLP, "--skip-download", "--dump-single-json", "--no-warnings",
             "--extractor-args", "youtube:player_client=android", url],
            capture_output=True, text=True, timeout=timeout,
        )
        if out.returncode != 0:
            return None
        d = json.loads(out.stdout)
        return {
            "views": d.get("view_count") or 0,
            "likes": d.get("like_count") or 0,
            "comments": d.get("comment_count") or 0,
            "duration": d.get("duration") or 0,
        }
    except Exception as e:
        print(f"  yt-dlp gagal {video_id}: {e}")
        return None


def crawl_stats(limit=80, sleep_s=1.0):
    """Isi statistik untuk video yang belum punya stats (atau refresh)."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT v.video_id FROM videos v
           LEFT JOIN video_stats s ON s.video_id = v.video_id
           WHERE s.id IS NULL
           ORDER BY v.published_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    print(f"Stats: {len(rows)} video antri")
    ok = 0
    for (vid,) in rows:
        st = fetch_stats_ytdlp(vid)
        if st:
            conn = get_conn()
            conn.execute(
                "INSERT INTO video_stats(video_id, views, likes, comments) VALUES(?,?,?,?)",
                (vid, st["views"], st["likes"], st["comments"]),
            )
            if st["duration"]:
                conn.execute("UPDATE videos SET duration_seconds=? WHERE video_id=?",
                             (st["duration"], vid))
            conn.commit()
            conn.close()
            ok += 1
            print(f"  {vid}: {st['views']:,} views")
        time.sleep(sleep_s)
    return ok


def crawl_all(max_videos=15, stats_limit=80):
    init_db()
    conn = get_conn()
    channels = conn.execute("SELECT * FROM channels").fetchall()
    conn.close()
    print(f"Crawl RSS: {len(channels)} channel")
    total_new = 0
    for ch in channels:
        n = crawl_channel_rss(ch, max_videos=max_videos)
        total_new += n
        print(f"  {ch['title']}: +{n} video")
    print(f"Total video baru: {total_new}")
    ok = crawl_stats(limit=stats_limit)
    print(f"Stats terisi: {ok}")


if __name__ == "__main__":
    max_v = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    lim = int(sys.argv[2]) if len(sys.argv) > 2 else 80
    crawl_all(max_videos=max_v, stats_limit=lim)
