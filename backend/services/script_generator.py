import json
import os
import re
import httpx
from typing import List, Tuple, Optional
from ..config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from ..models import ScriptSegment

ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "")
ANTHROPIC_AUTH_TOKEN = os.getenv("ANTHROPIC_AUTH_TOKEN", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "")


def generate_script(
    frames: List[Tuple[float, str]],
    video_duration: float,
    user_hint: Optional[str] = None
) -> List[ScriptSegment]:
    """Generate commentary script based on video frames using LLM."""
    if OPENAI_API_KEY:
        content = _call_openai(frames, video_duration, user_hint)
    elif ANTHROPIC_BASE_URL and ANTHROPIC_AUTH_TOKEN:
        content = _call_anthropic(frames, video_duration, user_hint)
    else:
        raise RuntimeError("No LLM API key configured. Set OPENAI_API_KEY or ANTHROPIC_BASE_URL+ANTHROPIC_AUTH_TOKEN.")

    return _parse_script(content, video_duration)


def _get_system_prompt(video_duration: float) -> str:
    return (
        "你是一位专业的影视解说文案创作者。根据提供的视频截图和信息，"
        "生成贴合画面的中文解说文案。\n\n"
        "要求：\n"
        "1. 文案要有叙事感，像讲故事一样娓娓道来\n"
        "2. 每个段落对应一个时间段，确保总时长覆盖整个视频\n"
        "3. 每段文案朗读时长大约为对应时间段的长度（按每秒4个汉字估算）\n"
        "4. 输出严格的JSON数组格式，不要包含任何其他内容\n\n"
        f"视频总时长: {video_duration:.1f}秒\n\n"
        "输出格式（纯JSON，不要markdown代码块）:\n"
        '[{"start": 0.0, "end": 5.0, "text": "解说文字..."}, ...]'
    )


def _call_openai(frames, video_duration, user_hint) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

    system_msg = _get_system_prompt(video_duration)
    user_content = _build_openai_user_content(frames, user_hint)

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_content}
        ],
        temperature=0.7,
        max_tokens=2000,
    )
    return response.choices[0].message.content


def _build_openai_user_content(frames, user_hint) -> list:
    user_content = []
    if user_hint:
        user_content.append({"type": "text", "text": f"影片信息补充: {user_hint}"})

    user_content.append({
        "type": "text",
        "text": f"以下是从视频中均匀抽取的{len(frames)}个关键帧截图，请根据画面内容创作解说文案："
    })

    for timestamp, b64_img in frames:
        user_content.append({"type": "text", "text": f"[时间点: {timestamp:.1f}秒]"})
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}", "detail": "low"}
        })

    return user_content


def _call_anthropic(frames, video_duration, user_hint) -> str:
    system_msg = _get_system_prompt(video_duration)
    user_content = _build_anthropic_user_content(frames, user_hint)

    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 2000,
        "system": system_msg,
        "messages": [{"role": "user", "content": user_content}],
    }

    resp = httpx.post(
        f"{ANTHROPIC_BASE_URL}/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_AUTH_TOKEN,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()

    for block in data["content"]:
        if block["type"] == "text":
            return block["text"]

    raise RuntimeError("No text response from Anthropic API")


def _build_anthropic_user_content(frames, user_hint) -> list:
    content = []
    if user_hint:
        content.append({"type": "text", "text": f"影片信息补充: {user_hint}"})

    content.append({
        "type": "text",
        "text": f"以下是从视频中均匀抽取的{len(frames)}个关键帧截图，请根据画面内容创作解说文案："
    })

    for timestamp, b64_img in frames:
        content.append({"type": "text", "text": f"[时间点: {timestamp:.1f}秒]"})
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": b64_img}
        })

    return content


def _parse_script(content: str, video_duration: float) -> List[ScriptSegment]:
    """Parse LLM output into ScriptSegments."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1])

    try:
        segments_data = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            segments_data = json.loads(match.group())
        else:
            raise ValueError(f"Failed to parse LLM output as JSON. Raw output:\n{content[:500]}")

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
