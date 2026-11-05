import { Calculator, Receipt, TrendingDown, TrendingUp, Wallet } from "lucide-react";
import type { Kpi } from "@/lib/types";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/format";

function icon(k: Kpi) {
  if (k.key === "growth") return (k.value ?? 0) >= 0 ? TrendingUp : TrendingDown;
  if (k.key === "count") return Receipt;
  if (k.key === "avg") return Calculator;
  return Wallet;
}

function show(k: Kpi) {
  if (k.format === "currency") return formatCurrency(k.value);
  if (k.format === "percent") return formatPercent(k.value);
  return formatNumber(k.value);
}

export default function KpiCards({ kpis }: { kpis: Kpi[] }) {
  if (!kpis.length) return null;
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {kpis.map((k) => {
        const Icon = icon(k);
        const growthColor = k.key === "growth" ? ((k.value ?? 0) >= 0 ? "text-emerald-600" : "text-rose-600") : "text-slate-900";
        return (
          <div key={k.key} className="card p-4">
            <div className="flex items-center justify-between text-sm text-slate-500">
              <span>{k.label}</span>
              <span className="rounded-lg bg-indigo-50 p-1.5 text-indigo-600">
                <Icon size={16} />
              </span>
            </div>
            <div className={`mt-2 truncate text-2xl font-semibold ${growthColor}`}>{show(k)}</div>
            {k.hint && <div className="mt-1 truncate text-xs text-slate-400">{k.hint}</div>}
          </div>
        );
      })}
    </div>
  );
}
