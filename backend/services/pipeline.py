import traceback
from pathlib import Path
from typing import Optional

from ..config import OUTPUT_DIR
from ..models import ScriptSegment, TaskStatus
from .video_analyzer import extract_frames, get_video_duration
from .script_generator import generate_script
from .tts_service import run_tts
from .subtitle_service import generate_srt
from .video_editor import concat_audio_with_padding, compose_final_video


def run_pipeline(
    task_id: str,
    video_path: str,
    user_hint: Optional[str],
    status_callback=None
):
    """Run the full video commentary pipeline."""
    work_dir = OUTPUT_DIR / task_id
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Step 1: Analyze video
        if status_callback:
            status_callback(TaskStatus.ANALYZING, 10, "正在分析视频内容...")

        duration = get_video_duration(video_path)
        frames = extract_frames(video_path, num_frames=min(8, max(4, int(duration / 10))))

        # Step 2: Generate script
        if status_callback:
            status_callback(TaskStatus.GENERATING_SCRIPT, 30, "正在生成解说文案...")

        segments = generate_script(frames, duration, user_hint)

        # Step 3: TTS synthesis
        if status_callback:
            status_callback(TaskStatus.SYNTHESIZING_VOICE, 50, "正在合成配音...")

        tts_dir = work_dir / "tts"
        audio_files = run_tts(segments, tts_dir)

        # Step 4: Generate subtitles
        if status_callback:
            status_callback(TaskStatus.ADDING_SUBTITLES, 70, "正在生成字幕...")

        srt_path = str(work_dir / "subtitles.srt")
        generate_srt(segments, audio_files, srt_path)

        # Step 5: Compose final video
        if status_callback:
            status_callback(TaskStatus.EDITING_VIDEO, 85, "正在合成最终视频...")

        merged_audio = str(work_dir / "narration.mp3")
        concat_audio_with_padding(audio_files, segments, merged_audio, duration)

        output_file = str(work_dir / "final_output.mp4")
        compose_final_video(video_path, merged_audio, srt_path, output_file, target_duration=duration)

        if status_callback:
            status_callback(TaskStatus.COMPLETED, 100, "处理完成！", output_file)

        return output_file

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        if status_callback:
            status_callback(TaskStatus.FAILED, 0, "处理失败", error=error_msg)
        raise
