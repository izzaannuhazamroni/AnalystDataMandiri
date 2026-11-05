"""AutoAnalytica API — FastAPI."""
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import ai, config, datastore, supa
from .cleaning import LoadError
from .models import AskRequest, BatchQuery, ShareBatchQuery, ShareRequest, SingleQuery
from .pipeline import build_analysis, process_file
from .query import QueryError, run_chart_query

app = FastAPI(title="AutoAnalytica API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(QueryError)
async def _query_error(_, exc: QueryError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(supa.SupabaseError)
async def _supa_error(_, exc: supa.SupabaseError):
    return JSONResponse(status_code=502, content={"detail": f"Layanan penyimpanan bermasalah. {exc}"})


# ------------------------------------------------------------------------- auth
def current_user(authorization: str = Header(default="")) -> dict:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Token tidak ada.")
    user = supa.get_user(authorization[7:].strip())
    if not user:
        raise HTTPException(401, "Sesi tidak valid. Silakan login ulang.")
    return user


def owned_dataset(dataset_id: str, user: dict) -> dict:
    rows = supa.select("datasets", {"id": f"eq.{dataset_id}", "user_id": f"eq.{user['id']}", "select": "*"})
    if not rows:
        raise HTTPException(404, "Dataset tidak ditemukan.")
    return rows[0]


_ask_hits: dict[str, deque] = defaultdict(deque)


def _rate_limit(user_id: str) -> None:
    now = time.time()
    q = _ask_hits[user_id]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= config.ASK_RATE_LIMIT_PER_MIN:
        raise HTTPException(429, "Terlalu banyak pertanyaan. Coba lagi sebentar lagi.")
    q.append(now)


# ----------------------------------------------------------------------- health
@app.get("/health")
def health():
    return {"status": "ok", "ai_provider": config.AI_PROVIDER if ai.llm_available() else "none"}


# ---------------------------------------------------------------------- analyze
@app.post("/api/datasets/{dataset_id}/analyze")
def analyze(dataset_id: str, user: dict = Depends(current_user)):
    ds = owned_dataset(dataset_id, user)
    supa.update("datasets", {"id": f"eq.{dataset_id}"}, {"status": "processing", "error_message": None})
    try:
        content = supa.download(ds["file_path"])
        if len(content) > config.MAX_FILE_MB * 1024 * 1024:
            raise LoadError(f"Ukuran file melebihi {config.MAX_FILE_MB}MB.")
        df, types, columns, report = process_file(content, ds["file_name"])
        result = build_analysis(df, types, columns, report, ds["file_name"])
    except LoadError as exc:
        supa.update("datasets", {"id": f"eq.{dataset_id}"}, {"status": "failed", "error_message": str(exc)})
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        supa.update("datasets", {"id": f"eq.{dataset_id}"}, {"status": "failed", "error_message": "Gagal memproses data."})
        raise HTTPException(500, f"Gagal memproses data: {exc}") from exc

    datastore.evict(dataset_id)
    datastore.put(ds, df, types, columns)
    supa.update(
        "datasets",
        {"id": f"eq.{dataset_id}"},
        {
            "row_count": int(len(df)),
            "col_count": int(df.shape[1]),
            "schema_json": {"columns": columns, "cleaning": report},
            "status": "ready",
            "error_message": None,
        },
    )
    supa.delete("dashboards", {"dataset_id": f"eq.{dataset_id}"})
    title = ds["file_name"].rsplit(".", 1)[0]
    dash = supa.insert(
        "dashboards",
        {
            "dataset_id": dataset_id,
            "user_id": user["id"],
            "title": f"Dashboard {title}",
            "summary_text": result["narrative"],
            "kpi_json": result["kpis"],
        },
    )[0]
    rows = [{**c, "dashboard_id": dash["id"], "position": i} for i, c in enumerate(result["charts"])]
    if rows:
        supa.insert("charts", rows)
    return {
        "dashboard_id": dash["id"],
        "narrative_source": result["narrative_source"],
        "elapsed_sec": result["elapsed_sec"],
    }


# ------------------------------------------------------------------------ query
def _run_items(ds: dict, items, filters) -> dict:
    df, types, _ = datastore.get_frame(ds)
    f = filters.model_dump()
    out: dict = {}
    for it in items:
        spec = it.model_dump(exclude={"id"})
        try:
            out[it.id] = run_chart_query(df, types, spec, f)
        except QueryError as exc:
            out[it.id] = {"error": str(exc)}
    return out


@app.post("/api/query/batch")
def query_batch(body: BatchQuery, user: dict = Depends(current_user)):
    ds = owned_dataset(body.dataset_id, user)
    return {"results": _run_items(ds, body.items, body.filters)}


@app.post("/api/query")
def query_single(body: SingleQuery, user: dict = Depends(current_user)):
    ds = owned_dataset(body.dataset_id, user)
    df, types, _ = datastore.get_frame(ds)
    return run_chart_query(df, types, body.spec.model_dump(), body.filters.model_dump())


# -------------------------------------------------------------------------- ask
@app.post("/api/ask")
def ask(body: AskRequest, user: dict = Depends(current_user)):
    _rate_limit(user["id"])
    ds = owned_dataset(body.dataset_id, user)
    df, types, columns = datastore.get_frame(ds)

    raw = ai.llm_spec(body.question, columns)
    spec = ai.validate_spec(raw, columns) if raw else None
    source = "ai" if spec else "heuristic"
    if not spec:
        spec = ai.validate_spec(ai.heuristic_spec(body.question, columns), columns)
    if not spec:
        raise HTTPException(422, "Pertanyaan belum bisa diterjemahkan. Coba sebut nama kolom yang ingin dianalisis.")

    q_filters = ai.resolve_filters((raw or {}).get("filters"), columns) if source == "ai" else {}
    merged = body.filters.model_dump()
    if q_filters.get("categories"):
        merged["categories"] = (merged.get("categories") or []) + q_filters["categories"]
    spec_run = {k: v for k, v in spec.items() if k != "title"}
    data = run_chart_query(df, types, spec_run, merged)
    answer, ans_src = ai.describe_answer(body.question, spec, data)
    return {
        "spec": spec,
        "data": data,
        "answer": answer,
        "source": "ai" if (source == "ai" or ans_src == "ai") else "heuristic",
        "applied_filters": q_filters,
    }


# ------------------------------------------------------------------------ share
@app.post("/api/dashboards/{dashboard_id}/share")
def create_share(dashboard_id: str, body: ShareRequest, user: dict = Depends(current_user)):
    rows = supa.select("dashboards", {"id": f"eq.{dashboard_id}", "user_id": f"eq.{user['id']}", "select": "id"})
    if not rows:
        raise HTTPException(404, "Dashboard tidak ditemukan.")
    token = secrets.token_urlsafe(24)
    expires = (
        (datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)).isoformat()
        if body.expires_in_days
        else None
    )
    supa.update("dashboards", {"id": f"eq.{dashboard_id}"}, {"share_token": token, "share_expires_at": expires})
    return {"token": token, "expires_at": expires}


@app.delete("/api/dashboards/{dashboard_id}/share")
def revoke_share(dashboard_id: str, user: dict = Depends(current_user)):
    rows = supa.select("dashboards", {"id": f"eq.{dashboard_id}", "user_id": f"eq.{user['id']}", "select": "id"})
    if not rows:
        raise HTTPException(404, "Dashboard tidak ditemukan.")
    supa.update("dashboards", {"id": f"eq.{dashboard_id}"}, {"share_token": None, "share_expires_at": None})
    return {"ok": True}


def _shared_dashboard(token: str) -> dict:
    if len(token) < 16:
        raise HTTPException(404, "Link tidak valid.")
    rows = supa.select("dashboards", {"share_token": f"eq.{token}", "select": "*"})
    if not rows:
        raise HTTPException(404, "Link tidak valid atau sudah dicabut.")
    d = rows[0]
    exp: Optional[str] = d.get("share_expires_at")
    if exp and datetime.fromisoformat(exp.replace("Z", "+00:00")) < datetime.now(timezone.utc):
        raise HTTPException(410, "Link sudah kedaluwarsa.")
    return d


def _dataset_by_id(dataset_id: str) -> dict:
    rows = supa.select("datasets", {"id": f"eq.{dataset_id}", "select": "*"})
    if not rows:
        raise HTTPException(404, "Dataset tidak ditemukan.")
    return rows[0]


@app.get("/api/share/{token}")
def get_shared(token: str):
    d = _shared_dashboard(token)
    ds = _dataset_by_id(d["dataset_id"])
    charts = supa.select("charts", {"dashboard_id": f"eq.{d['id']}", "select": "*", "order": "position.asc"})
    return {
        "dashboard": {
            "id": d["id"],
            "title": d["title"],
            "summary_text": d["summary_text"],
            "kpi_json": d["kpi_json"],
            "created_at": d["created_at"],
        },
        "dataset": {
            "file_name": ds["file_name"],
            "row_count": ds["row_count"],
            "schema_json": ds["schema_json"],
        },
        "charts": charts,
    }


@app.post("/api/share/{token}/query/batch")
def shared_batch(token: str, body: ShareBatchQuery):
    d = _shared_dashboard(token)
    ds = _dataset_by_id(d["dataset_id"])
    return {"results": _run_items(ds, body.items, body.filters)}
