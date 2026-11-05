"""Phase 1 — Data loading, cleaning otomatis & inferensi tipe kolom.

Tipe semantik: quantitative | categorical | datetime | text (identifier / teks bebas).
"""
import csv
import io
import re
from typing import Optional

import numpy as np
import pandas as pd

MISSING_TOKENS = {"", "nan", "none", "null", "n/a", "na", "-", "--", "#n/a", "#value!"}
UNKNOWN_LABEL = "Tidak Diketahui"

_RE_ID = re.compile(r"^-?\d{1,3}(\.\d{3})+(,\d+)?$")  # 1.234.567,89
_RE_EN = re.compile(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$")  # 1,234,567.89
_ID_NAME = re.compile(r"(^|[_\s])(id|no|kode|code|nomor|uuid)($|[_\s])|_id$|^id", re.I)


class LoadError(ValueError):
    pass


# --------------------------------------------------------------------------- load
def _sniff_sep(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def _fix_header(df: pd.DataFrame) -> pd.DataFrame:
    """Jika header berada di baris bawah (banyak kolom 'Unnamed'), pakai baris pertama yang padat."""
    unnamed = sum(str(c).startswith("Unnamed") for c in df.columns)
    if unnamed <= len(df.columns) / 2 or df.empty:
        return df
    for i in range(min(15, len(df))):
        row = df.iloc[i]
        if row.notna().mean() >= 0.6 and all(isinstance(v, str) for v in row.dropna()):
            new = df.iloc[i + 1 :].copy()
            new.columns = [str(v) if pd.notna(v) else f"Kolom {j + 1}" for j, v in enumerate(row)]
            return new.reset_index(drop=True)
    return df


def load_dataframe(content: bytes, filename: str) -> pd.DataFrame:
    name = filename.lower()
    try:
        if name.endswith((".csv", ".txt", ".tsv")):
            text = None
            for enc in ("utf-8-sig", "utf-16", "latin-1"):
                try:
                    text = content.decode(enc)
                    break
                except UnicodeError:
                    continue
            if text is None:
                raise LoadError("Encoding file tidak dikenali.")
            sep = _sniff_sep(text[:8192])
            df = pd.read_csv(
                io.StringIO(text), sep=sep, low_memory=False, on_bad_lines="skip"
            )
        elif name.endswith((".xlsx", ".xlsm", ".xls")):
            engine = "xlrd" if name.endswith(".xls") else "openpyxl"
            sheets = pd.read_excel(io.BytesIO(content), sheet_name=None, engine=engine)
            if not sheets:
                raise LoadError("File Excel tidak berisi sheet.")
            # pilih sheet dengan sel terisi terbanyak
            df = max(sheets.values(), key=lambda d: int(d.notna().sum().sum()))
            df = _fix_header(df)
        else:
            raise LoadError("Format tidak didukung. Gunakan .xlsx, .xls, atau .csv.")
    except LoadError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise LoadError(f"Gagal membaca file: {exc}") from exc
    if df.empty or df.shape[1] == 0:
        raise LoadError("File tidak berisi data.")
    return df


# ------------------------------------------------------------------- type parsing
def _parse_numeric_object(s: pd.Series) -> Optional[pd.Series]:
    """Parse string angka (format Indonesia/Inggris, Rp, %, kurung negatif)."""
    x = s.where(s.notna()).astype(str).str.strip()
    x = x.mask(x.str.lower().isin(MISSING_TOKENS))
    x = x.str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    x = x.str.replace(r"(?i)rp\.?|idr|usd|\$|€|%", "", regex=True)
    x = x.str.replace(r"\s+", "", regex=True)
    nn = x.dropna()
    if nn.empty:
        return None
    sample = nn.head(500)
    id_hits = int(sample.str.match(_RE_ID).sum())
    en_hits = int(sample.str.match(_RE_EN).sum())
    if en_hits:
        y = x.str.replace(",", "", regex=False)
    elif id_hits:
        y = x.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    else:
        y = x.str.replace(",", ".", regex=False)
    out = pd.to_numeric(y, errors="coerce")
    if out.notna().sum() / len(nn) < 0.9:
        return None
    return out


def _try_datetime(s: pd.Series) -> Optional[pd.Series]:
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    if pd.api.types.is_numeric_dtype(s) or pd.api.types.is_bool_dtype(s):
        return None
    nn = s.dropna()
    if nn.empty:
        return None
    sample = nn.astype(str).head(200)
    if sample.str.contains(r"\d").mean() < 0.9:
        return None
    if sample.str.len().max() < 6:
        return None
    parsed_sample = pd.to_datetime(sample, errors="coerce", dayfirst=True, format="mixed")
    if parsed_sample.notna().mean() < 0.9:
        return None
    parsed = pd.to_datetime(
        s.where(s.notna()).astype(str).where(s.notna()),
        errors="coerce",
        dayfirst=True,
        format="mixed",
    )
    if parsed.notna().sum() / len(nn) < 0.9:
        return None
    return parsed


def _dedupe_columns(cols: list) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for i, c in enumerate(cols):
        name = re.sub(r"\s+", " ", str(c)).strip() or f"Kolom {i + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name} ({seen[name]})"
        else:
            seen[name] = 0
        out.append(name)
    return out


# ----------------------------------------------------------------------- cleaning
def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str], dict]:
    """Bersihkan data. Return (df_bersih, {kolom: tipe_semantik}, laporan)."""
    report: dict = {
        "rows_before": int(len(df)),
        "cols_before": int(df.shape[1]),
        "empty_rows_dropped": 0,
        "empty_cols_dropped": 0,
        "duplicates_removed": 0,
        "converted": [],
        "filled": [],
        "numeric_missing": [],
    }
    df = df.copy()
    df.columns = _dedupe_columns(list(df.columns))

    # baris/kolom kosong total
    before = len(df)
    df = df.dropna(how="all")
    report["empty_rows_dropped"] = before - len(df)
    keep = [c for c in df.columns if df[c].notna().any()]
    report["empty_cols_dropped"] = df.shape[1] - len(keep)
    df = df[keep]

    # whitespace pada string
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].map(lambda v: v.strip() if isinstance(v, str) else v)

    # duplikat
    before = len(df)
    df = df.drop_duplicates()
    report["duplicates_removed"] = before - len(df)
    df = df.reset_index(drop=True)

    types: dict[str, str] = {}
    n = max(len(df), 1)
    for c in list(df.columns):
        s = df[c]
        if pd.api.types.is_bool_dtype(s):
            df[c] = s.map({True: "Ya", False: "Tidak"})
            types[c] = "categorical"
            continue
        if pd.api.types.is_datetime64_any_dtype(s):
            types[c] = "datetime"
            continue
        if pd.api.types.is_numeric_dtype(s):
            types[c] = "quantitative"
        else:
            num = _parse_numeric_object(s)
            if num is not None:
                df[c] = num
                types[c] = "quantitative"
                report["converted"].append({"column": c, "to": "quantitative"})
            else:
                dt = _try_datetime(s)
                if dt is not None:
                    df[c] = dt
                    types[c] = "datetime"
                    report["converted"].append({"column": c, "to": "datetime"})
                else:
                    s2 = s.where(s.notna()).astype(object)
                    s2 = s2.map(lambda v: str(v) if v is not None and v == v else None)
                    nun = s2.nunique(dropna=True)
                    if nun > 50 and nun / n > 0.5:
                        types[c] = "text"
                    else:
                        types[c] = "categorical"
                    df[c] = s2

        # kolom numerik yang sebenarnya identifier
        if types[c] == "quantitative":
            nn = df[c].dropna()
            if (
                len(nn) > 20
                and _ID_NAME.search(c)
                and nn.nunique() / len(nn) > 0.95
                and (nn % 1 == 0).all()
            ):
                types[c] = "text"
                df[c] = df[c].map(lambda v: None if pd.isna(v) else str(int(v)))
                report["converted"].append({"column": c, "to": "text"})

    # missing values
    for c, t in types.items():
        miss = int(df[c].isna().sum())
        if not miss:
            continue
        if t in ("categorical", "text"):
            df[c] = df[c].fillna(UNKNOWN_LABEL)
            report["filled"].append(
                {"column": c, "strategy": f"Diisi '{UNKNOWN_LABEL}'", "count": miss}
            )
        else:
            report["numeric_missing"].append({"column": c, "count": miss})

    report["rows_after"] = int(len(df))
    report["cols_after"] = int(df.shape[1])
    return df, types, report
