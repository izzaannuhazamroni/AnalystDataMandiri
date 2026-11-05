-- =====================================================================
-- AutoAnalytica — Skema Supabase (PRD v2.0 §5)
-- Cara pakai: Supabase Dashboard → SQL Editor → paste seluruh file → Run.
-- Aman dijalankan ulang (idempotent).
-- Catatan: tabel mengikuti PRD; kolom tambahan ditandai [+] (dibutuhkan
-- untuk RLS, status proses, KPI, dan shareable link).
-- =====================================================================

create extension if not exists "pgcrypto";

-- profiles ------------------------------------------------------------
create table if not exists public.profiles (
  id          uuid primary key references auth.users(id) on delete cascade,
  email       text,
  full_name   text,
  created_at  timestamptz not null default now()
);

-- datasets ------------------------------------------------------------
create table if not exists public.datasets (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references public.profiles(id) on delete cascade,
  file_name     text not null,
  file_path     text not null,
  file_size     bigint,                                   -- [+]
  row_count     integer,
  col_count     integer,                                  -- [+]
  schema_json   jsonb,
  status        text not null default 'uploaded',         -- [+] uploaded|processing|ready|failed
  error_message text,                                     -- [+]
  created_at    timestamptz not null default now()
);
create index if not exists datasets_user_idx on public.datasets(user_id, created_at desc);

-- dashboards ----------------------------------------------------------
create table if not exists public.dashboards (
  id                uuid primary key default gen_random_uuid(),
  dataset_id        uuid not null references public.datasets(id) on delete cascade,
  user_id           uuid not null references public.profiles(id) on delete cascade,  -- [+]
  title             text,
  summary_text      text,
  kpi_json          jsonb,                                -- [+]
  share_token       text unique,                          -- [+] shareable link read-only
  share_expires_at  timestamptz,                          -- [+]
  created_at        timestamptz not null default now()
);
create index if not exists dashboards_dataset_idx on public.dashboards(dataset_id);

-- charts --------------------------------------------------------------
create table if not exists public.charts (
  id             uuid primary key default gen_random_uuid(),
  dashboard_id   uuid not null references public.dashboards(id) on delete cascade,
  chart_type     text not null,
  x_axis         text,
  y_axis         text,
  aggregation    text not null default 'SUM',
  styling_json   jsonb not null default '{}'::jsonb,
  position       integer not null default 0               -- [+]
);
create index if not exists charts_dashboard_idx on public.charts(dashboard_id, position);

-- Row Level Security ----------------------------------------------------
alter table public.profiles   enable row level security;
alter table public.datasets   enable row level security;
alter table public.dashboards enable row level security;
alter table public.charts     enable row level security;

drop policy if exists "profiles_own" on public.profiles;
create policy "profiles_own" on public.profiles
  for all to authenticated using (auth.uid() = id) with check (auth.uid() = id);

drop policy if exists "datasets_own" on public.datasets;
create policy "datasets_own" on public.datasets
  for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "dashboards_own" on public.dashboards;
create policy "dashboards_own" on public.dashboards
  for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "charts_own" on public.charts;
create policy "charts_own" on public.charts
  for all to authenticated
  using (exists (select 1 from public.dashboards d where d.id = charts.dashboard_id and d.user_id = auth.uid()))
  with check (exists (select 1 from public.dashboards d where d.id = charts.dashboard_id and d.user_id = auth.uid()));

-- Akses publik (share link) TIDAK lewat RLS: dilayani backend FastAPI
-- (service role) dengan token acak read-only, sehingga tabel tetap privat.

-- Auto-create profile saat user mendaftar ---------------------------------
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email, full_name)
  values (new.id, new.email, new.raw_user_meta_data->>'full_name')
  on conflict (id) do nothing;
  return new;
end; $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Backfill untuk user yang sudah ada sebelum trigger dibuat
insert into public.profiles (id, email)
select id, email from auth.users
on conflict (id) do nothing;

-- Storage bucket: datasets-raw (private, maks 50MB) ---------------------------
insert into storage.buckets (id, name, public, file_size_limit)
values ('datasets-raw', 'datasets-raw', false, 52428800)
on conflict (id) do update set file_size_limit = excluded.file_size_limit, public = false;

-- File disimpan di folder "<user_id>/..." — user hanya akses foldernya sendiri
drop policy if exists "datasets_raw_insert" on storage.objects;
create policy "datasets_raw_insert" on storage.objects
  for insert to authenticated
  with check (bucket_id = 'datasets-raw' and (storage.foldername(name))[1] = auth.uid()::text);

drop policy if exists "datasets_raw_select" on storage.objects;
create policy "datasets_raw_select" on storage.objects
  for select to authenticated
  using (bucket_id = 'datasets-raw' and (storage.foldername(name))[1] = auth.uid()::text);

drop policy if exists "datasets_raw_delete" on storage.objects;
create policy "datasets_raw_delete" on storage.objects
  for delete to authenticated
  using (bucket_id = 'datasets-raw' and (storage.foldername(name))[1] = auth.uid()::text);
