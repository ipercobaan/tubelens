"""Outlier scoring: skor = views video / median views channel."""
import statistics

from db import get_conn


def compute_outliers(min_videos=3):
    conn = get_conn()
    # stats terbaru per video
    stats = conn.execute(
        """SELECT v.video_id, v.channel_id, s.views, v.published_at
           FROM videos v
           JOIN video_stats s ON s.video_id = v.video_id
           WHERE s.id IN (SELECT MAX(id) FROM video_stats GROUP BY video_id)
             AND s.views IS NOT NULL"""
    ).fetchall()

    by_channel = {}
    for r in stats:
        by_channel.setdefault(r["channel_id"], []).append(r)

    n = 0
    for ch_id, vids in by_channel.items():
        views = sorted(r["views"] for r in vids)
        if len(views) < min_videos:
            continue
        median = statistics.median(views) or 1
        for r in vids:
            score = r["views"] / median
            # views per day
            vpd = None
            try:
                from datetime import datetime, timezone
                pub = datetime.fromisoformat(r["published_at"].replace("Z", "+00:00"))
                days = max((datetime.now(timezone.utc) - pub).days, 1)
                vpd = r["views"] / days
            except Exception:
                pass
            conn.execute(
                """INSERT INTO outlier_scores(video_id, channel_median_views, outlier_score, views_per_day)
                   VALUES(?,?,?,?)
                   ON CONFLICT(video_id) DO UPDATE SET
                     channel_median_views=excluded.channel_median_views,
                     outlier_score=excluded.outlier_score,
                     views_per_day=excluded.views_per_day,
                     computed_at=datetime('now')""",
                (r["video_id"], median, round(score, 2), round(vpd, 1) if vpd else None),
            )
            n += 1
    conn.commit()
    conn.close()
    print(f"Outlier scores dihitung: {n} video")
    return n


if __name__ == "__main__":
    compute_outliers()
