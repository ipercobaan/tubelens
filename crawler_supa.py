"""TubeLens crawler versi Supabase (untuk GitHub Actions / tanpa server).

Env yang dibutuhkan:
  SUPABASE_URL         → https://xyz.supabase.co
  SUPABASE_SERVICE_KEY → service_role key (bypass RLS, untuk tulis)

Jalankan:  python crawler_supa.py [--max-videos N] [--stats-limit N]
Idempoten: aman dijalankan berulang. Seed channel otomatis jika niche masih sepi.
"""
import argparse
import feedparser
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone

from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
if not SUPABASE_URL or not SUPABASE_KEY:
    sys.exit("Set SUPABASE_URL dan SUPABASE_SERVICE_KEY dulu.")

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE = os.path.dirname(os.path.abspath(__file__))
YTDLP = os.path.join(BASE, ".venv", "bin", "yt-dlp")
if not os.path.exists(YTDLP):
    YTDLP = "yt-dlp"  # di GitHub Actions: yt-dlp dari pip ada di PATH

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


# ---------- seed ----------

def ytsearch_videos(query, n=10):
    try:
        out = subprocess.run(
            [YTDLP, f"ytsearch{n}:{query}", "--flat-playlist",
             "--print", "%(id)s|%(channel_id)s|%(channel)s", "--no-warnings"],
            capture_output=True, text=True, timeout=180,
        )
    except Exception as e:
        print("  ytsearch gagal:", e)
        return []
    rows = []
    for line in out.stdout.strip().splitlines():
        p = line.split("|")
        if len(p) >= 3 and p[1] and p[1] != "NA":
            rows.append((p[0], p[1], p[2]))
    return rows


def ensure_seed(max_channels=12):
    """Pastikan tiap niche punya channel. Jalan hanya jika masih sepi."""
    for slug, info in NICHES.items():
        sb.table("niches").upsert(
            {"name": info["name"], "slug": slug,
             "seed_keywords": ", ".join(info["keywords"])},
            on_conflict="slug",
        ).execute()
        niche = sb.table("niches").select("id").eq("slug", slug).single().execute().data
        rows = sb.table("channels").select("id").eq("niche_id", niche["id"]).execute().data
        n_ch = len(rows or [])
        if (n_ch or 0) >= 5:
            print(f"[{slug}] sudah ada {n_ch} channel, skip seed")
            continue
        seen, added = set(), 0
        for kw in info["keywords"]:
            print(f"[{slug}] cari: {kw}")
            for _vid, ch_id, ch_title in ytsearch_videos(kw):
                if ch_id in seen:
                    continue
                seen.add(ch_id)
                sb.table("channels").upsert(
                    {"channel_id": ch_id, "title": ch_title, "niche_id": niche["id"]},
                    on_conflict="channel_id",
                ).execute()
                added += 1
                if added >= max_channels:
                    break
            if added >= max_channels:
                break
        print(f"[{slug}] +{added} channel")


# ---------- crawl RSS ----------

def crawl_rss(max_videos=8):
    channels = sb.table("channels").select("id,channel_id,title").execute().data
    print(f"Crawl RSS: {len(channels)} channel")
    total = 0
    for ch in channels:
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={ch['channel_id']}"
        feed = feedparser.parse(url)
        n = 0
        for e in feed.entries[:max_videos]:
            vid = e.get("yt_videoid")
            if not vid:
                continue
            thumb = ""
            if e.get("media_thumbnail"):
                thumb = e["media_thumbnail"][0].get("url", "").replace("hqdefault", "mqdefault")
            pub = e.get("published", "") or None
            try:
                if pub:
                    pub = datetime.fromisoformat(pub.replace("Z", "+00:00")).isoformat()
            except Exception:
                pub = None
            sb.table("videos").upsert({
                "video_id": vid,
                "channel_id": ch["channel_id"],
                "title": (e.get("title", "") or "")[:500],
                "description": (e.get("summary", "") or "")[:500],
                "thumbnail_url": thumb,
                "published_at": pub,
            }, on_conflict="video_id").execute()
            n += 1
        sb.table("channels").update({"last_crawled_at": datetime.now(timezone.utc).isoformat()}) \
            .eq("id", ch["id"]).execute()
        total += n
        print(f"  {ch['title']}: {n} video")
    print(f"Total: {total} video")
    return total


# ---------- stats via yt-dlp ----------

def fetch_stats(video_id, timeout=60):
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
        return {"views": d.get("view_count") or 0,
                "likes": d.get("like_count") or 0,
                "comments": d.get("comment_count") or 0,
                "duration": d.get("duration") or 0}
    except Exception as e:
        print(f"  yt-dlp gagal {video_id}: {e}")
        return None


def crawl_stats(limit=100, sleep_s=1.0):
    all_vids = [r["video_id"] for r in
                sb.table("videos").select("video_id").execute().data]
    have = {r["video_id"] for r in
            sb.table("video_stats").select("video_id").execute().data}
    queue = [v for v in all_vids if v not in have][:limit]
    print(f"Stats: {len(queue)} video antri")
    ok = 0
    for vid in queue:
        st = fetch_stats(vid)
        if st:
            sb.table("video_stats").insert({
                "video_id": vid, "views": st["views"],
                "likes": st["likes"], "comments": st["comments"],
            }).execute()
            if st["duration"]:
                sb.table("videos").update({"duration_seconds": st["duration"]}) \
                    .eq("video_id", vid).execute()
            ok += 1
            print(f"  {vid}: {st['views']:,} views")
        time.sleep(sleep_s)
    print(f"Stats terisi: {ok}")
    return ok


# ---------- outlier scoring ----------

def compute_outliers(min_videos=3):
    videos = {r["video_id"]: r for r in
              sb.table("videos").select("video_id,channel_id,published_at").execute().data}
    # stats terbaru per video
    stats_rows = sb.table("video_stats") \
        .select("video_id,views,crawled_at").order("crawled_at", desc=True).execute().data
    latest = {}
    for r in stats_rows:
        if r["video_id"] not in latest and r["views"] is not None:
            latest[r["video_id"]] = r
    by_channel = {}
    for vid, s in latest.items():
        v = videos.get(vid)
        if v:
            by_channel.setdefault(v["channel_id"], []).append((vid, s["views"], v["published_at"]))
    n = 0
    now = datetime.now(timezone.utc)
    for _ch, items in by_channel.items():
        views = sorted(x[1] for x in items)
        if len(views) < min_videos:
            continue
        median = statistics.median(views) or 1
        for vid, vw, pub in items:
            vpd = None
            try:
                dt = datetime.fromisoformat(pub.replace("Z", "+00:00")) if pub else now
                days = max((now - dt).days, 1)
                vpd = round(vw / days, 1)
            except Exception:
                pass
            sb.table("outlier_scores").upsert({
                "video_id": vid,
                "channel_median_views": median,
                "outlier_score": round(vw / median, 2),
                "views_per_day": vpd,
            }, on_conflict="video_id").execute()
            n += 1
    print(f"Outlier scores: {n} video")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-videos", type=int, default=8)
    ap.add_argument("--stats-limit", type=int, default=100)
    ap.add_argument("--skip-seed", action="store_true")
    args = ap.parse_args()
    if not args.skip_seed:
        ensure_seed()
    crawl_rss(max_videos=args.max_videos)
    crawl_stats(limit=args.stats_limit)
    compute_outliers()
    print("SELESAI")


if __name__ == "__main__":
    main()
