import subprocess
import json
from pathlib import Path
from typing import List
from ..models import ScriptSegment


def _get_audio_duration(audio_path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", audio_path],
        capture_output=True, text=True
    )
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])


def _video_has_audio(video_path: str) -> bool:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams",
         "-select_streams", "a", video_path],
        capture_output=True, text=True
    )
    info = json.loads(result.stdout)
    return len(info.get("streams", [])) > 0


def concat_audio_with_padding(
    audio_files: List[str],
    segments: List[ScriptSegment],
    output_path: str,
    video_duration: float
) -> str:
    """
    Build a single narration track where each segment starts at its script start_time.
    Gaps between segments are filled with silence. Total length = video_duration.
    """
    n = len(audio_files)
    input_args = []
    filter_parts = []
    segment_labels = []

    for i, (audio_file, segment) in enumerate(zip(audio_files, segments)):
        audio_dur = _get_audio_duration(audio_file)
        input_args.extend(["-i", audio_file])

        # Delay each segment to its start_time using adelay (milliseconds)
        delay_ms = int(segment.start_time * 1000)
        filter_parts.append(
            f"[{i}:a]adelay={delay_ms}|{delay_ms}[a{i}]"
        )
        segment_labels.append(f"[a{i}]")

    # Mix all delayed segments together (they don't overlap by design)
    mix_inputs = "".join(segment_labels)
    filter_parts.append(
        f"{mix_inputs}amix=inputs={n}:duration=longest:normalize=0[mixed]"
    )

    # Pad/trim to exact video duration
    total_samples = int(video_duration * 44100)
    filter_parts.append(
        f"[mixed]apad=whole_dur={video_duration}[padded]"
    )
    filter_parts.append(
        f"[padded]atrim=0:{video_duration}[out]"
    )

    filter_complex = ";".join(filter_parts)

    cmd = ["ffmpeg", "-y"] + input_args + [
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-acodec", "libmp3lame", "-ar", "44100",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Audio concat failed: {result.stderr}")
    return output_path


def compose_final_video(
    video_path: str,
    audio_path: str,
    srt_path: str,
    output_path: str,
    target_duration: float = None
) -> str:
    """
    Compose final video:
    - Narration audio replaces/mixes with original track
    - Subtitles burned in
    - Output duration = max(video_duration, narration_duration) — never truncated
    """
    from .video_analyzer import get_video_duration

    video_dur = get_video_duration(video_path)
    narr_dur = _get_audio_duration(audio_path)
    final_dur = target_duration or max(video_dur, narr_dur)

    srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
    subtitle_filter = f"subtitles={srt_escaped}:force_style='FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,MarginV=30'"

    has_audio = _video_has_audio(video_path)

    if has_audio:
        # Mix original audio (lowered) with narration
        filter_complex = (
            f"[0:a]volume=0.3[bg];"
            f"[1:a]volume=1.0[narr];"
            f"[bg][narr]amix=inputs=2:duration=longest:normalize=0[aout]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-vf", subtitle_filter,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-t", str(final_dur),
            output_path
        ]
    else:
        # No original audio — use narration directly
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-map", "0:v",
            "-map", "1:a",
            "-vf", subtitle_filter,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-t", str(final_dur),
            output_path
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Video compose failed: {result.stderr}")

    return output_path
