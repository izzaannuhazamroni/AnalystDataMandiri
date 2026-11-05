"use client";

import { X } from "lucide-react";
import clsx from "clsx";
import {
  CHART_TYPE_LABEL,
  type Agg,
  type ChartRow,
  type ChartType,
  type ColumnProfile,
} from "@/lib/types";

const TYPES = Object.keys(CHART_TYPE_LABEL) as ChartType[];
const AGGS: { v: Agg; l: string }[] = [
  { v: "SUM", l: "SUM (Total)" },
  { v: "AVG", l: "AVG (Rata-rata)" },
  { v: "COUNT", l: "COUNT (Jumlah)" },
  { v: "MIN", l: "MIN" },
  { v: "MAX", l: "MAX" },
];

export type ChartPatch = Partial<Pick<ChartRow, "chart_type" | "x_axis" | "y_axis" | "aggregation">> & {
  styling?: Partial<ChartRow["styling_json"]>;
};

interface Props {
  chart: ChartRow;
  columns: ColumnProfile[];
  onChange: (patch: ChartPatch) => void;
  onClose: () => void;
}

export default function Studio({ chart, columns, onChange, onClose }: Props) {
  const quants = columns.filter((c) => c.type === "quantitative");
  const hasMeasures = !!chart.styling_json.measures?.length;

  const swapAxes = () => onChange({ x_axis: chart.y_axis, y_axis: chart.x_axis });
  const canSwap = !!chart.x_axis && !!chart.y_axis;

  return (
    <aside className="fixed inset-y-0 right-0 z-40 flex w-full max-w-sm flex-col border-l border-slate-200 bg-white shadow-2xl">
      <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold">Chart Studio</h2>
          <p className="text-xs text-slate-400">Perubahan tersimpan otomatis</p>
        </div>
        <button className="btn-ghost !p-1.5" onClick={onClose} aria-label="Tutup">
          <X size={16} />
        </button>
      </header>

      <div className="flex-1 space-y-5 overflow-y-auto p-4 text-sm">
        <label className="block">
          <span className="mb-1 block font-medium text-slate-700">Judul</span>
          <input
            className="input"
            value={chart.styling_json.title ?? ""}
            onChange={(e) => onChange({ styling: { title: e.target.value } })}
          />
        </label>

        <div>
          <span className="mb-1 block font-medium text-slate-700">Tipe grafik</span>
          <div className="flex flex-wrap gap-1.5">
            {TYPES.map((t) => (
              <button
                key={t}
                onClick={() => onChange({ chart_type: t })}
                className={clsx(
                  "rounded-md px-2.5 py-1 text-xs",
                  chart.chart_type === t ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200",
                )}
              >
                {CHART_TYPE_LABEL[t]}
              </button>
            ))}
          </div>
        </div>

        {hasMeasures && chart.chart_type === "waterfall" ? (
          <div className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
            <p className="mb-2">
              Mode alur keuangan memakai kolom:{" "}
              <b>{chart.styling_json.measures?.map((m) => `${m.sign < 0 ? "−" : "+"}${m.column}`).join(", ")}</b>
            </p>
            <button className="btn-ghost !py-1 text-xs" onClick={() => onChange({ styling: { measures: null } })}>
              Pakai sumbu X/Y sebagai gantinya
            </button>
          </div>
        ) : null}

        <label className="block">
          <span className="mb-1 block font-medium text-slate-700">Sumbu X (dimensi)</span>
          <select
            className="input"
            value={chart.x_axis ?? ""}
            onChange={(e) => onChange({ x_axis: e.target.value || null })}
          >
            <option value="">— pilih kolom —</option>
            {columns.map((c) => (
              <option key={c.name} value={c.name}>
                {c.name} ({c.type})
              </option>
            ))}
          </select>
        </label>

        <div className="flex items-center gap-2">
          <div className="h-px flex-1 bg-slate-200" />
          <button className="btn-ghost !py-1 text-xs" disabled={!canSwap} onClick={swapAxes}>
            ⇅ Tukar X ↔ Y
          </button>
          <div className="h-px flex-1 bg-slate-200" />
        </div>

        <label className="block">
          <span className="mb-1 block font-medium text-slate-700">Sumbu Y (nilai)</span>
          <select
            className="input"
            value={chart.y_axis ?? ""}
            onChange={(e) => onChange({ y_axis: e.target.value || null })}
          >
            <option value="">(hitung jumlah baris)</option>
            {(chart.aggregation === "COUNT" ? columns : quants).map((c) => (
              <option key={c.name} value={c.name}>
                {c.name}
              </option>
            ))}
            {chart.y_axis && !(chart.aggregation === "COUNT" ? columns : quants).some((c) => c.name === chart.y_axis) && (
              <option value={chart.y_axis}>{chart.y_axis}</option>
            )}
          </select>
        </label>

        <label className="block">
          <span className="mb-1 block font-medium text-slate-700">Agregasi</span>
          <select
            className="input"
            value={chart.aggregation}
            onChange={(e) => onChange({ aggregation: e.target.value as Agg })}
          >
            {AGGS.map((a) => (
              <option key={a.v} value={a.v}>
                {a.l}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="mb-1 block font-medium text-slate-700">Tampilkan Top N (kategori)</span>
          <input
            type="number"
            min={1}
            max={100}
            className="input"
            placeholder="otomatis"
            value={chart.styling_json.top_n ?? ""}
            onChange={(e) => {
              const n = parseInt(e.target.value, 10);
              onChange({ styling: { top_n: Number.isFinite(n) ? Math.min(100, Math.max(1, n)) : null } });
            }}
          />
        </label>
      </div>
    </aside>
  );
}
