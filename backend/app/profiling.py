"""Auto Data Profiling per kolom."""
from typing import Any

import numpy as np
import pandas as pd


def py(v: Any) -> Any:
    """Konversi nilai numpy/pandas ke tipe python yang JSON-safe."""
    if v is None:
        return None
    if isinstance(v, (pd.Timestamp,)):
        return None if pd.isna(v) else v.strftime("%Y-%m-%d")
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        f = float(v)
        return None if (np.isnan(f) or np.isinf(f)) else round(f, 4)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


def profile_dataframe(df: pd.DataFrame, types: dict[str, str]) -> list[dict]:
    n = len(df)
    out: list[dict] = []
    for c in df.columns:
        s = df[c]
        t = types[c]
        n_missing = int(s.isna().sum())
        col: dict = {
            "name": c,
            "type": t,
            "n_missing": n_missing,
            "missing_pct": round(n_missing / n * 100, 2) if n else 0.0,
            "n_unique": int(s.nunique(dropna=True)),
            "samples": [str(v) for v in s.dropna().head(3).tolist()],
        }
        if t == "quantitative":
            nn = s.dropna().astype(float)
            if len(nn):
                col["stats"] = {
                    "min": py(nn.min()),
                    "max": py(nn.max()),
                    "mean": py(nn.mean()),
                    "median": py(nn.median()),
                    "std": py(nn.std()) if len(nn) > 1 else None,
                    "sum": py(nn.sum()),
                }
        elif t == "categorical":
            vc = s.value_counts(dropna=True)
            limit = 30 if col["n_unique"] <= 30 else 10
            col["top_values"] = [
                {"value": str(k), "count": int(v)} for k, v in vc.head(limit).items()
            ]
        elif t == "datetime":
            col["date_min"] = py(s.min())
            col["date_max"] = py(s.max())
        out.append(col)
    return out
