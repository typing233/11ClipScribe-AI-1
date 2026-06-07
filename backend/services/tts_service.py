import asyncio
import edge_tts
from pathlib import Path
from typing import List
from ..models import ScriptSegment
from ..config import TTS_VOICE, TTS_RATE


async def synthesize_segment(text: str, output_path: str, voice: str = None) -> str:
    """Synthesize a single text segment to audio file."""
    voice = voice or TTS_VOICE
    communicate = edge_tts.Communicate(text, voice, rate=TTS_RATE)
    await communicate.save(output_path)
    return output_path


async def synthesize_all_segments(
    segments: List[ScriptSegment],
    output_dir: Path
) -> List[str]:
    """Synthesize all script segments to individual audio files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_files = []

    for i, segment in enumerate(segments):
        output_path = str(output_dir / f"segment_{i:03d}.mp3")
        await synthesize_segment(segment.text, output_path)
        audio_files.append(output_path)

    return audio_files


def run_tts(segments: List[ScriptSegment], output_dir: Path) -> List[str]:
    """Synchronous wrapper for TTS synthesis."""
    return asyncio.run(synthesize_all_segments(segments, output_dir))
