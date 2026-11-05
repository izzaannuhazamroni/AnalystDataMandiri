"use client";

import { useMemo, useRef, useState } from "react";
import { Download, Loader2, Pencil, Trash2 } from "lucide-react";
import clsx from "clsx";
import EChart from "./EChart";
import { buildOption } from "@/lib/chartOptions";
import { downloadPng, downloadSvg } from "@/lib/export";
import { CHART_TYPE_LABEL, type ChartData, type ChartRow, type ChartType } from "@/lib/types";

const TYPES: ChartType[] = ["line", "area", "bar", "barh", "donut", "scatter", "waterfall"];

interface Props {
  chart: ChartRow;
  data?: ChartData;
  loading: boolean;
  readOnly: boolean;
  tall?: boolean;
  onTypeChange?: (t: ChartType) => void;
  onEdit?: () => void;
  onDelete?: () => void;
}

export default function ChartCard({ chart, data, loading, readOnly, tall, onTypeChange, onEdit, onDelete }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const [menu, setMenu] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const title = chart.styling_json?.title ?? "Grafik";

  const option = useMemo(
    () => (data && !data.error && !data.empty ? buildOption(chart.chart_type, data) : null),
    [data, chart.chart_type],
  );

  const run = async (fn: () => Promise<void> | void) => {
    setErr(null);
    setMenu(false);
    try {
      await fn();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Gagal mengekspor.");
    }
  };

  return (
    <div className="card flex flex-col p-4">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-slate-900">{title}</h3>
          {chart.styling_json?.reason && (
            <p className="truncate text-xs text-slate-400" title={chart.styling_json.reason}>
              {chart.styling_json.reason}
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-1" data-html2canvas-ignore>
          {loading && <Loader2 size={16} className="animate-spin text-slate-400" />}
          <div className="relative">
            <button className="btn-ghost !p-1.5" title="Unduh grafik" onClick={() => setMenu((m) => !m)}>
              <Download size={15} />
            </button>
            {menu && (
              <div className="absolute right-0 z-20 mt-1 w-40 rounded-lg border border-slate-200 bg-white py-1 text-sm shadow-lg">
                <button className="block w-full px-3 py-1.5 text-left hover:bg-slate-50" onClick={() => run(async () => { if (box.current) await downloadPng(box.current, title); })}>
                  PNG (resolusi tinggi)
                </button>
                <button className="block w-full px-3 py-1.5 text-left hover:bg-slate-50" onClick={() => run(() => { if (box.current) downloadSvg(box.current, title); })}>
                  SVG (vektor)
                </button>
              </div>
            )}
          </div>
          {!readOnly && (
            <>
              <button className="btn-ghost !p-1.5" title="Buka Studio" onClick={onEdit}>
                <Pencil size={15} />
              </button>
              <button className="btn-ghost !p-1.5 hover:!text-rose-600" title="Hapus grafik" onClick={onDelete}>
                <Trash2 size={15} />
              </button>
            </>
          )}
        </div>
      </div>

      {!readOnly && (
        <div className="mb-2 flex flex-wrap gap-1" data-html2canvas-ignore>
          {TYPES.map((t) => (
            <button
              key={t}
              onClick={() => onTypeChange?.(t)}
              className={clsx(
                "rounded-md px-2 py-0.5 text-xs transition",
                chart.chart_type === t ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200",
              )}
            >
              {CHART_TYPE_LABEL[t]}
            </button>
          ))}
        </div>
      )}

      <div ref={box} className="min-h-[220px] flex-1">
        {option ? (
          <EChart option={option} height={tall ? 340 : 280} />
        ) : (
          <div className="flex h-[220px] items-center justify-center px-6 text-center text-sm text-slate-400">
            {data?.error ?? (data?.empty ? "Tidak ada data pada filter ini." : loading ? "Memuat…" : "—")}
          </div>
        )}
      </div>
      {data?.truncated && <p className="mt-1 text-xs text-slate-400">Menampilkan sebagian data teratas/sampel.</p>}
      {chart.chart_type === "scatter" && data?.corr != null && (
        <p className="mt-1 text-xs text-slate-500">Korelasi (r) = {data.corr.toFixed(2)}</p>
      )}
      {err && <p className="mt-1 text-xs text-rose-600">{err}</p>}
    </div>
  );
}
