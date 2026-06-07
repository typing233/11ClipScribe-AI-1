import subprocess
from pathlib import Path
from typing import List
from ..models import ScriptSegment


def concat_audio_with_padding(
    audio_files: List[str],
    segments: List[ScriptSegment],
    output_path: str,
    video_duration: float
) -> str:
    """Concatenate audio segments with silence padding to align with video timing."""
    from .subtitle_service import get_audio_duration

    filter_parts = []
    inputs = []
    current_time = 0.0

    for i, (audio_file, segment) in enumerate(zip(audio_files, segments)):
        audio_dur = get_audio_duration(audio_file)
        inputs.extend(["-i", audio_file])
        filter_parts.append(f"[{i}:a]asetpts=PTS-STARTPTS[a{i}]")

    concat_input = "".join(f"[a{i}]" for i in range(len(audio_files)))
    filter_parts.append(f"{concat_input}concat=n={len(audio_files)}:v=0:a=1[out]")

    filter_complex = ";".join(filter_parts)

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-acodec", "libmp3lame", "-ar", "44100",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def compose_final_video(
    video_path: str,
    audio_path: str,
    srt_path: str,
    output_path: str
) -> str:
    """Compose final video with narration audio mixed and subtitles burned in."""
    srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-filter_complex",
        f"[0:a]volume=0.3[bg];[1:a]volume=1.0[narr];[bg][narr]amix=inputs=2:duration=first[aout]",
        "-map", "0:v",
        "-map", "[aout]",
        "-vf", f"subtitles={srt_escaped}:force_style='FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,MarginV=30'",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Fallback: try without original audio mixing (video might have no audio)
        cmd_fallback = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-map", "0:v",
            "-map", "1:a",
            "-vf", f"subtitles={srt_escaped}:force_style='FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,MarginV=30'",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            output_path
        ]
        subprocess.run(cmd_fallback, capture_output=True, check=True)

    return output_path
