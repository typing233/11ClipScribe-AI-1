import uuid
import shutil
from pathlib import Path
from typing import Optional
from threading import Thread
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .config import UPLOAD_DIR, OUTPUT_DIR, MAX_UPLOAD_SIZE
from .models import TaskInfo, TaskStatus
from .services.pipeline import run_pipeline

tasks: dict[str, TaskInfo] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    UPLOAD_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    yield


app = FastAPI(title="ClipScribe AI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _update_task(task_id: str):
    def callback(status: TaskStatus, progress: int, message: str, output_file: str = None, error: str = None):
        tasks[task_id] = TaskInfo(
            task_id=task_id,
            status=status,
            progress=progress,
            message=message,
            output_file=output_file,
            error=error
        )
    return callback


@app.post("/api/upload")
async def upload_video(
    file: UploadFile = File(...),
    hint: Optional[str] = Form(None)
):
    """Upload video and start processing pipeline."""
    if file.size and file.size > MAX_UPLOAD_SIZE:
        raise HTTPException(413, "文件过大，最大支持500MB")

    task_id = str(uuid.uuid4())[:8]
    ext = Path(file.filename).suffix or ".mp4"
    video_path = UPLOAD_DIR / f"{task_id}{ext}"

    with open(video_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)

    tasks[task_id] = TaskInfo(
        task_id=task_id,
        status=TaskStatus.PENDING,
        progress=0,
        message="任务已创建，等待处理..."
    )

    thread = Thread(
        target=run_pipeline,
        args=(task_id, str(video_path), hint, _update_task(task_id)),
        daemon=True
    )
    thread.start()

    return {"task_id": task_id, "message": "任务已提交"}


@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """Get task processing status."""
    if task_id not in tasks:
        raise HTTPException(404, "任务不存在")
    return tasks[task_id]


@app.get("/api/download/{task_id}")
async def download_result(task_id: str):
    """Download the processed video."""
    if task_id not in tasks:
        raise HTTPException(404, "任务不存在")

    task = tasks[task_id]
    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(400, "任务尚未完成")

    if not task.output_file or not Path(task.output_file).exists():
        raise HTTPException(500, "输出文件不存在")

    return FileResponse(
        task.output_file,
        media_type="video/mp4",
        filename=f"clipscribe_{task_id}.mp4"
    )


app.mount("/", StaticFiles(directory=str(Path(__file__).parent.parent / "frontend"), html=True), name="frontend")
