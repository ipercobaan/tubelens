# DEPLOY TubeLens — tanpa server, 100% gratis

Arsitektur: **Vercel** (web statis) + **Supabase** (database) + **GitHub Actions** (crawler harian).
Nggak ada server yang nyala terus. Semua gratis.

## 1. Supabase — database (10 menit)

1. Buka [supabase.com](https://supabase.com) → New Project (gratis).
2. Masuk ke **SQL Editor** → New Query.
3. Copy-paste seluruh isi `supabase-schema.sql` → **Run**.
   - Bikin tabel + view + RLS (baca publik, tulis cuma service_role).
4. Catat 3 hal dari **Project Settings → API**:
   - `Project URL` → mis. `https://xyz.supabase.co`
   - `anon public key` → untuk web
   - `service_role key` → untuk crawler (**RAHASIA**, jangan dipublikasi)

## 2. GitHub — crawler otomatis (10 menit)

1. Push folder `tubelens` ini jadi repo GitHub (public/private bebas).
2. Repo → **Settings → Secrets and variables → Actions** → tambah:
   - `SUPABASE_URL` = Project URL
   - `SUPABASE_SERVICE_KEY` = service_role key
3. Buka tab **Actions** → pilih **Daily Crawl** → **Run workflow** (manual, sekali).
   - Run pertama: seed channel + crawl + hitung outlier (~10 menit).
   - Cek hasilnya: Supabase → Table Editor → `videos` harusnya terisi.
4. Selanjutnya jalan otomatis tiap hari jam 02:00 WIB.

## 3. Vercel — web (5 menit)

1. Edit `web/index.html`, ganti 2 baris konfigurasi:
   ```js
   const SUPABASE_URL = "https://xyz.supabase.co";
   const SUPABASE_ANON_KEY = "eyJ...";   // anon key — aman dipublikasi (RLS yang jaga)
   ```
2. Buka [vercel.com](https://vercel.com) → Add New → Project → import repo GitHub.
   - **Root Directory**: `tubelens/web`
   - Framework Preset: Other. Build command: kosong. Output: default.
3. Deploy → jadi. Web langsung baca Supabase, tanpa backend.

## Catatan

- Tombol "Crawl" manual nggak ada di versi Vercel (serverless nggak bisa jalanin
  proses 7 menit). Crawl jalan otomatis via GitHub Actions tiap hari.
- Tambah niche baru: edit `NICHES` di `crawler_supa.py`, push → crawl berikutnya
  otomatis seed.
- Versi lokal (FastAPI + SQLite) tetap ada di folder ini buat development:
  `app.py`, `crawler.py`, `seed.py`, `score.py` — nggak dipakai produksi.
- Kalau nanti butuh auth/paywall: tambah Supabase Auth + cek di frontend
  sebelum render (tahap berikutnya).
