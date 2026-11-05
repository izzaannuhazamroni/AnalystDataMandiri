"""Lapisan AI: narasi eksekutif & "Ask My Data".

Privasi: hanya statistik teragregasi (bukan baris mentah) yang dikirim ke penyedia AI.
Jika API key tidak ada / gagal, otomatis memakai fallback berbasis aturan.
"""
import json
import re
from typing import Optional

import httpx

from . import config
from .analysis import default_agg, pick_primary_measure, rule_for

_http = httpx.Client(timeout=40)

CHART_TYPES = ["line", "area", "bar", "barh", "donut", "scatter", "waterfall"]
AGGS = ["SUM", "AVG", "COUNT", "MIN", "MAX"]


def fmt_compact(n: Optional[float], money: bool = False) -> str:
    if n is None:
        return "-"
    a = abs(n)
    for div, suf in ((1e12, " T"), (1e9, " M"), (1e6, " jt"), (1e3, " rb")):
        if a >= div:
            s = f"{n / div:.1f}".replace(".", ",") + suf
            return ("Rp " + s) if money else s
    s = f"{n:,.0f}".replace(",", ".")
    return ("Rp " + s) if money else s


# ------------------------------------------------------------------ LLM transport
def llm_available() -> bool:
    return config.AI_PROVIDER in ("gemini", "openai") and bool(
        config.GEMINI_API_KEY if config.AI_PROVIDER == "gemini" else config.OPENAI_API_KEY
    )


def call_llm(system: str, prompt: str, json_mode: bool = False) -> Optional[str]:
    if not llm_available():
        return None
    try:
        if config.AI_PROVIDER == "gemini":
            body = {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3},
            }
            if json_mode:
                body["generationConfig"]["responseMimeType"] = "application/json"
            r = _http.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent",
                headers={"x-goog-api-key": config.GEMINI_API_KEY},
                json=body,
            )
            r.raise_for_status()
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        body = {
            "model": config.OPENAI_MODEL,
            "temperature": 0.3,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        r = _http.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
            json=body,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception:  # noqa: BLE001 — fallback ke aturan
        return None


def _extract_json(text: str) -> Optional[dict]:
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------- narrative
def rule_based_narrative(ctx: dict) -> str:
    lines: list[str] = []
    kp = {k["key"]: k for k in ctx.get("kpis", [])}
    if "total" in kp:
        t = kp["total"]
        money = t["format"] == "currency"
        line = f"{t['label']} mencapai {fmt_compact(t['value'], money)}"
        if "count" in kp:
            line += f" dari {fmt_compact(kp['count']['value'])} transaksi"
        if "avg" in kp:
            line += f", rata-rata {fmt_compact(kp['avg']['value'], money)} per transaksi"
        lines.append(f"- {line}.")
    elif "count" in kp:
        lines.append(f"- Dataset berisi {fmt_compact(kp['count']['value'])} baris data.")

    growth = None
    if "growth" in kp and kp["growth"]["value"] is not None:
        growth = kp["growth"]["value"]
        arah = "naik" if growth >= 0 else "turun"
        lines.append(
            f"- Periode terakhir {arah} {abs(growth) * 100:.1f}% dibanding periode sebelumnya ({kp['growth']['hint']})."
        )
    f = ctx.get("facts", {})
    if f.get("peak"):
        lines.append(f"- Puncak tertinggi terjadi pada {f['peak']['label']} ({fmt_compact(f['peak']['value'])}).")
    top_share = None
    if f.get("top_category"):
        tc = f["top_category"]
        top_share = tc["share"]
        lines.append(
            f"- Pada {tc['dimension']}, '{tc['label']}' memberi kontribusi terbesar: {tc['share'] * 100:.1f}% dari total."
        )
    if f.get("correlation"):
        c = f["correlation"]
        if c["r"] is not None and abs(c["r"]) >= 0.5:
            sifat = "positif" if c["r"] > 0 else "negatif"
            lines.append(f"- Terdapat korelasi {sifat} yang kuat antara {c['x']} dan {c['y']} (r = {c['r']:.2f}).")
    if f.get("net_margin") is not None:
        lines.append(f"- Margin bersih dari alur keuangan sekitar {f['net_margin'] * 100:.1f}% dari pendapatan.")
    if not lines:
        lines.append("- Data berhasil diproses. Jelajahi grafik untuk melihat pola.")

    if growth is not None and growth < 0:
        rec = "Selidiki penyebab penurunan periode terakhir (volume, harga, atau musiman) dan siapkan promosi untuk memulihkan tren."
    elif top_share is not None and top_share > 0.5:
        rec = "Ketergantungan pada satu kategori cukup tinggi; pertimbangkan diversifikasi agar risiko lebih seimbang."
    elif f.get("net_margin") is not None and f["net_margin"] < 0.1:
        rec = "Margin tipis; tinjau komponen biaya terbesar untuk peluang efisiensi."
    else:
        rec = "Pertahankan momentum pada segmen berkinerja terbaik dan pantau segmen terendah untuk peluang perbaikan."
    lines.append(f"> Rekomendasi: {rec}")
    return "\n".join(lines)


def generate_narrative(ctx: dict) -> tuple[str, str]:
    """Return (teks, sumber) — sumber: 'ai' atau 'rule'."""
    system = (
        "Kamu analis bisnis senior. Tulis ringkasan eksekutif dalam Bahasa Indonesia yang ringkas dan faktual. "
        "Gunakan HANYA angka pada data yang diberikan; jangan mengarang. "
        "Format keluaran: 3-5 baris yang masing-masing diawali '- ' lalu satu baris terakhir diawali '> Rekomendasi: ' "
        "berisi satu rekomendasi bisnis yang dapat ditindaklanjuti. Tanpa markdown lain."
    )
    text = call_llm(system, "Data ringkasan:\n" + json.dumps(ctx, ensure_ascii=False, default=str))
    if text:
        lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
        ok = [l for l in lines if l.startswith("- ") or l.startswith("> ")]
        if len(ok) >= 2:
            return "\n".join(ok), "ai"
    return rule_based_narrative(ctx), "rule"


# ------------------------------------------------------------------- Ask My Data
def _norm(s: str) -> str:
    return re.sub(r"[_\s]+", " ", s.lower()).strip()


def heuristic_spec(question: str, columns: list[dict]) -> dict:
    q = _norm(question)
    by_name = {c["name"]: c for c in columns}
    mentioned = [c for c in columns if _norm(c["name"]) in q]
    m_quant = [c for c in mentioned if c["type"] == "quantitative"]
    m_dim = [c for c in mentioned if c["type"] in ("categorical", "datetime", "text")]

    measure = m_quant[0] if m_quant else pick_primary_measure(columns)
    y = measure["name"] if measure else None

    time_words = ("bulan", "tren", "waktu", "harian", "mingguan", "tahun", "per hari", "perkembangan", "naik", "turun")
    dts = [c for c in columns if c["type"] == "datetime"]
    cats = [c for c in columns if c["type"] == "categorical" and 2 <= c["n_unique"] <= 40]

    x = None
    if any(w in q for w in time_words) and dts:
        x = dts[0]
    elif m_dim:
        x = m_dim[0]
    elif cats:
        x = sorted(cats, key=lambda c: c["n_unique"])[0]
    elif dts:
        x = dts[0]

    if any(w in q for w in ("hubungan", "korelasi", "pengaruh")) and len(m_quant) >= 2:
        return {"chart_type": "scatter", "x_axis": m_quant[0]["name"], "y_axis": m_quant[1]["name"],
                "aggregation": "SUM", "title": f"Korelasi {m_quant[0]['name']} vs {m_quant[1]['name']}"}

    agg = default_agg(y)
    if "rata" in q or "average" in q or "avg" in q:
        agg = "AVG"
    elif any(w in q for w in ("berapa banyak", "jumlah transaksi", "hitung", "count", "banyaknya")):
        agg = "COUNT"
    elif "maksimum" in q or "tertinggi satu" in q:
        agg = "MAX"
    elif "minimum" in q or "terendah satu" in q:
        agg = "MIN"

    if x is None:
        return {"chart_type": "bar", "x_axis": y, "y_axis": None, "aggregation": "COUNT",
                "title": f"Distribusi {y}" if y else "Distribusi"}

    ct = rule_for(x["type"], x["n_unique"], "quantitative")
    if any(w in q for w in ("proporsi", "persentase", "kontribusi", "porsi", "komposisi")) and x["type"] != "datetime":
        ct = "donut"
    elif any(w in q for w in ("terbanyak", "tertinggi", "top", "terbesar", "terlaris")) and x["type"] != "datetime":
        ct = "barh"
    top_n = None
    mm = re.search(r"top\s*(\d+)|(\d+)\s*(teratas|terbesar|tertinggi)", q)
    if mm:
        top_n = int(mm.group(1) or mm.group(2))
    agg_word = {"SUM": "Total", "AVG": "Rata-rata", "COUNT": "Jumlah", "MIN": "Minimum", "MAX": "Maksimum"}[agg]
    title = f"{agg_word} {y or 'baris'} per {x['name']}"
    spec = {"chart_type": ct, "x_axis": x["name"], "y_axis": y if agg != "COUNT" or y else None,
            "aggregation": agg, "title": title}
    if top_n:
        spec["top_n"] = min(top_n, 100)
    return spec


def llm_spec(question: str, columns: list[dict]) -> Optional[dict]:
    if not llm_available():
        return None
    schema = []
    for c in columns:
        item = {"name": c["name"], "type": c["type"], "n_unique": c["n_unique"]}
        if c["type"] == "categorical" and c.get("top_values"):
            item["values"] = [v["value"] for v in c["top_values"][:10]]
        if c["type"] == "datetime":
            item["range"] = [c.get("date_min"), c.get("date_max")]
        schema.append(item)
    system = (
        "Kamu menerjemahkan pertanyaan bisnis berbahasa Indonesia menjadi spesifikasi grafik JSON. "
        "Balas HANYA JSON dengan kunci: chart_type (salah satu: line, area, bar, barh, donut, scatter), "
        "x_axis (nama kolom persis), y_axis (nama kolom kuantitatif persis, atau null untuk menghitung baris), "
        "aggregation (SUM, AVG, COUNT, MIN, MAX), top_n (integer atau null), title (judul singkat Indonesia), "
        "filters (null atau {\"categories\":[{\"column\":..., \"values\":[...]}]}). "
        "Aturan: datetime→line; kategori ≤5→donut; kategori >5→barh; dua kuantitatif→scatter. "
        "Gunakan hanya kolom yang ada pada skema."
    )
    prompt = f"Skema kolom:\n{json.dumps(schema, ensure_ascii=False)}\n\nPertanyaan: {question}"
    return _extract_json(call_llm(system, prompt, json_mode=True) or "")


def validate_spec(raw: dict, columns: list[dict]) -> Optional[dict]:
    """Validasi/normalisasi spec dari LLM. None jika tidak valid."""
    names = {c["name"].lower(): c["name"] for c in columns}
    ct = raw.get("chart_type")
    if ct not in CHART_TYPES or ct == "waterfall":
        return None
    x = names.get(str(raw.get("x_axis", "")).lower())
    y_raw = raw.get("y_axis")
    y = names.get(str(y_raw).lower()) if y_raw else None
    agg = str(raw.get("aggregation", "SUM")).upper()
    if agg not in AGGS or not x:
        return None
    if y_raw and not y:
        return None
    spec = {"chart_type": ct, "x_axis": x, "y_axis": y, "aggregation": agg if y else "COUNT",
            "title": str(raw.get("title") or "Hasil Pertanyaan")[:120]}
    tn = raw.get("top_n")
    if isinstance(tn, int) and 1 <= tn <= 100:
        spec["top_n"] = tn
    return spec


def resolve_filters(raw: Optional[dict], columns: list[dict]) -> dict:
    out: list[dict] = []
    if not raw:
        return {}
    names = {c["name"].lower(): c for c in columns}
    for cf in raw.get("categories") or []:
        col = names.get(str(cf.get("column", "")).lower())
        if not col or col["type"] != "categorical":
            continue
        known = {v["value"].lower(): v["value"] for v in col.get("top_values", [])}
        vals = [known[str(v).lower()] for v in cf.get("values", []) if str(v).lower() in known]
        if vals:
            out.append({"column": col["name"], "values": vals})
    return {"categories": out} if out else {}


def describe_answer(question: str, spec: dict, data: dict) -> tuple[str, str]:
    """Jawaban singkat. Return (teks, sumber)."""
    if data.get("empty") or (not data.get("labels") and not data.get("points")):
        return "Tidak ada data yang cocok dengan pertanyaan tersebut.", "rule"
    if llm_available():
        compact = {k: data.get(k) for k in ("labels", "values", "x_label", "y_label", "corr", "period")}
        if compact.get("labels"):
            compact["labels"] = compact["labels"][:20]
            compact["values"] = (compact.get("values") or [])[:20]
        text = call_llm(
            "Jawab pertanyaan user dalam Bahasa Indonesia, maksimal 2 kalimat, hanya berdasarkan data hasil query. Jangan mengarang angka.",
            f"Pertanyaan: {question}\nSpesifikasi: {json.dumps(spec, ensure_ascii=False)}\nHasil: {json.dumps(compact, ensure_ascii=False, default=str)}",
        )
        if text:
            return text.strip(), "ai"
    if spec["chart_type"] == "scatter":
        r = data.get("corr")
        if r is None:
            return "Korelasi tidak dapat dihitung dari data ini.", "rule"
        return f"Korelasi antara {data['x_label']} dan {data['y_label']} adalah r = {r:.2f}.", "rule"
    labels, values = data["labels"], data["values"]
    pairs = [(l, v) for l, v in zip(labels, values) if v is not None]
    if not pairs:
        return "Hasil kosong.", "rule"
    top = max(pairs, key=lambda p: p[1])
    low = min(pairs, key=lambda p: p[1])
    return (
        f"{data['y_label']} tertinggi: {top[0]} ({fmt_compact(top[1])}); terendah: {low[0]} ({fmt_compact(low[1])}).",
        "rule",
    )
