"""Mesin query agregasi untuk grafik (Studio): filter, group-by, SUM/AVG/COUNT/MIN/MAX."""
from typing import Any, Optional

import numpy as np
import pandas as pd


class QueryError(ValueError):
    """Kesalahan query yang bisa ditampilkan ke user (HTTP 400)."""


AGG_PREFIX = {"SUM": "Total", "AVG": "Rata-rata", "COUNT": "Jumlah", "MIN": "Minimum", "MAX": "Maksimum"}
PERIOD_FMT = {"D": "%Y-%m-%d", "W": "%Y-%m-%d", "M": "%Y-%m", "Y": "%Y"}
MAX_SCATTER = 2000


def _col_type(df: pd.DataFrame, name: Optional[str], types: dict[str, str]) -> str:
    if name not in df.columns:
        raise QueryError(f"Kolom '{name}' tidak ditemukan.")
    return types[name]


def apply_filters(df: pd.DataFrame, filters: Optional[dict], types: dict[str, str]) -> pd.DataFrame:
    if not filters:
        return df
    mask = pd.Series(True, index=df.index)
    d = filters.get("date")
    if d and (d.get("start") or d.get("end")):
        col = d["column"]
        if _col_type(df, col, types) != "datetime":
            raise QueryError(f"Kolom '{col}' bukan kolom tanggal.")
        try:
            if d.get("start"):
                mask &= df[col] >= pd.to_datetime(d["start"])
            if d.get("end"):
                mask &= df[col] < pd.to_datetime(d["end"]) + pd.Timedelta(days=1)
        except (ValueError, TypeError) as exc:
            raise QueryError("Format tanggal filter tidak valid.") from exc
    for cf in filters.get("categories") or []:
        vals = cf.get("values") or []
        if not vals:
            continue
        col = cf["column"]
        _col_type(df, col, types)
        mask &= df[col].astype(str).isin([str(v) for v in vals])
    return df[mask]


def choose_period(s: pd.Series) -> str:
    span = (s.max() - s.min()).days
    if span <= 45:
        return "D"
    if span <= 200:
        return "W"
    if span <= 1100:
        return "M"
    return "Y"


def _round(v: Any) -> Optional[float]:
    if v is None or pd.isna(v):
        return None
    return round(float(v), 4)


def _y_label(y: Optional[str], agg: str) -> str:
    if y is None:
        return "Jumlah baris"
    return f"{AGG_PREFIX[agg]} {y}"


def _bin_numeric(s: pd.Series) -> pd.Series:
    nn = s.dropna()
    if nn.nunique() <= 30:
        return s
    c = pd.cut(s, bins=10)
    labels = [f"{iv.left:.4g}–{iv.right:.4g}" for iv in c.cat.categories]
    return c.cat.rename_categories(labels)


def _scatter(df, types, x, y) -> dict:
    if not x or not y:
        raise QueryError("Scatter plot membutuhkan sumbu X dan Y.")
    for c in (x, y):
        if _col_type(df, c, types) != "quantitative":
            raise QueryError("Scatter plot membutuhkan dua kolom kuantitatif.")
    d = df[[x, y]].dropna()
    truncated = len(d) > MAX_SCATTER
    corr = None
    if len(d) > 2 and d[x].std() > 0 and d[y].std() > 0:
        corr = _round(d[x].corr(d[y]))
    if truncated:
        d = d.sample(MAX_SCATTER, random_state=42)
    pts = [[round(float(a), 4), round(float(b), 4)] for a, b in zip(d[x], d[y])]
    return {"points": pts, "x_label": x, "y_label": y, "truncated": truncated, "corr": corr}


def _waterfall_measures(df, types, measures) -> dict:
    labels, vals = [], []
    for m in measures:
        col = m["column"]
        if _col_type(df, col, types) != "quantitative":
            raise QueryError(f"Kolom '{col}' harus kuantitatif untuk waterfall.")
        labels.append(col)
        vals.append(round(float(df[col].sum()) * (m.get("sign") or 1), 2))
    labels.append("Laba Bersih")
    vals.append(round(sum(vals), 2))
    return {"labels": labels, "values": vals, "total_last": True, "x_label": "Komponen", "y_label": "Nilai"}


def _grouped(df, types, ct, x, y, agg, top_n) -> dict:
    if not x:
        raise QueryError("Sumbu X wajib dipilih.")
    xt = _col_type(df, x, types)
    if not y:
        y, agg = None, "COUNT"
    else:
        yt = _col_type(df, y, types)
        if agg != "COUNT" and yt != "quantitative":
            raise QueryError(f"Agregasi {agg} membutuhkan kolom Y kuantitatif. Gunakan COUNT untuk '{y}'.")

    s = df[x]
    chrono = False
    period = None
    if xt == "datetime":
        s = s.dropna()
        if s.empty:
            return {"labels": [], "values": [], "x_label": x, "y_label": _y_label(y, agg), "empty": True}
        period = choose_period(s)
        key = s.dt.to_period(period)
        chrono = True
    elif xt == "quantitative":
        key = _bin_numeric(s)
    else:
        key = s

    work = pd.DataFrame({"k": key})
    if y:
        work["v"] = df[y]
    work = work[work["k"].notna()]
    if work.empty:
        return {"labels": [], "values": [], "x_label": x, "y_label": _y_label(y, agg), "empty": True}

    g = work.groupby("k", observed=True, sort=True)
    if y is None:
        res = g.size()
    else:
        fn = {"SUM": "sum", "AVG": "mean", "COUNT": "count", "MIN": "min", "MAX": "max"}[agg]
        res = getattr(g["v"], fn)()

    sort_desc = (not chrono) and xt != "quantitative" and ct not in ("line", "area")
    if sort_desc:
        res = res.sort_values(ascending=False)

    limit = top_n or {"bar": 10, "barh": 10, "donut": 8, "waterfall": 10}.get(ct, 60)
    truncated = False
    other = None
    if len(res) > limit and not chrono:
        rest = res.iloc[limit:]
        res = res.iloc[:limit]
        truncated = True
        if ct == "donut" and agg in ("SUM", "COUNT"):
            other = float(rest.sum())

    idx = res.index
    if chrono:
        fmt = PERIOD_FMT[period]
        labels = [p.start_time.strftime(fmt) for p in idx]
    elif pd.api.types.is_numeric_dtype(idx):
        labels = [f"{v:g}" for v in idx]
    else:
        labels = [str(i) for i in idx]
    values = [_round(v) for v in res.values]
    if other is not None:
        labels.append("Lainnya")
        values.append(_round(other))

    out = {
        "labels": labels,
        "values": values,
        "x_label": x,
        "y_label": _y_label(y, agg),
        "truncated": truncated,
    }
    if period:
        out["period"] = {"D": "harian", "W": "mingguan", "M": "bulanan", "Y": "tahunan"}[period]
    if ct == "waterfall":
        total = round(float(np.nansum([v or 0 for v in values])), 2)
        out["labels"].append("Total")
        out["values"].append(total)
        out["total_last"] = True
    return out


def run_chart_query(
    df: pd.DataFrame,
    types: dict[str, str],
    spec: dict,
    filters: Optional[dict] = None,
) -> dict:
    df = apply_filters(df, filters, types)
    ct = spec["chart_type"]
    x, y = spec.get("x_axis"), spec.get("y_axis")
    agg = spec.get("aggregation") or "SUM"
    if len(df) == 0:
        return {"labels": [], "values": [], "points": [], "x_label": x, "y_label": y, "empty": True}
    if ct == "scatter":
        return _scatter(df, types, x, y)
    if ct == "waterfall" and spec.get("measures"):
        return _waterfall_measures(df, types, spec["measures"])
    return _grouped(df, types, ct, x, y, agg, spec.get("top_n"))
