-- TubeLens (codename) — schema MVP
-- SQLite sekarang, portable ke Postgres/Supabase nanti.

CREATE TABLE IF NOT EXISTS niches (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  seed_keywords TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS channels (
  id INTEGER PRIMARY KEY,
  channel_id TEXT UNIQUE NOT NULL,
  title TEXT,
  niche_id INTEGER REFERENCES niches(id),
  subs INTEGER,
  country TEXT DEFAULT 'ID',
  last_crawled_at TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS videos (
  id INTEGER PRIMARY KEY,
  video_id TEXT UNIQUE NOT NULL,
  channel_id TEXT NOT NULL,
  title TEXT,
  description TEXT,
  thumbnail_url TEXT,
  published_at TEXT,
  duration_seconds INTEGER,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_videos_channel ON videos(channel_id);
CREATE INDEX IF NOT EXISTS idx_videos_published ON videos(published_at);

CREATE TABLE IF NOT EXISTS video_stats (
  id INTEGER PRIMARY KEY,
  video_id TEXT NOT NULL,
  views INTEGER,
  likes INTEGER,
  comments INTEGER,
  crawled_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_stats_video ON video_stats(video_id);

CREATE TABLE IF NOT EXISTS outlier_scores (
  video_id TEXT PRIMARY KEY,
  channel_median_views REAL,
  outlier_score REAL,
  views_per_day REAL,
  computed_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ai_analysis (
  id INTEGER PRIMARY KEY,
  video_id TEXT NOT NULL,
  analysis_type TEXT NOT NULL,
  result TEXT NOT NULL,
  model TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(video_id, analysis_type)
);
