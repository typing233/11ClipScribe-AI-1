from pydantic import BaseModel
from enum import Enum
from typing import Optional


class TaskStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    GENERATING_SCRIPT = "generating_script"
    EDITING_VIDEO = "editing_video"
    SYNTHESIZING_VOICE = "synthesizing_voice"
    ADDING_SUBTITLES = "adding_subtitles"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskInfo(BaseModel):
    task_id: str
    status: TaskStatus
    progress: int = 0
    message: str = ""
    output_file: Optional[str] = None
    error: Optional[str] = None


class ScriptSegment(BaseModel):
    text: str
    start_time: float
    end_time: float
    duration: float
