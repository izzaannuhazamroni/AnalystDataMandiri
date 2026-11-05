import type { EChartsCoreOption } from "echarts/core";
import type { ChartData, ChartType } from "./types";
import { compact, formatNumber } from "./format";

export const PALETTE = [
  "#4f46e5", "#06b6d4", "#f59e0b", "#10b981", "#ef4444",
  "#8b5cf6", "#ec4899", "#84cc16", "#0ea5e9", "#f97316",
];

const axisStyle = {
  axisLine: { lineStyle: { color: "#cbd5e1" } },
  axisLabel: { color: "#475569" },
  splitLine: { lineStyle: { color: "#e2e8f0" } },
};

export function buildOption(type: ChartType, d: ChartData): EChartsCoreOption {
  const labels = d.labels ?? [];
  const values = (d.values ?? []).map((v) => v ?? 0);
  const base = {
    color: PALETTE,
    animationDuration: 300,
    textStyle: { fontFamily: "Inter, system-ui, sans-serif" },
    grid: { left: 8, right: 20, top: 28, bottom: 8, containLabel: true },
  };

  switch (type) {
    case "line":
    case "area":
      return {
        ...base,
        tooltip: { trigger: "axis", valueFormatter: (v: unknown) => formatNumber(v as number) },
        xAxis: { type: "category", data: labels, boundaryGap: false, ...axisStyle },
        yAxis: { type: "value", name: d.y_label ?? "", axisLabel: { ...axisStyle.axisLabel, formatter: (v: number) => compact(v) }, splitLine: axisStyle.splitLine },
        dataZoom: labels.length > 60 ? [{ type: "inside" }] : undefined,
        series: [
          {
            type: "line",
            smooth: true,
            showSymbol: labels.length < 40,
            data: values,
            lineStyle: { width: 2.5 },
            areaStyle: type === "area" ? { opacity: 0.18 } : undefined,
          },
        ],
      };
    case "bar":
      return {
        ...base,
        tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (v: unknown) => formatNumber(v as number) },
        xAxis: { type: "category", data: labels, ...axisStyle, axisLabel: { ...axisStyle.axisLabel, interval: 0, rotate: labels.length > 6 ? 30 : 0 } },
        yAxis: { type: "value", name: d.y_label ?? "", axisLabel: { ...axisStyle.axisLabel, formatter: (v: number) => compact(v) }, splitLine: axisStyle.splitLine },
        series: [{ type: "bar", data: values, itemStyle: { borderRadius: [4, 4, 0, 0] }, barMaxWidth: 48 }],
      };
    case "barh":
      return {
        ...base,
        tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (v: unknown) => formatNumber(v as number) },
        xAxis: { type: "value", axisLabel: { ...axisStyle.axisLabel, formatter: (v: number) => compact(v) }, splitLine: axisStyle.splitLine },
        yAxis: { type: "category", data: labels, inverse: true, ...axisStyle },
        series: [{ type: "bar", data: values, itemStyle: { borderRadius: [0, 4, 4, 0] }, barMaxWidth: 26 }],
      };
    case "donut":
      return {
        ...base,
        tooltip: { trigger: "item", formatter: "{b}<br/>{c} ({d}%)" },
        legend: { bottom: 0, type: "scroll", textStyle: { color: "#475569" } },
        series: [
          {
            type: "pie",
            radius: ["45%", "70%"],
            center: ["50%", "46%"],
            avoidLabelOverlap: true,
            itemStyle: { borderColor: "#fff", borderWidth: 2 },
            label: { formatter: "{d}%", color: "#334155" },
            data: labels.map((name, i) => ({ name, value: values[i] })),
          },
        ],
      };
    case "scatter":
      return {
        ...base,
        tooltip: {
          trigger: "item",
          formatter: (p: unknown) => {
            const v = (p as { value: [number, number] }).value;
            return `${d.x_label}: ${formatNumber(v[0])}<br/>${d.y_label}: ${formatNumber(v[1])}`;
          },
        },
        xAxis: { type: "value", name: d.x_label ?? "", nameLocation: "middle", nameGap: 28, scale: true, axisLabel: { ...axisStyle.axisLabel, formatter: (v: number) => compact(v) }, splitLine: axisStyle.splitLine },
        yAxis: { type: "value", name: d.y_label ?? "", scale: true, axisLabel: { ...axisStyle.axisLabel, formatter: (v: number) => compact(v) }, splitLine: axisStyle.splitLine },
        series: [{ type: "scatter", data: d.points ?? [], symbolSize: 7, itemStyle: { opacity: 0.55 } }],
      };
    case "waterfall": {
      let cum = 0;
      const baseS: number[] = [], up: number[] = [], down: number[] = [], total: number[] = [];
      values.forEach((v, i) => {
        const isTotal = d.total_last && i === values.length - 1;
        if (isTotal) {
          baseS.push(0); up.push(0); down.push(0); total.push(v);
        } else {
          const start = cum;
          cum += v;
          baseS.push(Math.min(start, cum));
          up.push(v >= 0 ? v : 0);
          down.push(v < 0 ? -v : 0);
          total.push(0);
        }
      });
      return {
        ...base,
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
          formatter: (p: unknown) => {
            const i = (p as { dataIndex: number }[])[0].dataIndex;
            return `${labels[i]}<br/><b>${formatNumber(values[i])}</b>`;
          },
        },
        xAxis: { type: "category", data: labels, ...axisStyle, axisLabel: { ...axisStyle.axisLabel, interval: 0 } },
        yAxis: { type: "value", axisLabel: { ...axisStyle.axisLabel, formatter: (v: number) => compact(v) }, splitLine: axisStyle.splitLine },
        series: [
          { type: "bar", stack: "w", silent: true, itemStyle: { color: "transparent" }, data: baseS },
          { name: "Naik", type: "bar", stack: "w", itemStyle: { color: "#10b981" }, data: up, barMaxWidth: 48 },
          { name: "Turun", type: "bar", stack: "w", itemStyle: { color: "#ef4444" }, data: down, barMaxWidth: 48 },
          { name: "Total", type: "bar", stack: "w", itemStyle: { color: "#4f46e5" }, data: total, barMaxWidth: 48 },
        ],
      };
    }
  }
}
