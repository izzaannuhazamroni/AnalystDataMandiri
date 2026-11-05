"""Heuristik pemilihan kolom: measure utama, deteksi data keuangan, agregasi default."""
import re
from typing import Optional

REVENUE_KW = ["omset", "omzet", "revenue", "pendapatan", "penjualan", "sales", "income"]
MEASURE_KW = REVENUE_KW + ["total", "amount", "nilai", "subtotal", "harga", "price", "profit", "laba"]
COST_KW = [
    "hpp", "cogs", "biaya", "beban", "expense", "cost", "pengeluaran",
    "gaji", "sewa", "pajak", "diskon", "discount", "ongkir",
]
MONEY_KW = MEASURE_KW + COST_KW
AVG_KW = ["harga", "price", "rate", "rating", "score", "skor", "nilai rata", "persen", "pct", "margin"]
TXN_ID_KW = ["transaksi", "transaction", "invoice", "order", "nota", "faktur"]


def _has(name: str, kws: list[str]) -> bool:
    n = name.lower().replace("_", " ")
    return any(k in n for k in kws)


def is_money_name(name: str) -> bool:
    return _has(name, MONEY_KW)


def default_agg(name: Optional[str]) -> str:
    if not name:
        return "COUNT"
    return "AVG" if _has(name, AVG_KW) else "SUM"


def pick_primary_measure(columns: list[dict]) -> Optional[dict]:
    quants = [c for c in columns if c["type"] == "quantitative"]
    if not quants:
        return None
    for kw in MEASURE_KW:
        for c in quants:
            if kw in c["name"].lower().replace("_", " "):
                return c
    return quants[0]


def detect_financial(columns: list[dict]) -> Optional[list[dict]]:
    """Return daftar measures waterfall [{column, sign}] bila ada inflow & outflow."""
    quants = [c for c in columns if c["type"] == "quantitative"]
    inflow = [c for c in quants if _has(c["name"], REVENUE_KW)]
    outflow = [c for c in quants if _has(c["name"], COST_KW) and c not in inflow]
    if not inflow or not outflow:
        return None
    measures = [{"column": inflow[0]["name"], "sign": 1}]
    measures += [{"column": c["name"], "sign": -1} for c in outflow[:5]]
    return measures


def find_txn_id(columns: list[dict]) -> Optional[dict]:
    for c in columns:
        if c["type"] == "text" and _has(c["name"], TXN_ID_KW):
            return c
    return None


def rule_for(x_type: str, x_unique: int, y_type: Optional[str]) -> str:
    """Aturan visual PRD §4."""
    if x_type == "datetime":
        return "line"
    if x_type == "quantitative" and y_type == "quantitative":
        return "scatter"
    if x_type in ("categorical", "text"):
        return "donut" if x_unique <= 5 else "barh"
    return "bar"
