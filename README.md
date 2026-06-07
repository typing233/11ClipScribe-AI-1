# ClipScribe AI - 影视解说视频自动生成工具

自动完成：视频分析 → 解说文案生成 → 配音合成 → 字幕叠加 → 输出成片。

## 系统依赖

```bash
# FFmpeg (必须)
sudo apt install ffmpeg

# Python 3.10+
python --version
```

## 安装与运行

```bash
pip install -r backend/requirements.txt

# 方式一：使用 OpenAI API（需支持 vision 的模型）
export OPENAI_API_KEY="sk-your-key-here"
export OPENAI_MODEL="gpt-4o"  # 可选，默认 gpt-4o

# 方式二：使用 Anthropic API（Claude 系列模型）
export ANTHROPIC_BASE_URL="https://api.anthropic.com"
export ANTHROPIC_AUTH_TOKEN="your-key"
export ANTHROPIC_MODEL="claude-sonnet-4-6"

# 可选：自定义 TTS 语音
export TTS_VOICE="zh-CN-YunxiNeural"  # 男声
# export TTS_VOICE="zh-CN-XiaoxiaoNeural"  # 女声

# 启动服务
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

服务启动后访问 http://localhost:8000 即可打开前端界面。

## 使用方法

1. 打开浏览器访问 `http://localhost:8000`
2. 拖拽或选择一个 30秒~2分钟 的影视片段（MP4/MKV/AVI）
3. 可选填写影片信息（如片名、剧情背景），帮助 AI 生成更贴合的文案
4. 点击"开始生成解说视频"
5. 等待处理完成（约 1~3 分钟），下载生成的视频

## 处理流程

```
上传视频 → 抽取关键帧 → LLM 生成解说文案（带时间轴）
    → Edge TTS 逐段配音 → 按时间轴对齐音频（空白段补静音）
    → 生成 SRT 字幕（与配音同步）→ FFmpeg 混音+字幕烧录
    → 输出最终 MP4（时长 = 原视频时长，不会被截短）
```

## 测试验证

```bash
# 用 curl 测试 API
curl -X POST http://localhost:8000/api/upload \
  -F "file=@test_video.mp4" \
  -F "hint=这是一段动作电影片段"

# 返回 {"task_id": "abcd1234", "message": "任务已提交"}

# 轮询状态
curl http://localhost:8000/api/task/abcd1234

# 下载结果
curl -o output.mp4 http://localhost:8000/api/download/abcd1234
```

## 配置项

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| OPENAI_API_KEY | — | OpenAI API 密钥（与 Anthropic 二选一） |
| OPENAI_BASE_URL | OpenAI 官方 | API 地址，支持兼容接口 |
| OPENAI_MODEL | gpt-4o | 使用的模型，需支持 vision |
| ANTHROPIC_BASE_URL | — | Anthropic API 地址（与 OpenAI 二选一） |
| ANTHROPIC_AUTH_TOKEN | — | Anthropic API 密钥 |
| ANTHROPIC_MODEL | — | Anthropic 模型名 |
| TTS_VOICE | zh-CN-YunxiNeural | Edge TTS 语音角色 |
| TTS_RATE | +0% | 语速调节 |

## 音频/字幕对齐机制

- LLM 生成的文案包含 `start`/`end` 时间戳
- 每段 TTS 音频通过 `adelay` 精确延迟到对应 `start` 时间点
- 段间空白自动填充静音，总音频长度 = 视频时长
- 字幕的起止时间 = `start_time` 到 `start_time + 实际音频时长`
- 最终视频使用 `-t` 控制时长，不使用 `-shortest`，避免意外截断

## 项目结构

```
├── backend/
│   ├── main.py              # FastAPI 入口，API 路由
│   ├── config.py            # 配置管理
│   ├── models.py            # 数据模型
│   └── services/
│       ├── video_analyzer.py    # 视频分析，关键帧提取
│       ├── script_generator.py  # LLM 解说文案生成（支持 OpenAI / Anthropic）
│       ├── tts_service.py       # Edge TTS 语音合成
│       ├── subtitle_service.py  # SRT 字幕生成
│       ├── video_editor.py      # 音频对齐、混音、字幕烧录
│       └── pipeline.py          # 端到端流水线编排
├── frontend/
│   ├── index.html           # 页面结构
│   ├── style.css            # 样式
│   └── app.js               # 交互逻辑
└── README.md
```

## 验收记录

使用 30 秒测试视频完成了完整的 upload → LLM 文案生成 → TTS → 字幕 → download 流程：

- 上传 POST `/api/upload` → 返回 task_id
- 轮询 GET `/api/task/{id}` → 依次经过 analyzing / generating_script / synthesizing_voice / adding_subtitles / editing_video / completed
- 下载 GET `/api/download/{id}` → HTTP 200，输出 30.00s MP4 视频
- 字幕时间轴与配音严格对齐，段间有静音过渡
- 无音频源视频正常处理，不会被截短

## 注意事项

- 视频文件需包含可识别的画面内容，纯黑屏/静态画面可能导致文案质量较低
- 首次运行 Edge TTS 需要网络连接
- 生成耗时取决于视频时长和网络延迟，30秒视频约需 30s~2min
- 原视频音轨会被保留并降低音量作为背景音，解说配音为主音轨
- 无音轨的视频也能正常处理（直接使用解说配音）
