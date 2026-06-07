import asyncio
import subprocess
import json
import edge_tts
from pathlib import Path
from typing import List
from ..models import ScriptSegment
from ..config import TTS_VOICE, TTS_RATE


def _get_audio_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
        capture_output=True, text=True
    )
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])


def _compress_audio_to_fit(input_path: str, output_path: str, target_duration: float):
    """Speed up audio using atempo so it fits within target_duration."""
    actual = _get_audio_duration(input_path)
    ratio = actual / target_duration

    # atempo only accepts [0.5, 100.0]; chain filters for extreme cases
    filters = []
    remaining = ratio
    while remaining > 2.0:
        filters.append("atempo=2.0")
        remaining /= 2.0
    if remaining > 1.0:
        filters.append(f"atempo={remaining:.4f}")

    if not filters:
        # No compression needed, just copy
        subprocess.run(["cp", input_path, output_path], check=True)
        return

    filter_str = ",".join(filters)
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-af", filter_str,
        "-acodec", "libmp3lame", "-ar", "44100",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Audio compression failed: {result.stderr}")


async def synthesize_segment(text: str, output_path: str, voice: str = None) -> str:
    voice = voice or TTS_VOICE
    communicate = edge_tts.Communicate(text, voice, rate=TTS_RATE)
    await communicate.save(output_path)
    return output_path


async def synthesize_all_segments(
    segments: List[ScriptSegment],
    output_dir: Path
) -> List[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_files = []

    for i, segment in enumerate(segments):
        raw_path = str(output_dir / f"segment_{i:03d}_raw.mp3")
        final_path = str(output_dir / f"segment_{i:03d}.mp3")

        await synthesize_segment(segment.text, raw_path)

        max_duration = segment.end_time - segment.start_time
        actual_duration = _get_audio_duration(raw_path)

        if actual_duration > max_duration + 0.1:
            _compress_audio_to_fit(raw_path, final_path, max_duration)
        else:
            subprocess.run(["mv", raw_path, final_path], check=True)

        audio_files.append(final_path)

    return audio_files


def run_tts(segments: List[ScriptSegment], output_dir: Path) -> List[str]:
    """Synchronous wrapper for TTS synthesis."""
    return asyncio.run(synthesize_all_segments(segments, output_dir))
