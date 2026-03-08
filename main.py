import asyncio
from uuid import uuid4
from pathlib import Path

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from agents.orchestrator import Orchestrator

app = FastAPI(title="GitArch")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

jobs: dict[str, dict] = {}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/analyze")
async def analyze(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    repo_url = body.get("repo_url", "").strip()

    if not repo_url or "github.com" not in repo_url:
        return JSONResponse({"error": "Please provide a valid GitHub URL"}, status_code=400)

    job_id = uuid4().hex[:12]
    jobs[job_id] = {"status": "processing", "progress": 0, "phase": "Starting...", "result": None, "error": None}

    background_tasks.add_task(_run_analysis, job_id, repo_url)
    return {"job_id": job_id}


@app.get("/status/{job_id}")
async def status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return {
        "status": job["status"],
        "progress": job["progress"],
        "phase": job["phase"],
        "error": job["error"],
    }


@app.get("/result/{job_id}", response_class=HTMLResponse)
async def result(request: Request, job_id: str):
    job = jobs.get(job_id)
    if not job:
        return HTMLResponse("<h1>Job not found</h1>", status_code=404)
    if job["status"] != "completed":
        return HTMLResponse("<h1>Analysis not ready yet</h1>", status_code=202)

    return templates.TemplateResponse("report.html", {
        "request": request,
        "repo_url": job.get("repo_url", ""),
        **job["result"],
    })


async def _run_analysis(job_id: str, repo_url: str):
    jobs[job_id]["repo_url"] = repo_url

    async def on_progress(value: int, phase: str):
        jobs[job_id]["progress"] = value
        jobs[job_id]["phase"] = phase

    try:
        orchestrator = Orchestrator()
        result = await orchestrator.analyze(repo_url, on_progress=on_progress)
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = result
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
