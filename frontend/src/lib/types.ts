export type ColType = "quantitative" | "categorical" | "datetime" | "text";

export interface ColumnProfile {
  name: string;
  type: ColType;
  n_missing: number;
  missing_pct: number;
  n_unique: number;
  samples: string[];
  stats?: {
    min: number | null;
    max: number | null;
    mean: number | null;
    median: number | null;
    std: number | null;
    sum: number | null;
  };
  top_values?: { value: string; count: number }[];
  date_min?: string | null;
  date_max?: string | null;
}

export interface CleaningReport {
  rows_before: number;
  rows_after: number;
  cols_before: number;
  cols_after: number;
  empty_rows_dropped: number;
  empty_cols_dropped: number;
  duplicates_removed: number;
  converted: { column: string; to: ColType }[];
  filled: { column: string; strategy: string; count: number }[];
  numeric_missing: { column: string; count: number }[];
}

export interface DatasetSchema {
  columns: ColumnProfile[];
  cleaning?: CleaningReport;
}

export interface Kpi {
  key: string;
  label: string;
  value: number | null;
  format: "currency" | "number" | "percent";
  hint?: string;
}

export type ChartType = "line" | "area" | "bar" | "barh" | "donut" | "scatter" | "waterfall";
export type Agg = "SUM" | "AVG" | "COUNT" | "MIN" | "MAX";

export interface Measure {
  column: string;
  sign: number;
}

export interface ChartStyling {
  title?: string;
  reason?: string;
  top_n?: number | null;
  measures?: Measure[] | null;
}

export interface ChartRow {
  id: string;
  dashboard_id: string;
  chart_type: ChartType;
  x_axis: string | null;
  y_axis: string | null;
  aggregation: Agg;
  styling_json: ChartStyling;
  position: number;
}

export interface BatchItem {
  id: string;
  chart_type: ChartType;
  x_axis: string | null;
  y_axis: string | null;
  aggregation: Agg;
  top_n: number | null;
  measures: Measure[] | null;
}

export interface ChartData {
  labels?: string[];
  values?: (number | null)[];
  points?: [number, number][];
  x_label?: string | null;
  y_label?: string | null;
  total_last?: boolean;
  truncated?: boolean;
  empty?: boolean;
  corr?: number | null;
  period?: string;
  error?: string;
}

export interface Filters {
  date?: { column: string; start?: string; end?: string };
  categories?: { column: string; values: string[] }[];
}

export interface DashboardInfo {
  id: string;
  title: string | null;
  summary_text: string | null;
  kpi_json: Kpi[] | null;
  share_token?: string | null;
  share_expires_at?: string | null;
}

export interface DatasetInfo {
  id?: string;
  file_name: string;
  row_count: number | null;
  schema_json: DatasetSchema | null;
}

export interface AskResult {
  spec: {
    chart_type: ChartType;
    x_axis: string | null;
    y_axis: string | null;
    aggregation: Agg;
    top_n?: number;
    title: string;
  };
  data: ChartData;
  answer: string;
  source: "ai" | "heuristic";
}

export const CHART_TYPE_LABEL: Record<ChartType, string> = {
  line: "Line",
  area: "Area",
  bar: "Bar",
  barh: "Bar Horizontal",
  donut: "Donut",
  scatter: "Scatter",
  waterfall: "Waterfall",
};
