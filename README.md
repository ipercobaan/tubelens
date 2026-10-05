# TubeLens (codename) — Tool Riset YouTube Indonesia

MVP: Galeri Viral (ala 1of10) + Radar Outlier (ala OutlierKit).
Modul berikutnya: Keyword Intel (ala ytRank) + Bedah AI (Gemini, BYOK).

## Cara jalanin (Windows / PC sendiri)

```bat
cd tubelens
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

python db.py        :: bikin database
python seed.py      :: cari channel Indonesia per niche (tanpa API key)
python crawler.py   :: crawl RSS + statistik views (tanpa API key)
python score.py     :: hitung skor outlier

uvicorn app:app --host 127.0.0.1 --port 8000
:: buka http://127.0.0.1:8000
:: tombol "🔄 Crawl" di web menjalankan crawler langsung (POST /api/crawl)
```

Jadwal harian (opsional, tanpa buka web):
```bat
python crawler.py && python score.py
```

## File penting

| File | Fungsi |
|---|---|
| `schema.sql` / `db.py` | Database SQLite (gampang pindah ke Supabase/Postgres) |
| `seed.py` | Cari channel per niche via yt-dlp `ytsearch` |
| `crawler.py` | Ambil video baru via RSS (gratis, tanpa kuota) + stats views via yt-dlp |
| `score.py` | Skor outlier = views video / median views channel |
| `app.py` | API + web UI |
| `static/index.html` | UI Galeri Viral & Radar Outlier |

## Catatan teknis

- RSS YouTube publik & gratis — deteksi upload baru tanpa makan kuota API.
- Stats via yt-dlp pakai `player_client=android` (mengakali bot-check YouTube).
- Kalau nanti punya YouTube Data API key, ganti `fetch_stats_ytdlp` dengan API
  resmi (lebih cepat & stabil, 1 unit kuota per 50 video).
- Tabel `ai_analysis` sudah disiapkan untuk cache hasil Bedah AI (Gemini BYOK).

## Upgrade path produksi

1. Pindah DB ke Supabase Postgres (skema sudah kompatibel).
2. Crawler jadi cron harian (saat ini manual via `crawler.py`).
3. Tambah Modul Keyword Intel + Bedah AI.
4. Auth + payment (lihat pola MANMETHOD: upload bukti / Midtrans).
