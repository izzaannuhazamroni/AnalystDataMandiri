"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, FileSpreadsheet, Loader2, RefreshCw, Trash2 } from "lucide-react";
import Dropzone from "@/components/Dropzone";
import { api } from "@/lib/api";
import { BUCKET, getSupabase } from "@/lib/supabase";

interface DatasetRow {
  id: string;
  file_name: string;
  file_path: string;
  row_count: number | null;
  status: "uploaded" | "processing" | "ready" | "failed";
  error_message: string | null;
  created_at: string;
  dashboards: { id: string }[];
}

const STATUS: Record<DatasetRow["status"], { label: string; cls: string }> = {
  uploaded: { label: "Diunggah", cls: "bg-slate-100 text-slate-600" },
  processing: { label: "Memproses", cls: "bg-amber-100 text-amber-700" },
  ready: { label: "Siap", cls: "bg-emerald-100 text-emerald-700" },
  failed: { label: "Gagal", cls: "bg-rose-100 text-rose-700" },
};

export default function DashboardHome() {
  const [rows, setRows] = useState<DatasetRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const { data, error } = await getSupabase()
      .from("datasets")
      .select("id,file_name,file_path,row_count,status,error_message,created_at,dashboards(id)")
      .order("created_at", { ascending: false });
    if (error) setError(error.message);
    else setRows((data ?? []) as unknown as DatasetRow[]);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const remove = async (d: DatasetRow) => {
    if (!window.confirm(`Hapus "${d.file_name}" beserta dashboard-nya?`)) return;
    setBusyId(d.id);
    const sb = getSupabase();
    await sb.storage.from(BUCKET).remove([d.file_path]);
    const { error } = await sb.from("datasets").delete().eq("id", d.id);
    if (error) setError(error.message);
    setBusyId(null);
    void load();
  };

  const reanalyze = async (d: DatasetRow) => {
    setBusyId(d.id);
    setError(null);
    try {
      await api(`/api/datasets/${d.id}/analyze`, { method: "POST" });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal menganalisis ulang.");
    }
    setBusyId(null);
    void load();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Unggah data baru</h1>
        <p className="text-sm text-slate-500">Dashboard dibuat otomatis setelah file selesai dianalisis.</p>
      </div>
      <Dropzone onUploaded={load} />

      <div>
        <h2 className="mb-2 text-base font-semibold">Dataset Anda</h2>
        {error && (
          <p className="mb-3 flex items-center gap-2 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">
            <AlertCircle size={16} /> {error}
          </p>
        )}
        {rows === null ? (
          <Loader2 className="animate-spin text-slate-400" />
        ) : rows.length === 0 ? (
          <p className="card p-6 text-center text-sm text-slate-400">Belum ada dataset.</p>
        ) : (
          <ul className="space-y-2">
            {rows.map((d) => {
              const st = STATUS[d.status];
              const dash = d.dashboards?.[0];
              return (
                <li key={d.id} className="card flex flex-wrap items-center justify-between gap-3 p-4">
                  <div className="flex min-w-0 items-center gap-3">
                    <FileSpreadsheet className="shrink-0 text-indigo-600" size={22} />
                    <div className="min-w-0">
                      <p className="truncate font-medium">{d.file_name}</p>
                      <p className="text-xs text-slate-400">
                        {new Date(d.created_at).toLocaleString("id-ID")}
                        {d.row_count != null && ` · ${d.row_count.toLocaleString("id-ID")} baris`}
                      </p>
                      {d.status === "failed" && d.error_message && (
                        <p className="text-xs text-rose-600">{d.error_message}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs ${st.cls}`}>{st.label}</span>
                    {dash && (
                      <Link href={`/dashboard/${dash.id}`} className="btn-primary !py-1.5">
                        Buka
                      </Link>
                    )}
                    <button
                      className="btn-ghost !p-1.5"
                      title="Analisis ulang"
                      disabled={busyId === d.id}
                      onClick={() => reanalyze(d)}
                    >
                      {busyId === d.id ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
                    </button>
                    <button
                      className="btn-ghost !p-1.5 hover:!text-rose-600"
                      title="Hapus"
                      disabled={busyId === d.id}
                      onClick={() => remove(d)}
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
