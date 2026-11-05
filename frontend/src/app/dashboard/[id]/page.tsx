"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import DashboardView from "@/components/DashboardView";
import { api } from "@/lib/api";
import { getSupabase } from "@/lib/supabase";
import type { BatchItem, ChartData, ChartRow, DashboardInfo, DatasetInfo, Filters } from "@/lib/types";

interface Loaded {
  dashboard: DashboardInfo;
  dataset: DatasetInfo & { id: string };
  charts: ChartRow[];
}

export default function DashboardPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<Loaded | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const sb = getSupabase();
      const { data: d, error } = await sb
        .from("dashboards")
        .select("*, datasets(id,file_name,row_count,schema_json), charts(*)")
        .eq("id", id)
        .single();
      if (cancelled) return;
      if (error || !d) {
        setError(error?.message ?? "Dashboard tidak ditemukan.");
        return;
      }
      const charts = ([...(d.charts ?? [])] as ChartRow[]).sort((a, b) => a.position - b.position);
      setData({ dashboard: d as DashboardInfo, dataset: d.datasets as Loaded["dataset"], charts });
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  const datasetId = data?.dataset.id;
  const runBatch = useCallback(
    async (items: BatchItem[], filters: Filters) => {
      const r = await api<{ results: Record<string, ChartData> }>("/api/query/batch", {
        method: "POST",
        body: { dataset_id: datasetId, items, filters },
      });
      return r.results;
    },
    [datasetId],
  );

  return (
    <div className="space-y-4">
      <Link href="/dashboard" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-indigo-600">
        <ArrowLeft size={14} /> Kembali
      </Link>
      {error ? (
        <p className="rounded-lg bg-rose-50 p-4 text-sm text-rose-700">{error}</p>
      ) : !data ? (
        <Loader2 className="animate-spin text-slate-400" />
      ) : (
        <DashboardView
          mode="owner"
          dashboard={data.dashboard}
          dataset={data.dataset}
          initialCharts={data.charts}
          runBatch={runBatch}
        />
      )}
    </div>
  );
}
