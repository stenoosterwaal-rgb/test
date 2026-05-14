"""ASI-Evolve web server — FastAPI backend with WebSocket log streaming."""

import asyncio
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Ensure repo root is on the path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

app = FastAPI(title="ASI-Evolve")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ---------------------------------------------------------------------------
# Global run state
# ---------------------------------------------------------------------------

class RunState:
    def __init__(self):
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.best_score: Optional[float] = None
        self.best_code: Optional[str] = None
        self.step_count = 0
        self.log_queue: asyncio.Queue = asyncio.Queue()
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def reset(self):
        self.stop_event = threading.Event()
        self.best_score = None
        self.best_code = None
        self.step_count = 0

run_state = RunState()

# ---------------------------------------------------------------------------
# Custom logging handler — bridges Python logging → WebSocket queue
# ---------------------------------------------------------------------------

class WSLogHandler(logging.Handler):
    """Push log records into the asyncio queue so WebSocket clients receive them."""

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            loop = run_state.loop
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(run_state.log_queue.put(msg), loop)
        except Exception:
            pass

_ws_handler = WSLogHandler()
_ws_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))

# ---------------------------------------------------------------------------
# Pipeline runner (executed in background thread)
# ---------------------------------------------------------------------------

def _push_log(level: str, message: str):
    """Thread-safe log push to WebSocket queue."""
    from datetime import datetime
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"{ts} [{level}] {message}"
    loop = run_state.loop
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(run_state.log_queue.put(line), loop)


def _run_pipeline(steps: int):
    """Executed in a background thread — runs the ASI-Evolve pipeline."""
    root_logger = logging.getLogger()
    root_logger.addHandler(_ws_handler)
    root_logger.setLevel(logging.INFO)

    eval_script = str(ROOT / "experiments" / "circle_packing_demo" / "eval.sh")

    try:
        _push_log("INFO", "Initialising ASI-Evolve pipeline…")
        _push_log("INFO", f"Experiment: circle_packing_demo | Steps: {steps}")

        # Import here so startup is fast
        from pipeline.main import Pipeline

        config_path = str(ROOT / "web_config.yaml")
        pipeline = Pipeline(config_path=config_path, experiment_name="circle_packing_demo")

        # Read task description once
        input_file = ROOT / "experiments" / "circle_packing_demo" / "input.md"
        task_description = input_file.read_text(encoding="utf-8") if input_file.exists() else ""

        # Evaluate initial program seed (if not already done)
        if not pipeline.is_resume and not pipeline.initial_node_created:
            _push_log("INFO", "Evaluating baseline program…")
            pipeline._create_initial_node(task_description, eval_script)

        # Evolution loop — check stop_event between steps
        for step_idx in range(steps):
            if run_state.stop_event.is_set():
                _push_log("INFO", "Run stopped by user.")
                break

            _push_log("INFO", f"─── Evolution step {step_idx + 1}/{steps} ───")
            pipeline.run_step(
                task_description=task_description,
                eval_script=eval_script,
            )
            run_state.step_count = step_idx + 1

            # Update best result
            try:
                all_nodes = pipeline.database.get_all()
                if all_nodes:
                    best = max(all_nodes, key=lambda n: n.score if n.score is not None else -1e9)
                    if best.score is not None:
                        run_state.best_score = best.score
                        run_state.best_code = best.code
                        _push_log("INFO", f"Best score so far: {best.score:.6f}")
            except Exception:
                pass

        _push_log("INFO", "Evolution run complete.")

    except Exception as exc:
        import traceback as tb
        _push_log("ERROR", f"Pipeline error: {exc}")
        _push_log("ERROR", tb.format_exc())
    finally:
        root_logger.removeHandler(_ws_handler)
        run_state.running = False
        _push_log("INFO", "__DONE__")   # sentinel so the UI knows the run ended

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def _startup():
    run_state.loop = asyncio.get_event_loop()


@app.get("/", response_class=HTMLResponse)
async def index():
    html_file = STATIC_DIR / "index.html"
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@app.get("/api/status")
async def status():
    api_key_set = bool(os.environ.get("GROQ_API_KEY"))
    return {
        "api_key_set": api_key_set,
        "running": run_state.running,
        "step_count": run_state.step_count,
        "best_score": run_state.best_score,
    }


@app.post("/api/run/start")
async def start_run(payload: Optional[Dict[str, Any]] = None):
    if run_state.running:
        return JSONResponse({"error": "A run is already in progress."}, status_code=409)

    if not os.environ.get("GROQ_API_KEY"):
        return JSONResponse(
            {"error": "GROQ_API_KEY is not set. Get a free key at console.groq.com, then add it in Railway → Variables."},
            status_code=400,
        )

    steps = (payload or {}).get("steps", 10)
    run_state.reset()
    run_state.running = True

    # Seed cognition store on first run
    cognition_dir = ROOT / "experiments" / "circle_packing_demo" / "cognition_data"
    if not cognition_dir.exists():
        _push_log("INFO", "Seeding cognition store (first run only)…")
        try:
            import subprocess
            subprocess.run(
                [sys.executable, str(ROOT / "experiments" / "circle_packing_demo" / "init_cognition.py")],
                cwd=str(ROOT),
                timeout=120,
                check=False,
            )
        except Exception as e:
            _push_log("WARNING", f"Cognition seeding failed (will continue): {e}")

    run_state.thread = threading.Thread(target=_run_pipeline, args=(steps,), daemon=True)
    run_state.thread.start()

    return {"status": "started", "steps": steps}


@app.post("/api/run/stop")
async def stop_run():
    if not run_state.running:
        return {"status": "not_running"}
    run_state.stop_event.set()
    return {"status": "stopping"}


@app.get("/api/run/results")
async def results():
    return {
        "running": run_state.running,
        "step_count": run_state.step_count,
        "best_score": run_state.best_score,
        "best_code": run_state.best_code,
    }


@app.websocket("/api/run/logs")
async def logs_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            try:
                msg = await asyncio.wait_for(run_state.log_queue.get(), timeout=1.0)
                await websocket.send_text(msg)
                if msg.endswith("__DONE__"):
                    break
            except asyncio.TimeoutError:
                try:
                    await websocket.send_text("__PING__")
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
