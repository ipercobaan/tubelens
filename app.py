"""TubeLens API + UI statis."""
import os
import threading
from datetime import datetime

from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles

from db import get_conn

app = FastAPI(title="TubeLens")

BASE = os.path.dirname(os.path.abspath(__file__))

crawl_state = {"status": "idle", "started_at": None, "finished_at": None, "message": ""}


def _run_crawl(max_videos, stats_limit):
    from crawler import crawl_all
    from score import compute_outliers
    crawl_state.update(status="running", started_at=datetime.now().isoformat(),
                       finished_at=None, message="Crawl berjalan...")
    try:
        crawl_all(max_videos=max_videos, stats_limit=stats_limit)
        compute_outliers()
        crawl_state.update(status="done", message="Crawl selesai.")
    except Exception as e:  # noqa: BLE001
        crawl_state.update(status="error", message=f"Error: {e}")
    crawl_state["finished_at"] = datetime.now().isoformat()


@app.post("/api/crawl")
def trigger_crawl(max_videos: int = 8, stats_limit: int = 100):
    if crawl_state["status"] == "running":
        return {"ok": False, "message": "Crawl sedang berjalan, tunggu selesai."}
    t = threading.Thread(target=_run_crawl, args=(max_videos, stats_limit), daemon=True)
    t.start()
    return {"ok": True, "message": "Crawl dimulai di background."}


@app.get("/api/crawl/status")
def crawl_status():
    return crawl_state

VIDEO_SELECT = """
SELECT v.video_id, v.title, v.thumbnail_url, v.published_at, v.duration_seconds,
       c.title AS channel_title, c.channel_id, n.slug AS niche, n.name AS niche_name,
       s.views, s.likes, s.comments,
       o.outlier_score, o.views_per_day
FROM videos v
JOIN channels c ON c.channel_id = v.channel_id
JOIN niches n ON n.id = c.niche_id
LEFT JOIN video_stats s ON s.id = (SELECT MAX(id) FROM video_stats WHERE video_id = v.video_id)
LEFT JOIN outlier_scores o ON o.video_id = v.video_id
"""


@app.get("/api/niches")
def niches():
    conn = get_conn()
    rows = conn.execute(
        """SELECT n.slug, n.name, COUNT(DISTINCT c.channel_id) AS channels,
                  COUNT(v.video_id) AS videos
           FROM niches n
           LEFT JOIN channels c ON c.niche_id = n.id
           LEFT JOIN videos v ON v.channel_id = c.channel_id
           GROUP BY n.id ORDER BY n.name"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/videos")
def videos(
    niche: str = "",
    sort: str = Query("views", pattern="^(views|latest|outlier)$"),
    q: str = "",
    limit: int = 48,
):
    order = {"views": "s.views DESC", "latest": "v.published_at DESC",
             "outlier": "o.outlier_score DESC"}[sort]
    where, params = [], []
    if niche:
        where.append("n.slug = ?")
        params.append(niche)
    if q:
        where.append("v.title LIKE ?")
        params.append(f"%{q}%")
    sql = VIDEO_SELECT
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY {order} LIMIT ?"
    params.append(min(limit, 200))
    conn = get_conn()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/outliers")
def outliers(niche: str = "", min_score: float = 2.0, limit: int = 48):
    where = ["o.outlier_score >= ?"]
    params = [min_score]
    if niche:
        where.append("n.slug = ?")
        params.append(niche)
    sql = VIDEO_SELECT + " WHERE " + " AND ".join(where)
    sql += " ORDER BY o.outlier_score DESC LIMIT ?"
    params.append(min(limit, 200))
    conn = get_conn()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


app.mount("/", StaticFiles(directory=os.path.join(BASE, "static"), html=True), name="static")
