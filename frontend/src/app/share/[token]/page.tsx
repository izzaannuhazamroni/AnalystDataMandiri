"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import DashboardView from "@/components/DashboardView";
import { publicApi } from "@/lib/api";
import type { BatchItem, ChartData, ChartRow, DashboardInfo, DatasetInfo, Filters } from "@/lib/types";

interface Shared {
  dashboard: DashboardInfo;
  dataset: DatasetInfo;
  charts: ChartRow[];
}

export default function SharedDashboardPage() {
  const { token } = useParams<{ token: string }>();
  const [data, setData] = useState<Shared | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    publicApi<Shared>(`/api/share/${token}`)
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Link tidak valid."));
  }, [token]);

  const runBatch = useCallback(
    async (items: BatchItem[], filters: Filters) => {
      const r = await publicApi<{ results: Record<string, ChartData> }>(`/api/share/${token}/query/batch`, {
        method: "POST",
        body: { items, filters },
      });
      return r.results;
    },
    [token],
  );

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center px-4 py-3">
          <span className="text-lg font-bold text-indigo-700">AutoAnalytica</span>
          <span className="ml-3 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">Dashboard bersama · hanya-baca</span>
        </div>
      </header>
      <main className="mx-auto max-w-7xl p-4">
        {error ? (
          <p className="rounded-lg bg-rose-50 p-4 text-sm text-rose-700">{error}</p>
        ) : !data ? (
          <Loader2 className="animate-spin text-slate-400" />
        ) : (
          <DashboardView
            mode="shared"
            dashboard={data.dashboard}
            dataset={data.dataset}
            initialCharts={data.charts}
            runBatch={runBatch}
          />
        )}
      </main>
    </div>
  );
}
