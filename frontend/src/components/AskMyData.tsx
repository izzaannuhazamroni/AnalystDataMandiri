"use client";

import { useMemo, useState } from "react";
import { Loader2, MessageSquare, Pin, Send } from "lucide-react";
import EChart from "./EChart";
import { api } from "@/lib/api";
import { buildOption } from "@/lib/chartOptions";
import type { AskResult, Filters } from "@/lib/types";

const SUGGESTIONS = [
  "Total omset per cabang",
  "Bagaimana tren penjualan per bulan?",
  "Kontribusi tiap kategori",
  "Rata-rata omset per kategori",
];

interface Props {
  datasetId: string;
  filters: Filters;
  onPin: (r: AskResult) => Promise<void>;
}

export default function AskMyData({ datasetId, filters, onPin }: Props) {
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [pinning, setPinning] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AskResult | null>(null);

  const option = useMemo(
    () => (result && !result.data.empty ? buildOption(result.spec.chart_type, result.data) : null),
    [result],
  );

  const ask = async (question: string) => {
    if (question.trim().length < 2) return;
    setLoading(true);
    setError(null);
    setPinned(false);
    try {
      const r = await api<AskResult>("/api/ask", {
        method: "POST",
        body: { dataset_id: datasetId, question, filters },
      });
      setResult(r);
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : "Gagal memproses pertanyaan.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card space-y-3 p-5" data-html2canvas-ignore>
      <h2 className="flex items-center gap-2 text-base font-semibold">
        <MessageSquare size={18} className="text-indigo-600" /> Ask My Data
      </h2>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          ask(q);
        }}
      >
        <input
          className="input"
          placeholder="Tanyakan sesuatu, mis. “Cabang mana yang omsetnya tertinggi?”"
          value={q}
          maxLength={500}
          onChange={(e) => setQ(e.target.value)}
        />
        <button className="btn-primary" disabled={loading || q.trim().length < 2}>
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />} Tanya
        </button>
      </form>
      <div className="flex flex-wrap gap-1.5">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-200"
            onClick={() => {
              setQ(s);
              ask(s);
            }}
          >
            {s}
          </button>
        ))}
      </div>

      {error && <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}

      {result && (
        <div className="space-y-3 rounded-xl border border-slate-200 p-4">
          <p className="text-sm text-slate-800">{result.answer}</p>
          <div className="text-xs text-slate-400">
            {result.spec.title} · dijawab oleh {result.source === "ai" ? "AI" : "mesin aturan"}
          </div>
          {option ? <EChart option={option} height={260} /> : <p className="text-sm text-slate-400">Tidak ada data untuk ditampilkan.</p>}
          <button
            className="btn-ghost"
            disabled={pinning || pinned || !option}
            onClick={async () => {
              setPinning(true);
              try {
                await onPin(result);
                setPinned(true);
              } catch (e) {
                setError(e instanceof Error ? e.message : "Gagal menyematkan grafik.");
              } finally {
                setPinning(false);
              }
            }}
          >
            <Pin size={14} /> {pinned ? "Tersemat di dashboard" : "Sematkan ke dashboard"}
          </button>
        </div>
      )}
    </section>
  );
}
