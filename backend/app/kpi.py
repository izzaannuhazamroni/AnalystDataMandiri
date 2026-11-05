"""Dynamic KPI Cards: Total Omset, Transaction Count, Average Ticket Size, Growth Rate."""
from typing import Optional

import pandas as pd

from .analysis import find_txn_id, is_money_name, pick_primary_measure
from .profiling import py
from .query import choose_period

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def _period_label(p: pd.Period, freq: str) -> str:
    ts = p.start_time
    if freq == "M":
        return f"{_MONTHS[ts.month - 1]} {ts.year}"
    if freq == "Y":
        return str(ts.year)
    return f"{ts.day} {_MONTHS[ts.month - 1]} {ts.year}"


def compute_kpis(df: pd.DataFrame, types: dict[str, str], columns: list[dict]) -> list[dict]:
    kpis: list[dict] = []
    measure = pick_primary_measure(columns)
    txn_col = find_txn_id(columns)
    n_txn = int(df[txn_col["name"]].nunique()) if txn_col else int(len(df))

    total: Optional[float] = None
    if measure:
        total = py(df[measure["name"]].sum())
        kpis.append(
            {
                "key": "total",
                "label": f"Total {measure['name']}",
                "value": total,
                "format": "currency" if is_money_name(measure["name"]) else "number",
                "hint": f"Jumlah seluruh nilai kolom {measure['name']}",
            }
        )
    kpis.append(
        {
            "key": "count",
            "label": "Jumlah Transaksi" if txn_col or measure else "Jumlah Baris",
            "value": n_txn,
            "format": "number",
            "hint": f"Unik berdasarkan {txn_col['name']}" if txn_col else "Jumlah baris data",
        }
    )
    if measure and total is not None and n_txn:
        kpis.append(
            {
                "key": "avg",
                "label": "Rata-rata per Transaksi",
                "value": py(total / n_txn),
                "format": "currency" if is_money_name(measure["name"]) else "number",
                "hint": "Total dibagi jumlah transaksi",
            }
        )

    # growth rate: periode terakhir vs sebelumnya
    dt_cols = [c for c in columns if c["type"] == "datetime" and c["n_unique"] > 1]
    if measure and dt_cols:
        dcol = dt_cols[0]["name"]
        s = df[[dcol, measure["name"]]].dropna(subset=[dcol])
        if len(s) > 1:
            freq = choose_period(s[dcol])
            if freq == "D":
                freq = "W" if (s[dcol].max() - s[dcol].min()).days >= 14 else "D"
            per = s.groupby(s[dcol].dt.to_period(freq))[measure["name"]].sum().sort_index()
            if len(per) >= 2 and per.iloc[-2] not in (0, None):
                prev, last = float(per.iloc[-2]), float(per.iloc[-1])
                kpis.append(
                    {
                        "key": "growth",
                        "label": "Growth Rate",
                        "value": py((last - prev) / abs(prev)),
                        "format": "percent",
                        "hint": f"{_period_label(per.index[-1], freq)} vs {_period_label(per.index[-2], freq)}",
                    }
                )
    return kpis
