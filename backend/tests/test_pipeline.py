import io
import time

import pandas as pd
import pytest

from app.cleaning import LoadError, clean_dataframe, load_dataframe
from app.pipeline import build_analysis, process_file
from app.query import QueryError, run_chart_query


def _sales_csv(n=3000) -> bytes:
    import random
    from datetime import date, timedelta

    random.seed(1)
    rows = []
    for i in range(n):
        d = date(2025, 1, 1) + timedelta(days=random.randint(0, 400))
        omset = random.randint(1, 20) * random.choice([5000, 12000, 25000])
        rows.append(
            {
                "No Transaksi": f"TRX{i:05d}",
                "Tanggal": d.strftime("%d/%m/%Y"),
                "Cabang": random.choice(["Jakarta", "Surabaya", "Bandung", "Madiun", "Malang", "Medan"]),
                "Kategori": random.choice(["Makanan", "Minuman", "Snack"]),
                "Omset": f"Rp {omset:,}".replace(",", "."),  # format Indonesia
                "HPP": int(omset * 0.6),
                "Biaya": int(omset * 0.1),
                "Qty": random.randint(1, 20),
            }
        )
    return pd.DataFrame(rows).to_csv(index=False).encode()


def test_type_inference_and_indonesian_numbers():
    df, types, columns, report = process_file(_sales_csv(), "x.csv")
    assert types["Tanggal"] == "datetime"
    assert types["Omset"] == "quantitative"
    assert types["Cabang"] == "categorical"
    assert types["No Transaksi"] == "text"
    assert df["Omset"].min() >= 5000


def test_analysis_charts_follow_prd_rules():
    df, types, columns, report = process_file(_sales_csv(), "x.csv")
    res = build_analysis(df, types, columns, report, "x.csv")
    by = {(c["chart_type"], c["x_axis"]) for c in res["charts"]}
    assert ("line", "Tanggal") in by  # datetime + quant
    assert ("donut", "Kategori") in by  # <=5 item
    assert ("barh", "Cabang") in by  # >5 item
    assert any(c["chart_type"] == "waterfall" for c in res["charts"])
    assert any(c["chart_type"] == "scatter" for c in res["charts"])
    assert {k["key"] for k in res["kpis"]} >= {"total", "count", "avg", "growth"}
    assert res["narrative"].count("\n") >= 2


def test_performance_100k_rows():
    import numpy as np

    rng = np.random.default_rng(0)
    n = 100_000
    df = pd.DataFrame(
        {
            "Tanggal": pd.to_datetime("2024-01-01") + pd.to_timedelta(rng.integers(0, 700, n), unit="D"),
            "Cabang": rng.choice([f"C{i}" for i in range(12)], n),
            "Kategori": rng.choice(["A", "B", "C"], n),
            "Omset": rng.integers(1000, 500000, n),
            "HPP": rng.integers(500, 250000, n),
            "Biaya": rng.integers(100, 50000, n),
        }
    )
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    t0 = time.time()
    d, types, columns, report = process_file(buf.getvalue().encode(), "big.csv")
    build_analysis(d, types, columns, report, "big.csv")
    assert time.time() - t0 <= 8, "melebihi target 8 detik (PRD §6)"

    t1 = time.time()
    run_chart_query(d, types, {"chart_type": "bar", "x_axis": "Cabang", "y_axis": "Omset", "aggregation": "AVG"})
    assert time.time() - t1 <= 0.3, "interaksi melebihi 300 ms"


def test_query_filters_and_aggregations():
    df, types, columns, _ = process_file(_sales_csv(), "x.csv")
    spec = {"chart_type": "bar", "x_axis": "Kategori", "y_axis": "Omset", "aggregation": "SUM"}
    full = run_chart_query(df, types, spec)
    assert abs(sum(full["values"]) - df["Omset"].sum()) < 1
    filt = run_chart_query(df, types, spec, {"categories": [{"column": "Cabang", "values": ["Jakarta"]}]})
    assert sum(filt["values"]) < sum(full["values"])
    cnt = run_chart_query(df, types, {"chart_type": "donut", "x_axis": "Kategori", "y_axis": None, "aggregation": "COUNT"})
    assert sum(cnt["values"]) == len(df)
    dated = run_chart_query(
        df, types, spec | {"chart_type": "line", "x_axis": "Tanggal"},
        {"date": {"column": "Tanggal", "start": "2025-03-01", "end": "2025-03-31"}},
    )
    assert all(l.startswith("2025-03") for l in dated["labels"])


def test_query_errors():
    df, types, *_ = process_file(_sales_csv(), "x.csv")
    with pytest.raises(QueryError):
        run_chart_query(df, types, {"chart_type": "scatter", "x_axis": "Cabang", "y_axis": "Omset"})
    with pytest.raises(QueryError):
        run_chart_query(df, types, {"chart_type": "bar", "x_axis": "Cabang", "y_axis": "Kategori", "aggregation": "SUM"})
    with pytest.raises(QueryError):
        run_chart_query(df, types, {"chart_type": "bar", "x_axis": "Tidak Ada", "y_axis": "Omset"})


def test_excel_roundtrip_and_bad_files():
    df = pd.DataFrame({"Produk": ["A", "B", "A"], "Total": [1000, 2000, 3000]})
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    loaded = load_dataframe(buf.getvalue(), "t.xlsx")
    assert len(loaded) == 3
    with pytest.raises(LoadError):
        load_dataframe(b"abc", "t.pdf")


def test_missing_values_handling():
    df = pd.DataFrame(
        {
            "Kota": ["A", None, "B", "A"] * 10,
            "Nilai": [1.0, None, 3.0, 4.0] * 10,
            "Urut": range(40),  # cegah baris dianggap duplikat
        }
    )
    out, types, report = clean_dataframe(df)
    assert "Tidak Diketahui" in set(out["Kota"])
    assert report["numeric_missing"][0]["column"] == "Nilai"


def test_heuristic_ask():
    from app import ai

    df, types, columns, _ = process_file(_sales_csv(), "x.csv")
    spec = ai.validate_spec(ai.heuristic_spec("Total omset per cabang terbanyak", columns), columns)
    assert spec and spec["x_axis"] == "Cabang" and spec["y_axis"] == "Omset"
    data = run_chart_query(df, types, {k: v for k, v in spec.items() if k != "title"})
    ans, _ = ai.describe_answer("x", spec, data)
    assert "tertinggi" in ans
