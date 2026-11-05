"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { FileDown, Loader2, Plus, Share2 } from "lucide-react";
import AskMyData from "./AskMyData";
import ChartCard from "./ChartCard";
import FilterBar from "./FilterBar";
import KpiCards from "./KpiCards";
import NarrativeCard from "./NarrativeCard";
import ShareDialog from "./ShareDialog";
import Studio, { type ChartPatch } from "./Studio";
import { exportDashboardPdf } from "@/lib/export";
import { getSupabase } from "@/lib/supabase";
import type {
  AskResult,
  BatchItem,
  ChartData,
  ChartRow,
  ChartType,
  DashboardInfo,
  DatasetInfo,
  Filters,
} from "@/lib/types";

export interface DashboardViewProps {
  mode: "owner" | "shared";
  dashboard: DashboardInfo;
  dataset: DatasetInfo;
  initialCharts: ChartRow[];
  runBatch: (items: BatchItem[], filters: Filters) => Promise<Record<string, ChartData>>;
}

const specOf = (c: ChartRow): BatchItem => ({
  id: c.id,
  chart_type: c.chart_type,
  x_axis: c.x_axis,
  y_axis: c.y_axis,
  aggregation: c.aggregation,
  top_n: c.styling_json?.top_n ?? null,
  measures: c.styling_json?.measures ?? null,
});

export default function DashboardView({ mode, dashboard, dataset, initialCharts, runBatch }: DashboardViewProps) {
  const readOnly = mode === "shared";
  const columns = dataset.schema_json?.columns ?? [];

  const [charts, setCharts] = useState<ChartRow[]>(initialCharts);
  const [filters, setFilters] = useState<Filters>({});
  const [results, setResults] = useState<Record<string, ChartData>>({});
  const [loading, setLoading] = useState<Set<string>>(new Set());
  const [studioId, setStudioId] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [share, setShare] = useState({ token: dashboard.share_token ?? null, expires: dashboard.share_expires_at ?? null });
  const [notice, setNotice] = useState<string | null>(null);

  const fetched = useRef<Record<string, string>>({});
  const latest = useRef<Record<string, number>>({});
  const seq = useRef(0);
  const exportRef = useRef<HTMLDivElement>(null);
  const persistTimers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  /* ------------------------------------------------ fetch data (hanya yang berubah) */
  useEffect(() => {
    const fkey = JSON.stringify(filters);
    const stale = charts.filter((c) => fetched.current[c.id] !== JSON.stringify(specOf(c)) + fkey);
    if (!stale.length) return;
    const timer = setTimeout(async () => {
      const mySeq = ++seq.current;
      stale.forEach((c) => {
        fetched.current[c.id] = JSON.stringify(specOf(c)) + fkey;
        latest.current[c.id] = mySeq;
      });
      setLoading((p) => new Set([...p, ...stale.map((c) => c.id)]));
      try {
        const res = await runBatch(stale.map(specOf), filters);
        setResults((r) => {
          const next = { ...r };
          for (const [id, d] of Object.entries(res)) if (latest.current[id] === mySeq) next[id] = d;
          return next;
        });
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Gagal memuat data grafik.";
        setResults((r) => {
          const next = { ...r };
          for (const c of stale) if (latest.current[c.id] === mySeq) next[c.id] = { error: msg };
          return next;
        });
      } finally {
        setLoading((p) => {
          const n = new Set(p);
          stale.forEach((c) => latest.current[c.id] === mySeq && n.delete(c.id));
          return n;
        });
      }
    }, 120);
    return () => clearTimeout(timer);
  }, [charts, filters, runBatch]);

  useEffect(() => {
    const timers = persistTimers.current;
    return () => Object.values(timers).forEach(clearTimeout);
  }, []);

  /* ------------------------------------------------------------- mutasi grafik */
  const persist = useCallback((row: ChartRow, immediate: boolean) => {
    if (readOnly) return;
    const run = async () => {
      const { error } = await getSupabase()
        .from("charts")
        .update({
          chart_type: row.chart_type,
          x_axis: row.x_axis,
          y_axis: row.y_axis,
          aggregation: row.aggregation,
          styling_json: row.styling_json,
        })
        .eq("id", row.id);
      if (error) setNotice(`Perubahan belum tersimpan: ${error.message}`);
    };
    clearTimeout(persistTimers.current[row.id]);
    if (immediate) void run();
    else persistTimers.current[row.id] = setTimeout(run, 500);
  }, [readOnly]);

  const updateChart = useCallback(
    (id: string, patch: ChartPatch) => {
      const cur = charts.find((c) => c.id === id);
      if (!cur) return;
      const { styling, ...rest } = patch;
      const next: ChartRow = { ...cur, ...rest, styling_json: { ...cur.styling_json, ...styling } };
      setCharts((cs) => cs.map((c) => (c.id === id ? next : c)));
      persist(next, !styling?.title);
    },
    [charts, persist],
  );

  const deleteChart = async (id: string) => {
    if (!window.confirm("Hapus grafik ini dari dashboard?")) return;
    const { error } = await getSupabase().from("charts").delete().eq("id", id);
    if (error) {
      setNotice(`Gagal menghapus: ${error.message}`);
      return;
    }
    setCharts((cs) => cs.filter((c) => c.id !== id));
    if (studioId === id) setStudioId(null);
  };

  const insertChart = async (row: Omit<ChartRow, "id" | "dashboard_id" | "position">): Promise<ChartRow> => {
    const position = charts.length ? Math.max(...charts.map((c) => c.position)) + 1 : 0;
    const { data, error } = await getSupabase()
      .from("charts")
      .insert({ ...row, dashboard_id: dashboard.id, position })
      .select("*")
      .single();
    if (error) throw new Error(error.message);
    const created = data as ChartRow;
    setCharts((cs) => [...cs, created]);
    return created;
  };

  const addChart = async () => {
    try {
      const dim = columns.find((c) => c.type === "categorical" && c.n_unique >= 2 && c.n_unique <= 40) ?? columns[0];
      const meas = columns.find((c) => c.type === "quantitative");
      if (!dim) return;
      const created = await insertChart({
        chart_type: "bar",
        x_axis: dim.name,
        y_axis: meas?.name ?? null,
        aggregation: meas ? "SUM" : "COUNT",
        styling_json: { title: "Grafik baru" },
      });
      setStudioId(created.id);
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Gagal menambah grafik.");
    }
  };

  const pinAsk = async (r: AskResult) => {
    await insertChart({
      chart_type: r.spec.chart_type,
      x_axis: r.spec.x_axis,
      y_axis: r.spec.y_axis,
      aggregation: r.spec.aggregation,
      styling_json: { title: r.spec.title, reason: "Disematkan dari Ask My Data.", top_n: r.spec.top_n ?? null },
    });
  };

  const doExport = async () => {
    if (!exportRef.current) return;
    setExporting(true);
    try {
      await exportDashboardPdf(exportRef.current, dashboard.title ?? "dashboard");
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Export PDF gagal.");
    } finally {
      setExporting(false);
    }
  };

  const studioChart = charts.find((c) => c.id === studioId) ?? null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <h1 className="truncate text-xl font-semibold">{dashboard.title ?? "Dashboard"}</h1>
          <p className="text-sm text-slate-500">
            {dataset.file_name}
            {dataset.row_count != null && ` · ${dataset.row_count.toLocaleString("id-ID")} baris`}
            {readOnly && " · tampilan hanya-baca"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {!readOnly && (
            <>
              <button className="btn-ghost" onClick={addChart}>
                <Plus size={16} /> Tambah grafik
              </button>
              <button className="btn-ghost" onClick={() => setShareOpen(true)}>
                <Share2 size={16} /> Bagikan
              </button>
            </>
          )}
          <button className="btn-primary" disabled={exporting} onClick={doExport}>
            {exporting ? <Loader2 size={16} className="animate-spin" /> : <FileDown size={16} />} Export PDF
          </button>
        </div>
      </div>

      {notice && (
        <div className="flex items-center justify-between rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
          {notice}
          <button className="text-xs underline" onClick={() => setNotice(null)}>
            Tutup
          </button>
        </div>
      )}

      <FilterBar columns={columns} filters={filters} onChange={setFilters} />

      {!readOnly && dataset.id && <AskMyData datasetId={dataset.id} filters={filters} onPin={pinAsk} />}

      <div ref={exportRef} className="space-y-4 bg-white p-1">
        <div className="hidden print:block" />
        <NarrativeCard text={dashboard.summary_text} />
        <KpiCards kpis={dashboard.kpi_json ?? []} />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {charts.map((c, i) => (
            <div key={c.id} className={i === 0 && c.chart_type === "line" ? "lg:col-span-2" : ""}>
              <ChartCard
                chart={c}
                data={results[c.id]}
                loading={loading.has(c.id)}
                readOnly={readOnly}
                tall={i === 0 && c.chart_type === "line"}
                onTypeChange={(t: ChartType) => updateChart(c.id, { chart_type: t })}
                onEdit={() => setStudioId(c.id)}
                onDelete={() => deleteChart(c.id)}
              />
            </div>
          ))}
        </div>
        {!charts.length && (
          <p className="card p-8 text-center text-sm text-slate-400">Belum ada grafik. Klik “Tambah grafik” atau gunakan Ask My Data.</p>
        )}
      </div>

      {studioChart && (
        <Studio
          chart={studioChart}
          columns={columns}
          onChange={(p) => updateChart(studioChart.id, p)}
          onClose={() => setStudioId(null)}
        />
      )}
      {shareOpen && (
        <ShareDialog
          dashboardId={dashboard.id}
          token={share.token}
          expiresAt={share.expires}
          onChange={(token, expires) => setShare({ token, expires })}
          onClose={() => setShareOpen(false)}
        />
      )}
    </div>
  );
}
