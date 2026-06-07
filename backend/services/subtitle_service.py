import subprocess
import json
from pathlib import Path
from typing import List
from ..models import ScriptSegment


def get_audio_duration(audio_path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", audio_path],
        capture_output=True, text=True
    )
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])


def generate_srt(segments: List[ScriptSegment], audio_files: List[str], srt_path: str) -> str:
    """Generate SRT subtitle file with timing adjusted to actual audio duration."""
    lines = []
    current_time = 0.0

    for i, (segment, audio_file) in enumerate(zip(segments, audio_files)):
        audio_dur = get_audio_duration(audio_file)
        start = current_time
        end = current_time + audio_dur

        lines.append(str(i + 1))
        lines.append(f"{_format_time(start)} --> {_format_time(end)}")
        lines.append(segment.text)
        lines.append("")

        current_time = end

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return srt_path


def _format_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
