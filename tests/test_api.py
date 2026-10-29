from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest
import yaml

from decisionpack.api import app as api_module
from decisionpack.api.app import app

CASE = Path(__file__).resolve().parents[1] / "cases" / "funnel-lab"
_CSV_PATH = CASE / "data" / "KAG_conversion_data.csv"
CSV = _CSV_PATH.read_bytes() if _CSV_PATH.exists() else b""


def spec_text(**changes: object) -> str:
    data = yaml.safe_load((CASE / "spec.yaml").read_text(encoding="utf-8"))
    data["tree"] = yaml.safe_load((CASE / "tree.yaml").read_text(encoding="utf-8"))
    del data["tree_file"]
    data.update(changes)
    return yaml.safe_dump(data, sort_keys=False)


@pytest.fixture
async def client():
    api_module.JOBS.clear()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def submit(client: httpx.AsyncClient, spec: str | bytes, data: bytes = CSV):
    return await client.post(
        "/runs",
        files={"spec": ("spec.yaml", spec, "text/yaml"), "data": ("d.csv", data, "text/csv")},
    )


async def wait_for(client: httpx.AsyncClient, job_id: str, timeout: float = 60.0) -> dict:
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        body = (await client.get(f"/runs/{job_id}")).json()
        if body["status"] in ("done", "failed"):
            return body
        assert asyncio.get_running_loop().time() < deadline, "job did not finish"
        await asyncio.sleep(0.05)


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


async def test_openapi_documents_every_endpoint(client):
    schema = (await client.get("/openapi.json")).json()
    paths = set(schema["paths"])
    assert {
        "/runs",
        "/runs/{job_id}",
        "/runs/{job_id}/result",
        "/runs/{job_id}/memo",
        "/runs/{job_id}/waterfall.svg",
        "/runs/{job_id}/tree.svg",
        "/runs/{job_id}/deck.pptx",
        "/health",
    } <= paths
    assert "ResultOut" in schema["components"]["schemas"]
    assert (await client.get("/docs")).status_code == 200


async def test_full_job_lifecycle(client):
    created = await submit(client, spec_text())
    assert created.status_code == 202
    body = created.json()
    assert body["status"] in ("queued", "running", "done")
    assert body["status_url"].endswith(f"/runs/{body['id']}")

    final = await wait_for(client, body["id"])
    assert final["status"] == "done" and final["error"] is None

    result = (await client.get(f"/runs/{body['id']}/result")).json()
    assert result["metric"]["gap"] == pytest.approx(48.02, abs=0.005)
    assert result["observational"] is True
    assert sum(result["bridge"]["shapley"].values()) == pytest.approx(result["metric"]["gap"])
    assert all(r["low"] <= r["base"] <= r["high"] for r in result["recommendations"])
    assert result["tree"]["mece_problems"] == []


async def test_files_are_served_with_the_right_types(client):
    job_id = (await submit(client, spec_text())).json()["id"]
    await wait_for(client, job_id)
    memo = await client.get(f"/runs/{job_id}/memo")
    assert memo.status_code == 200 and memo.text.startswith("# ")
    svg = await client.get(f"/runs/{job_id}/waterfall.svg")
    assert svg.headers["content-type"].startswith("image/svg+xml") and "<svg" in svg.text
    assert (await client.get(f"/runs/{job_id}/tree.svg")).status_code == 200
    deck = await client.get(f"/runs/{job_id}/deck.pptx")
    assert deck.status_code == 200 and deck.content[:2] == b"PK"


async def test_result_before_completion_is_409_or_ready(client):
    job_id = (await submit(client, spec_text())).json()["id"]
    first = await client.get(f"/runs/{job_id}/result")
    assert first.status_code in (200, 409)
    await wait_for(client, job_id)


async def test_unknown_run_is_404(client):
    assert (await client.get("/runs/nope")).status_code == 404
    assert (await client.get("/runs/nope/result")).status_code == 404


async def test_bad_spec_fails_the_job_with_a_readable_error(client):
    job_id = (await submit(client, "title: only a title\n")).json()["id"]
    final = await wait_for(client, job_id)
    assert final["status"] == "failed" and "invalid spec" in final["error"]
    r = await client.get(f"/runs/{job_id}/result")
    assert r.status_code == 422 and "invalid spec" in r.json()["detail"]


async def test_invalid_yaml_fails_the_job(client):
    job_id = (await submit(client, "a: [")).json()["id"]
    final = await wait_for(client, job_id)
    assert final["status"] == "failed" and "invalid YAML" in final["error"]


async def test_tree_file_is_refused_over_the_api(client):
    data = yaml.safe_load((CASE / "spec.yaml").read_text(encoding="utf-8"))
    job_id = (await submit(client, yaml.safe_dump(data))).json()["id"]
    final = await wait_for(client, job_id)
    assert final["status"] == "failed" and "tree_file is not allowed" in final["error"]


async def test_unsafe_expression_is_refused(client):
    spec = spec_text(filter="__import__('os').system('echo x')")
    job_id = (await submit(client, spec)).json()["id"]
    final = await wait_for(client, job_id)
    assert final["status"] == "failed"
    assert "not allowed" in final["error"] or "only these functions" in final["error"]


async def test_unreadable_csv_fails_the_job(client):
    job_id = (await submit(client, spec_text(), data=b"a,b\n1,2,3,4\n\x00\x00")).json()["id"]
    final = await wait_for(client, job_id)
    assert final["status"] == "failed"


async def test_empty_upload_is_rejected_immediately(client):
    r = await submit(client, spec_text(), data=b"")
    assert r.status_code == 422 and "empty" in r.json()["detail"]


async def test_oversized_upload_is_rejected(client, monkeypatch):
    monkeypatch.setattr(api_module, "MAX_UPLOAD_BYTES", 1000)
    r = await submit(client, spec_text())
    assert r.status_code == 413


async def test_missing_part_is_a_validation_error(client):
    r = await client.post("/runs", files={"spec": ("s.yaml", b"x", "text/yaml")})
    assert r.status_code == 422


async def test_row_limit_is_enforced(client, monkeypatch):
    monkeypatch.setattr(api_module, "MAX_ROWS", 10)
    job_id = (await submit(client, spec_text())).json()["id"]
    final = await wait_for(client, job_id)
    assert final["status"] == "failed" and "limit" in final["error"]


async def test_oldest_jobs_are_evicted(client, monkeypatch):
    monkeypatch.setattr(api_module, "MAX_JOBS", 2)
    ids = []
    for _ in range(3):
        ids.append((await submit(client, "title: x\n")).json()["id"])
        await wait_for(client, ids[-1])
    assert (await client.get(f"/runs/{ids[0]}")).status_code == 404
    assert (await client.get(f"/runs/{ids[2]}")).status_code == 200
