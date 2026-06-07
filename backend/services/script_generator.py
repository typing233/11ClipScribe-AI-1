import json
from typing import List, Tuple, Optional
from openai import OpenAI
from ..config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from ..models import ScriptSegment


def generate_script(
    frames: List[Tuple[float, str]],
    video_duration: float,
    user_hint: Optional[str] = None
) -> List[ScriptSegment]:
    """Generate commentary script based on video frames using LLM."""
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

    messages = _build_prompt(frames, video_duration, user_hint)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=2000,
    )

    content = response.choices[0].message.content
    return _parse_script(content, video_duration)


def _build_prompt(
    frames: List[Tuple[float, str]],
    video_duration: float,
    user_hint: Optional[str]
) -> list:
    system_msg = (
        "你是一位专业的影视解说文案创作者。根据提供的视频截图和信息，"
        "生成贴合画面的中文解说文案。\n\n"
        "要求：\n"
        "1. 文案要有叙事感，像讲故事一样娓娓道来\n"
        "2. 每个段落对应一个时间段，确保总时长覆盖整个视频\n"
        "3. 每段文案朗读时长大约为对应时间段的长度（按每秒4个汉字估算）\n"
        "4. 输出严格的JSON数组格式\n\n"
        f"视频总时长: {video_duration:.1f}秒\n\n"
        "输出格式（纯JSON，不要markdown代码块）:\n"
        '[{"start": 0.0, "end": 5.0, "text": "解说文字..."}, ...]'
    )

    user_content = []

    if user_hint:
        user_content.append({
            "type": "text",
            "text": f"影片信息补充: {user_hint}"
        })

    user_content.append({
        "type": "text",
        "text": f"以下是从视频中均匀抽取的{len(frames)}个关键帧截图，请根据画面内容创作解说文案："
    })

    for timestamp, b64_img in frames:
        user_content.append({
            "type": "text",
            "text": f"[时间点: {timestamp:.1f}秒]"
        })
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}", "detail": "low"}
        })

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_content}
    ]


def _parse_script(content: str, video_duration: float) -> List[ScriptSegment]:
    """Parse LLM output into ScriptSegments."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1])

    try:
        segments_data = json.loads(content)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            segments_data = json.loads(match.group())
        else:
            raise ValueError("Failed to parse LLM output as JSON")

    segments = []
    for seg in segments_data:
        start = float(seg["start"])
        end = float(seg["end"])
        segments.append(ScriptSegment(
            text=seg["text"],
            start_time=start,
            end_time=min(end, video_duration),
            duration=min(end, video_duration) - start
        ))

    return segments
