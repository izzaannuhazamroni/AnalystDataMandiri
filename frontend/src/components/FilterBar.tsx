"use client";

import { Filter, RotateCcw } from "lucide-react";
import type { ColumnProfile, Filters } from "@/lib/types";

interface Props {
  columns: ColumnProfile[];
  filters: Filters;
  onChange: (f: Filters) => void;
}

/** Global Slicer Filter: rentang tanggal + kategori (berlaku ke semua grafik). */
export default function FilterBar({ columns, filters, onChange }: Props) {
  const dateCols = columns.filter((c) => c.type === "datetime" && c.n_unique > 1);
  const catCols = columns
    .filter((c) => c.type === "categorical" && c.top_values && c.n_unique >= 2 && c.n_unique <= 30)
    .slice(0, 4);
  if (!dateCols.length && !catCols.length) return null;

  const dateCol = filters.date?.column ?? dateCols[0]?.name;
  const dateProfile = dateCols.find((c) => c.name === dateCol);
  const active = !!(filters.date?.start || filters.date?.end || filters.categories?.some((c) => c.values.length));

  const setDate = (patch: { column?: string; start?: string; end?: string }) => {
    const next = { column: dateCol!, start: filters.date?.start, end: filters.date?.end, ...patch };
    onChange({
      ...filters,
      date: next.start || next.end ? { column: next.column, start: next.start || undefined, end: next.end || undefined } : undefined,
    });
  };

  const toggleCat = (column: string, value: string) => {
    const cur = filters.categories?.find((c) => c.column === column)?.values ?? [];
    const values = cur.includes(value) ? cur.filter((v) => v !== value) : [...cur, value];
    const others = (filters.categories ?? []).filter((c) => c.column !== column);
    onChange({ ...filters, categories: values.length ? [...others, { column, values }] : others });
  };

  return (
    <div className="card flex flex-wrap items-end gap-3 p-3 text-sm" data-html2canvas-ignore>
      <span className="flex items-center gap-1.5 pb-2 font-medium text-slate-600">
        <Filter size={15} /> Filter
      </span>

      {dateCols.length > 0 && (
        <div className="flex flex-wrap items-end gap-2">
          {dateCols.length > 1 && (
            <label className="block">
              <span className="mb-0.5 block text-xs text-slate-400">Kolom tanggal</span>
              <select className="input !py-1.5" value={dateCol} onChange={(e) => setDate({ column: e.target.value })}>
                {dateCols.map((c) => (
                  <option key={c.name}>{c.name}</option>
                ))}
              </select>
            </label>
          )}
          <label className="block">
            <span className="mb-0.5 block text-xs text-slate-400">Dari</span>
            <input
              type="date"
              className="input !py-1.5"
              min={dateProfile?.date_min ?? undefined}
              max={dateProfile?.date_max ?? undefined}
              value={filters.date?.start ?? ""}
              onChange={(e) => setDate({ start: e.target.value })}
            />
          </label>
          <label className="block">
            <span className="mb-0.5 block text-xs text-slate-400">Sampai</span>
            <input
              type="date"
              className="input !py-1.5"
              min={dateProfile?.date_min ?? undefined}
              max={dateProfile?.date_max ?? undefined}
              value={filters.date?.end ?? ""}
              onChange={(e) => setDate({ end: e.target.value })}
            />
          </label>
        </div>
      )}

      {catCols.map((c) => {
        const sel = filters.categories?.find((f) => f.column === c.name)?.values ?? [];
        return (
          <details key={c.name} className="relative">
            <summary className="input flex cursor-pointer list-none items-center gap-2 !py-1.5">
              <span>{c.name}</span>
              {sel.length > 0 && <span className="rounded-full bg-indigo-100 px-1.5 text-xs text-indigo-700">{sel.length}</span>}
            </summary>
            <div className="absolute left-0 z-30 mt-1 max-h-60 w-56 overflow-y-auto rounded-lg border border-slate-200 bg-white p-2 shadow-lg">
              {c.top_values!.map((v) => (
                <label key={v.value} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 hover:bg-slate-50">
                  <input type="checkbox" checked={sel.includes(v.value)} onChange={() => toggleCat(c.name, v.value)} />
                  <span className="truncate">{v.value}</span>
                </label>
              ))}
            </div>
          </details>
        );
      })}

      {active && (
        <button className="btn-ghost" onClick={() => onChange({})}>
          <RotateCcw size={14} /> Reset
        </button>
      )}
    </div>
  );
}
