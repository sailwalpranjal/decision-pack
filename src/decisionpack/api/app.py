"""FastAPI app.

A run is a job: ``POST /runs`` accepts a spec and a CSV and returns at once with an id; the
analysis runs in a worker thread; ``GET /runs/{id}`` reports progress; the result and the files
of the pack are fetched when the job is done. Jobs live in memory and the oldest are evicted,
so this is a convenience for a single user or a demo, not a durable service.
"""

from __future__ import annotations

import asyncio
import io
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import pandas as pd
import yaml
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, Response

from decisionpack import __version__
from decisionpack.api.models import (
    ErrorOut,
    JobState,
    ResultOut,
    RunCreated,
    RunStatus,
)
from decisionpack.core.expr import ExpressionError
from decisionpack.core.sizing import MissingUncertaintyError
from decisionpack.core.tree import TreeError
from decisionpack.pack import write_pack
from decisionpack.run import AnalysisError, run_analysis
from decisionpack.serialize import result_to_dict
from decisionpack.spec import SpecError, parse_spec

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_ROWS = 2_000_000
MAX_JOBS = 100

USER_ERRORS = (SpecError, AnalysisError, ExpressionError, TreeError, MissingUncertaintyError)

app = FastAPI(
    title="decision-pack API",
    version=__version__,
    summary="Explain a metric gap: bridge, segment scan, hypothesis tree, sized recommendations.",
    description=(
        "Upload a spec (YAML) and a CSV, poll the job, then fetch the result and the files of "
        "the pack. Results are decision support for analysts and describe observational data; "
        "they do not establish causes."
    ),
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@dataclass
class Job:
    id: str
    status: JobState = "queued"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None
    result: dict | None = None  # type: ignore[type-arg]
    folder: Path | None = None
    task: asyncio.Task[None] | None = None


JOBS: dict[str, Job] = {}


def _evict() -> None:
    while len(JOBS) > MAX_JOBS:
        oldest = min(JOBS.values(), key=lambda j: j.created_at)
        JOBS.pop(oldest.id, None)


async def _read_limited(upload: UploadFile, what: str) -> bytes:
    data = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"{what} is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
    if not data:
        raise HTTPException(422, f"{what} is empty")
    return data


def _compute(job: Job, spec_text: str, csv_bytes: bytes) -> None:
    try:
        data = yaml.safe_load(spec_text)
        if isinstance(data, dict) and data.get("tree_file"):
            raise SpecError(
                "tree_file is not allowed over the API (the server does not read files); "
                "put the tree inline under 'tree'"
            )
        spec = parse_spec(data)
        df = pd.read_csv(io.BytesIO(csv_bytes))
        if len(df) > MAX_ROWS:
            raise AnalysisError(f"the CSV has {len(df)} rows; the limit is {MAX_ROWS}")
        result = run_analysis(spec, df)
        folder = Path(tempfile.mkdtemp(prefix=f"decisionpack-{job.id}-"))
        write_pack(result, folder)
        job.result = result_to_dict(result)
        job.folder = folder
        job.status = "done"
    except yaml.YAMLError as exc:
        job.status, job.error = "failed", f"invalid YAML: {exc}"
    except USER_ERRORS as exc:
        job.status, job.error = "failed", str(exc)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        job.status, job.error = "failed", f"could not read the CSV: {exc}"
    except Exception as exc:  # pragma: no cover - last resort so a job never hangs in "running"
        job.status, job.error = "failed", f"unexpected error: {type(exc).__name__}"


async def _run_job(job: Job, spec_text: str, csv_bytes: bytes) -> None:
    job.status = "running"
    await asyncio.to_thread(_compute, job, spec_text, csv_bytes)


def _get(job_id: str) -> Job:
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(404, "no such run")
    return job


def _done(job_id: str) -> Job:
    job = _get(job_id)
    if job.status in ("queued", "running"):
        raise HTTPException(409, f"the run is {job.status}; try again shortly")
    if job.status == "failed":
        raise HTTPException(422, job.error or "the run failed")
    return job


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.post(
    "/runs",
    status_code=202,
    response_model=RunCreated,
    responses={413: {"model": ErrorOut}, 422: {"model": ErrorOut}},
    tags=["runs"],
    summary="Start an analysis",
)
async def create_run(
    request: Request,
    spec: Annotated[UploadFile, File(description="Spec YAML. Tree must be inline.")],
    data: Annotated[UploadFile, File(description="CSV file")],
) -> RunCreated:
    spec_text = (await _read_limited(spec, "spec")).decode("utf-8", errors="replace")
    csv_bytes = await _read_limited(data, "data")
    job = Job(id=uuid.uuid4().hex[:12])
    JOBS[job.id] = job
    _evict()
    job.task = asyncio.create_task(_run_job(job, spec_text, csv_bytes))
    return RunCreated(
        id=job.id, status=job.status, status_url=str(request.url_for("get_run", job_id=job.id))
    )


@app.get("/runs/{job_id}", response_model=RunStatus, tags=["runs"], name="get_run")
def get_run(job_id: str) -> RunStatus:
    job = _get(job_id)
    return RunStatus(id=job.id, status=job.status, created_at=job.created_at, error=job.error)


@app.get("/runs/{job_id}/result", response_model=ResultOut, tags=["runs"])
def get_result(job_id: str) -> ResultOut:
    job = _done(job_id)
    assert job.result is not None
    return ResultOut.model_validate(job.result)


def _file(job_id: str, name: str, media: str) -> Response:
    job = _done(job_id)
    assert job.folder is not None
    path = job.folder / name
    if not path.exists():
        raise HTTPException(404, f"this run has no {name}")
    return FileResponse(path, media_type=media, filename=name)


@app.get("/runs/{job_id}/memo", response_class=PlainTextResponse, tags=["files"])
def get_memo(job_id: str) -> Response:
    return _file(job_id, "memo.md", "text/markdown; charset=utf-8")


@app.get("/runs/{job_id}/waterfall.svg", tags=["files"])
def get_waterfall(job_id: str) -> Response:
    return _file(job_id, "waterfall.svg", "image/svg+xml")


@app.get("/runs/{job_id}/tree.svg", tags=["files"])
def get_tree(job_id: str) -> Response:
    return _file(job_id, "tree.svg", "image/svg+xml")


@app.get("/runs/{job_id}/deck.pptx", tags=["files"])
def get_deck(job_id: str) -> Response:
    return _file(
        job_id,
        "deck.pptx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
