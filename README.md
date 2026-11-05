# AutoAnalytica v2.0 — AI Data Analyst & BI Dashboard

Unggah Excel/CSV → dashboard interaktif + insight bisnis otomatis, tanpa coding.
Implementasi PRD v2.0 (4 fase) dengan **Next.js 15 + Tailwind**, **Supabase** (Auth/Storage/Postgres), dan **Python FastAPI + Pandas**.

```
autoanalytica/
├─ frontend/        Next.js 15 (App Router) + Tailwind 3 + ECharts
├─ backend/         FastAPI: cleaning, profiling, rules engine, query, AI
├─ supabase/        schema.sql (tabel, RLS, bucket datasets-raw)
├─ sample_data/     penjualan_contoh.csv untuk uji coba
└─ docker-compose.yml
```

## Cakupan fitur vs PRD

| Fase | Fitur | Lokasi |
|---|---|---|
| 1 Ingestion | Dropzone .xlsx/.xls/.csv ≤ 50MB, upload langsung ke bucket `datasets-raw`, Auth | `frontend/src/components/Dropzone.tsx`, `supabase/schema.sql` |
| 1 | Auto cleaning: inferensi tipe (Categorical/Quantitative/Datetime), angka format Indonesia (`Rp 1.234.567,89`), missing values, duplikat, header bergeser | `backend/app/cleaning.py` |
| 1 | Auto Data Profiling | `backend/app/profiling.py` |
| 2 Analytics | Smart Chart Recommender (aturan PRD §4: Line / Donut ≤5 / Bar-H >5 / Scatter / Waterfall) | `backend/app/recommender.py` |
| 2 | KPI Cards: Total Omset, Transaction Count, Avg Ticket, Growth Rate | `backend/app/kpi.py` |
| 2 | Executive Narrative (AI Gemini/OpenAI, fallback aturan) | `backend/app/ai.py` |
| 3 Studio | Chart Switcher 1 klik, tukar sumbu X/Y, agregasi SUM/AVG/COUNT (+MIN/MAX), Top N, judul | `Studio.tsx`, `ChartCard.tsx` |
| 3 | Global Slicer (rentang tanggal + kategori) | `FilterBar.tsx` |
| 3 | **Ask My Data** (teks natural → spec grafik → jawaban), sematkan ke dashboard | `AskMyData.tsx`, `/api/ask` |
| 4 Export | PDF A4 print-ready, PNG 3x & SVG per grafik | `frontend/src/lib/export.ts` |
| 4 | Shareable link read-only (token acak, kedaluwarsa opsional, dapat dicabut) | `ShareDialog.tsx`, `/api/share/*` |

Target performa PRD §6 diuji otomatis (`backend/tests`): dashboard awal ≤ 8 dtk untuk 100.000 baris, query ganti tipe/filter ≤ 300 ms.

## Setup (±15 menit)

### 1. Supabase
1. Buat project di <https://supabase.com> (paket gratis cukup).
2. **SQL Editor** → tempel isi `supabase/schema.sql` → **Run** (membuat 4 tabel, RLS, trigger profile, dan bucket `datasets-raw` 50MB privat). Aman dijalankan ulang.
3. **Authentication → Providers → Email**: aktif. Untuk uji lokal cepat, matikan *Confirm email* (opsional).
4. Salin dari **Project Settings → API**: `Project URL`, `anon public key`, dan `service_role key`.

### 2. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # isi SUPABASE_URL & SUPABASE_SERVICE_ROLE_KEY (+ GEMINI_API_KEY opsional)
uvicorn app.main:app --reload --port 8000
pytest -q tests             # opsional: jalankan tes
```
Cek `http://localhost:8000/health`.

### 3. Frontend
```bash
cd frontend
cp .env.example .env.local   # isi URL & anon key Supabase, NEXT_PUBLIC_API_URL
npm install
npm run dev                  # http://localhost:3000
```
Daftar akun → unggah `sample_data/penjualan_contoh.csv` → dashboard terbuka otomatis.

### Docker (opsional)
Buat `.env` di root berisi `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL`, isi `backend/.env`, lalu `docker compose up --build`.

## Alur data & keamanan

- Browser mengunggah file **langsung ke Supabase Storage** (folder `<user_id>/…`, dibatasi RLS storage). Dataset/dashboard/chart dibatasi RLS per user.
- Backend memvalidasi JWT user ke Supabase Auth, memeriksa kepemilikan dataset, lalu mengunduh file dengan service-role key (**tidak pernah ke browser**).
- DataFrame bersih di-cache di memori (LRU, `CACHE_SIZE`) agar interaksi Studio cepat; jika cache hilang, file diunduh & diproses ulang otomatis.
- **Privasi AI:** hanya statistik teragregasi (KPI, top kategori, tren) yang dikirim ke Gemini/OpenAI — bukan baris data mentah. Tanpa API key, semuanya tetap jalan memakai mesin aturan.
- Link share dilayani backend lewat token acak (24 byte); tabel tetap privat. Link bisa kedaluwarsa dan dicabut. Pemilik link hanya mendapat hasil agregasi, tanpa file asli.
- Enkripsi: TLS saat transit dan AES-256 at-rest disediakan Supabase (sesuai PRD §6).

## Penyimpangan kecil dari PRD (disengaja)

- Skema ditambah kolom bertanda `[+]` (mis. `dashboards.user_id`, `kpi_json`, `share_token`, `datasets.status`) — dibutuhkan untuk RLS, status proses, dan share link. Skema dijalankan lewat satu file SQL (sekali tempel) agar RLS & storage policy ikut terpasang; Table Editor visual tetap bisa dipakai untuk melihat/mengedit.
- Waterfall dipakai otomatis hanya bila terdeteksi kolom pendapatan **dan** biaya (nama kolom mengandung kata seperti omset/revenue dan hpp/biaya/cost). Untuk keuangan lain, ubah lewat Studio.
- Jika kolom angka kosong (missing), nilainya **dilewati** saat agregasi (tidak diisi median) agar total tidak terdistorsi; kolom kategori kosong diisi "Tidak Diketahui". Laporan pembersihan tersimpan di `datasets.schema_json.cleaning`.
- Model Gemini default `gemini-2.5-flash`; ubah lewat `GEMINI_MODEL` bila nama model berubah. Verifikasi di dokumentasi penyedia sebelum produksi.

## Batasan yang perlu diketahui

- Aplikasi ini sudah lolos tes backend otomatis dan `next build`, tetapi **belum diuji end-to-end terhadap project Supabase sungguhan** (butuh kredensial Anda). Langkah pertama yang disarankan: jalankan alur unggah → dashboard → Studio → share dengan data contoh.
- Cache DataFrame bersifat per-proses. Untuk produksi dengan banyak worker/instance, gunakan satu worker, sticky session, atau ganti `datastore.py` dengan cache bersama (mis. Redis/Parquet di storage).
- Rate limit "Ask My Data" in-memory per proses.
- Pembacaan Excel memilih sheet dengan sel terisi terbanyak; file multi-sheet kompleks mungkin perlu dipisah.
- Waterfall mengasumsikan saldo kumulatif tidak melewati nol.
- Deploy produksi disarankan: frontend di Vercel, backend di Render/Fly/Railway (set `FRONTEND_ORIGINS`), dan aktifkan konfirmasi email di Supabase.
