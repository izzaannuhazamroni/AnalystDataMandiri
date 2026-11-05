"use client";

import { useState } from "react";
import { Check, Copy, Link2, Loader2, X } from "lucide-react";
import { api } from "@/lib/api";

interface Props {
  dashboardId: string;
  token: string | null;
  expiresAt: string | null;
  onChange: (token: string | null, expiresAt: string | null) => void;
  onClose: () => void;
}

export default function ShareDialog({ dashboardId, token, expiresAt, onChange, onClose }: Props) {
  const [days, setDays] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const link = token && typeof window !== "undefined" ? `${window.location.origin}/share/${token}` : "";

  const create = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await api<{ token: string; expires_at: string | null }>(`/api/dashboards/${dashboardId}/share`, {
        method: "POST",
        body: { expires_in_days: days ? parseInt(days, 10) : null },
      });
      onChange(r.token, r.expires_at);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal membuat link.");
    } finally {
      setBusy(false);
    }
  };

  const revoke = async () => {
    setBusy(true);
    setError(null);
    try {
      await api(`/api/dashboards/${dashboardId}/share`, { method: "DELETE" });
      onChange(null, null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal mencabut link.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="card w-full max-w-md p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-base font-semibold">
            <Link2 size={18} className="text-indigo-600" /> Bagikan Dashboard
          </h2>
          <button className="btn-ghost !p-1.5" onClick={onClose} aria-label="Tutup">
            <X size={16} />
          </button>
        </div>

        {token ? (
          <div className="space-y-3 text-sm">
            <p className="text-slate-600">Siapa pun yang memiliki link ini dapat melihat dashboard (hanya-baca), tanpa login.</p>
            <div className="flex gap-2">
              <input readOnly className="input" value={link} onFocus={(e) => e.currentTarget.select()} />
              <button
                className="btn-primary"
                onClick={async () => {
                  await navigator.clipboard.writeText(link);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 1500);
                }}
              >
                {copied ? <Check size={16} /> : <Copy size={16} />}
              </button>
            </div>
            {expiresAt && <p className="text-xs text-slate-400">Kedaluwarsa: {new Date(expiresAt).toLocaleString("id-ID")}</p>}
            <button className="btn-ghost text-rose-600" disabled={busy} onClick={revoke}>
              {busy && <Loader2 size={14} className="animate-spin" />} Cabut akses link
            </button>
          </div>
        ) : (
          <div className="space-y-3 text-sm">
            <p className="text-slate-600">Buat link read-only. Data asli tidak dapat diunduh dan link dapat dicabut kapan saja.</p>
            <label className="block">
              <span className="mb-1 block font-medium text-slate-700">Masa berlaku</span>
              <select className="input" value={days} onChange={(e) => setDays(e.target.value)}>
                <option value="">Tanpa batas waktu</option>
                <option value="1">1 hari</option>
                <option value="7">7 hari</option>
                <option value="30">30 hari</option>
              </select>
            </label>
            <button className="btn-primary" disabled={busy} onClick={create}>
              {busy && <Loader2 size={14} className="animate-spin" />} Buat link
            </button>
          </div>
        )}
        {error && <p className="mt-3 rounded-lg bg-rose-50 p-2 text-sm text-rose-700">{error}</p>}
      </div>
    </div>
  );
}
