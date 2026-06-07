import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", None)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

TTS_VOICE = os.getenv("TTS_VOICE", "zh-CN-YunxiNeural")
TTS_RATE = os.getenv("TTS_RATE", "+0%")

MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500MB
