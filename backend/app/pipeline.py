"""Orkestrasi analisis: load → clean → profile → KPI → chart recommendation → narasi."""
import time
from pathlib import Path
from typing import Any

import pandas as pd

from . import ai
from .cleaning import clean_dataframe, load_dataframe
from .kpi import compute_kpis
from .profiling import profile_dataframe
from .query import QueryError, run_chart_query
from .recommender import recommend_charts


def process_file(content: bytes, filename: str) -> tuple[pd.DataFrame, dict[str, str], list[dict], dict]:
    raw = load_dataframe(content, filename)
    df, types, report = clean_dataframe(raw)
    columns = profile_dataframe(df, types)
    return df, types, columns, report


def _facts(df, types, charts, kpis) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    for ch in charts:
        try:
            res = run_chart_query(df, types, {
                "chart_type": ch["chart_type"], "x_axis": ch["x_axis"], "y_axis": ch["y_axis"],
                "aggregation": ch["aggregation"], "measures": ch["styling_json"].get("measures"),
            })
        except QueryError:
            continue
        ct = ch["chart_type"]
        vals = res.get("values") or []
        labels = res.get("labels") or []
        if ct == "line" and vals and "peak" not in facts:
            i = max(range(len(vals)), key=lambda k: vals[k] or float("-inf"))
            facts["peak"] = {"label": labels[i], "value": vals[i]}
        elif ct in ("donut", "barh") and vals and "top_category" not in facts:
            total = sum(v or 0 for v in vals)
            if total > 0:
                facts["top_category"] = {
                    "dimension": ch["x_axis"], "label": labels[0], "share": round((vals[0] or 0) / total, 4),
                }
        elif ct == "scatter" and "correlation" not in facts:
            facts["correlation"] = {"x": ch["x_axis"], "y": ch["y_axis"], "r": res.get("corr")}
        elif ct == "waterfall" and len(vals) >= 2 and vals[0]:
            facts["net_margin"] = round(vals[-1] / vals[0], 4)
    return facts


def build_analysis(df, types, columns, report, filename: str) -> dict:
    t0 = time.time()
    kpis = compute_kpis(df, types, columns)
    charts = recommend_charts(df, columns)
    ctx = {
        "dataset": Path(filename).name,
        "rows": int(len(df)),
        "kpis": [{k: v for k, v in kp.items() if k != "hint"} | {"hint": kp.get("hint")} for kp in kpis],
        "facts": _facts(df, types, charts, kpis),
    }
    narrative, source = ai.generate_narrative(ctx)
    return {
        "kpis": kpis,
        "charts": charts,
        "narrative": narrative,
        "narrative_source": source,
        "elapsed_sec": round(time.time() - t0, 2),
    }
