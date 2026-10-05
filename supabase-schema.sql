-- TubeLens — Supabase (Postgres) schema
-- Cara pakai: Supabase Dashboard → SQL Editor → paste seluruh file → Run.
-- Crawler (GitHub Actions) pakai SERVICE_ROLE key → bypass RLS, bisa tulis.
-- Frontend (Vercel) pakai ANON key → hanya bisa baca (RLS).

-- ============ TABLES ============

create table if not exists niches (
  id bigint generated always as identity primary key,
  name text not null,
  slug text unique not null,
  seed_keywords text,
  created_at timestamptz default now()
);

create table if not exists channels (
  id bigint generated always as identity primary key,
  channel_id text unique not null,
  title text,
  niche_id bigint references niches(id),
  subs bigint,
  country text default 'ID',
  last_crawled_at timestamptz,
  created_at timestamptz default now()
);
create index if not exists idx_channels_niche on channels(niche_id);

create table if not exists videos (
  id bigint generated always as identity primary key,
  video_id text unique not null,
  channel_id text not null,
  title text,
  description text,
  thumbnail_url text,
  published_at timestamptz,
  duration_seconds integer,
  created_at timestamptz default now()
);
create index if not exists idx_videos_channel on videos(channel_id);
create index if not exists idx_videos_published on videos(published_at desc);

create table if not exists video_stats (
  id bigint generated always as identity primary key,
  video_id text not null,
  views bigint,
  likes bigint,
  comments bigint,
  crawled_at timestamptz default now()
);
create index if not exists idx_stats_video on video_stats(video_id);
create index if not exists idx_stats_crawled on video_stats(crawled_at desc);

create table if not exists outlier_scores (
  video_id text primary key,
  channel_median_views double precision,
  outlier_score double precision,
  views_per_day double precision,
  computed_at timestamptz default now()
);

create table if not exists ai_analysis (
  id bigint generated always as identity primary key,
  video_id text not null,
  analysis_type text not null,
  result text not null,
  model text,
  created_at timestamptz default now(),
  unique(video_id, analysis_type)
);

-- ============ VIEWS (dipakai frontend) ============

-- Satu baris per video: stats terbaru + skor outlier. Frontend cukup query view ini.
create or replace view v_videos_full as
select v.video_id, v.title, v.thumbnail_url, v.published_at, v.duration_seconds,
       c.channel_id, c.title as channel_title,
       n.slug as niche_slug, n.name as niche_name,
       s.views, s.likes, s.comments,
       o.outlier_score, o.views_per_day, o.channel_median_views
from videos v
join channels c on c.channel_id = v.channel_id
join niches n on n.id = c.niche_id
left join lateral (
  select views, likes, comments from video_stats
  where video_id = v.video_id order by crawled_at desc limit 1
) s on true
left join outlier_scores o on o.video_id = v.video_id;

-- Statistik per niche (untuk dropdown filter)
create or replace view v_niche_stats as
select n.slug, n.name,
       count(distinct c.channel_id)::int as channels,
       count(v.video_id)::int as videos
from niches n
left join channels c on c.niche_id = n.id
left join videos v on v.channel_id = c.channel_id
group by n.id, n.slug, n.name
order by n.name;

-- ============ RLS: baca publik, tulis service_role saja ============

alter table niches enable row level security;
alter table channels enable row level security;
alter table videos enable row level security;
alter table video_stats enable row level security;
alter table outlier_scores enable row level security;
alter table ai_analysis enable row level security;

drop policy if exists "public read" on niches;
drop policy if exists "public read" on channels;
drop policy if exists "public read" on videos;
drop policy if exists "public read" on video_stats;
drop policy if exists "public read" on outlier_scores;
drop policy if exists "public read" on ai_analysis;

create policy "public read" on niches for select to anon using (true);
create policy "public read" on channels for select to anon using (true);
create policy "public read" on videos for select to anon using (true);
create policy "public read" on video_stats for select to anon using (true);
create policy "public read" on outlier_scores for select to anon using (true);
create policy "public read" on ai_analysis for select to anon using (true);

grant select on niches, channels, videos, video_stats, outlier_scores, ai_analysis to anon;
grant select on v_videos_full, v_niche_stats to anon;
