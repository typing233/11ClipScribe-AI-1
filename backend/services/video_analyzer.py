import subprocess
import json
import base64
from pathlib import Path
from typing import List, Tuple


def get_video_duration(video_path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path],
        capture_output=True, text=True
    )
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])


def extract_frames(video_path: str, num_frames: int = 8) -> List[Tuple[float, str]]:
    """Extract evenly-spaced frames from video, return list of (timestamp, base64_jpg)."""
    duration = get_video_duration(video_path)
    interval = duration / (num_frames + 1)
    frames = []

    for i in range(1, num_frames + 1):
        timestamp = interval * i
        result = subprocess.run(
            [
                "ffmpeg", "-ss", str(timestamp), "-i", video_path,
                "-vframes", "1", "-f", "image2pipe",
                "-vcodec", "mjpeg", "-q:v", "5", "pipe:1"
            ],
            capture_output=True
        )
        if result.returncode == 0 and result.stdout:
            b64 = base64.b64encode(result.stdout).decode("utf-8")
            frames.append((timestamp, b64))

    return frames


def get_video_info(video_path: str) -> dict:
    """Get basic video metadata."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", video_path],
        capture_output=True, text=True
    )
    return json.loads(result.stdout)
