"""Tes alur API end-to-end dengan Supabase ditiru (tanpa jaringan)."""
import pytest
from fastapi.testclient import TestClient

from app import datastore, main, supa

CSV = open(__file__.replace("backend/tests/test_api.py", "sample_data/penjualan_contoh.csv"), "rb").read()


class FakeDB:
    def __init__(self):
        self.t = {"datasets": [], "dashboards": [], "charts": []}
        self.t["datasets"].append(
            {"id": "ds1", "user_id": "u1", "file_name": "penjualan_contoh.csv", "file_path": "u1/x.csv", "status": "uploaded"}
        )

    @staticmethod
    def _match(row, params):
        for k, v in params.items():
            if k in ("select", "order"):
                continue
            if v.startswith("eq.") and str(row.get(k)) != v[3:]:
                return False
        return True

    def select(self, table, params):
        return [r for r in self.t[table] if self._match(r, params)]

    def insert(self, table, rows):
        rows = rows if isinstance(rows, list) else [rows]
        out = []
        for r in rows:
            r = {**r, "id": r.get("id") or f"{table}{len(self.t[table]) + 1}", "created_at": "2026-01-01T00:00:00Z"}
            self.t[table].append(r)
            out.append(r)
        return out

    def update(self, table, params, values):
        hit = [r for r in self.t[table] if self._match(r, params)]
        for r in hit:
            r.update(values)
        return hit

    def delete(self, table, params):
        self.t[table] = [r for r in self.t[table] if not self._match(r, params)]


@pytest.fixture()
def client(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(supa, "get_user", lambda tok: {"id": "u1", "email": "a@b.c"} if tok == "good" else None)
    monkeypatch.setattr(supa, "download", lambda path: CSV)
    for fn in ("select", "insert", "update", "delete"):
        monkeypatch.setattr(supa, fn, getattr(db, fn))
    datastore._cache.clear()
    c = TestClient(main.app)
    c.db = db
    return c


H = {"Authorization": "Bearer good"}


def test_auth_required(client):
    assert client.post("/api/datasets/ds1/analyze").status_code == 401
    assert client.post("/api/datasets/ds1/analyze", headers={"Authorization": "Bearer bad"}).status_code == 401


def test_full_flow(client):
    r = client.post("/api/datasets/ds1/analyze", headers=H)
    assert r.status_code == 200, r.text
    assert client.db.t["datasets"][0]["status"] == "ready"
    assert client.db.t["datasets"][0]["row_count"] == 3000
    assert len(client.db.t["charts"]) >= 4
    dash = client.db.t["dashboards"][0]
    assert dash["summary_text"] and dash["kpi_json"]

    # batch query dengan filter
    items = [
        {"id": c["id"], "chart_type": c["chart_type"], "x_axis": c["x_axis"], "y_axis": c["y_axis"],
         "aggregation": c["aggregation"], "measures": c["styling_json"].get("measures")}
        for c in client.db.t["charts"]
    ]
    body = {"dataset_id": "ds1", "items": items, "filters": {"categories": [{"column": "Cabang", "values": ["Madiun"]}]}}
    res = client.post("/api/query/batch", headers=H, json=body).json()["results"]
    assert all("error" not in v for v in res.values())

    # error query -> ditampilkan per-chart, bukan 500
    bad = {"dataset_id": "ds1", "items": [{"id": "z", "chart_type": "scatter", "x_axis": "Cabang", "y_axis": "Omset"}]}
    assert "error" in client.post("/api/query/batch", headers=H, json=bad).json()["results"]["z"]

    # ask my data
    a = client.post("/api/ask", headers=H, json={"dataset_id": "ds1", "question": "Total omset per cabang"}).json()
    assert a["spec"]["x_axis"] == "Cabang" and a["data"]["labels"]

    # kepemilikan dataset
    assert client.post("/api/ask", headers=H, json={"dataset_id": "other", "question": "halo"}).status_code == 404

    # share: buat, baca publik, query publik, cabut
    tok = client.post(f"/api/dashboards/{dash['id']}/share", headers=H, json={"expires_in_days": 7}).json()["token"]
    pub = client.get(f"/api/share/{tok}").json()
    assert pub["charts"] and "file_path" not in pub["dataset"] and "user_id" not in pub["dashboard"]
    sb = client.post(f"/api/share/{tok}/query/batch", json={"items": items[:1]})
    assert sb.status_code == 200
    assert client.delete(f"/api/dashboards/{dash['id']}/share", headers=H).status_code == 200
    assert client.get(f"/api/share/{tok}").status_code == 404


def test_expired_share(client):
    client.post("/api/datasets/ds1/analyze", headers=H)
    dash = client.db.t["dashboards"][0]
    dash["share_token"] = "t" * 32
    dash["share_expires_at"] = "2020-01-01T00:00:00+00:00"
    assert client.get(f"/api/share/{'t' * 32}").status_code == 410
