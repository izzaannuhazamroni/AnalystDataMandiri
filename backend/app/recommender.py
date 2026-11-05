"""Smart Visual Recommendation Rules Engine (PRD §4)."""
import pandas as pd

from .analysis import default_agg, detect_financial, pick_primary_measure, rule_for


def _chart(chart_type, x, y, agg, title, reason, **style) -> dict:
    return {
        "chart_type": chart_type,
        "x_axis": x,
        "y_axis": y,
        "aggregation": agg,
        "styling_json": {"title": title, "reason": reason, **style},
    }


def recommend_charts(df: pd.DataFrame, columns: list[dict], max_charts: int = 6) -> list[dict]:
    measure = pick_primary_measure(columns)
    ymeas = measure["name"] if measure else None
    agg = default_agg(ymeas)
    label = ymeas or "Jumlah baris"

    dts = [c for c in columns if c["type"] == "datetime" and c["n_unique"] > 1]
    cats = [c for c in columns if c["type"] == "categorical" and 2 <= c["n_unique"] <= 40]
    cats.sort(key=lambda c: (c["missing_pct"], c["n_unique"]))
    quants = [c for c in columns if c["type"] == "quantitative"]

    charts: list[dict] = []

    # 1. Datetime + 1 Quantitative -> Line
    if dts:
        charts.append(
            _chart(
                rule_for("datetime", dts[0]["n_unique"], "quantitative"),
                dts[0]["name"], ymeas, agg,
                f"Tren {label} dari waktu ke waktu",
                "Kolom tanggal + kolom kuantitatif → Line Chart untuk melihat tren.",
            )
        )

    # 2. Financial inflow/outflow -> Waterfall
    fin = detect_financial(columns)
    if fin:
        charts.append(
            _chart(
                "waterfall", None, None, "SUM",
                "Alur Pendapatan hingga Laba Bersih",
                "Terdeteksi kolom pendapatan & biaya → Waterfall Chart.",
                measures=fin,
            )
        )

    # 3. Categorical + Quantitative -> Donut (<=5) / Bar horizontal (>5)
    for c in cats[:3]:
        ct = rule_for("categorical", c["n_unique"], "quantitative")
        if ct == "donut":
            reason = "Kategori ≤ 5 item → Donut Chart untuk proporsi terhadap total."
            title = f"Kontribusi {label} per {c['name']}"
        else:
            reason = "Kategori > 5 item → Bar Horizontal agar label mudah dibaca (Top 10)."
            title = f"{label} per {c['name']} (Top 10)"
        charts.append(_chart(ct, c["name"], ymeas, agg if ymeas else "COUNT", title, reason))

    # 4. 2 Quantitative -> Scatter (pilih pasangan berkorelasi tertinggi)
    qn = [c["name"] for c in quants][:8]
    if len(qn) >= 2:
        sample = df[qn].dropna()
        if len(sample) > 5000:
            sample = sample.sample(5000, random_state=1)
        best, best_r = (qn[0], qn[1]), -1.0
        if len(sample) > 2:
            corr = sample.corr().abs()
            for i, a in enumerate(qn):
                for b in qn[i + 1:]:
                    r = corr.loc[a, b]
                    if pd.notna(r) and r > best_r:
                        best, best_r = (a, b), float(r)
        charts.append(
            _chart(
                "scatter", best[0], best[1], "SUM",
                f"Korelasi {best[0]} vs {best[1]}",
                "Dua variabel kuantitatif → Scatter Plot untuk menguji korelasi.",
            )
        )

    # fallback: tidak ada kolom yang cocok
    if not charts and quants:
        charts.append(
            _chart("bar", quants[0]["name"], None, "COUNT",
                   f"Distribusi {quants[0]['name']}",
                   "Hanya kolom kuantitatif → distribusi frekuensi.")
        )
    return charts[:max_charts]
