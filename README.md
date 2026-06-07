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
cd backend
pip install -r requirements.txt

# 设置 OpenAI API Key（必须，用于生成解说文案）
export OPENAI_API_KEY="sk-your-key-here"

# 可选：自定义模型和接口地址（兼容任何 OpenAI 兼容 API）
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4o"

# 可选：自定义 TTS 语音
export TTS_VOICE="zh-CN-YunxiNeural"  # 男声
# export TTS_VOICE="zh-CN-XiaoxiaoNeural"  # 女声

# 启动服务
cd ..
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
上传视频 → 抽取关键帧 → GPT-4o 生成解说文案 → Edge TTS 配音合成
    → 生成 SRT 字幕 → FFmpeg 混音+字幕烧录 → 输出最终 MP4
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
| OPENAI_API_KEY | (必填) | OpenAI API 密钥 |
| OPENAI_BASE_URL | OpenAI 官方 | API 地址，支持兼容接口 |
| OPENAI_MODEL | gpt-4o | 使用的模型，需支持 vision |
| TTS_VOICE | zh-CN-YunxiNeural | Edge TTS 语音角色 |
| TTS_RATE | +0% | 语速调节 |

## 项目结构

```
├── backend/
│   ├── main.py              # FastAPI 入口，API 路由
│   ├── config.py            # 配置管理
│   ├── models.py            # 数据模型
│   └── services/
│       ├── video_analyzer.py    # 视频分析，关键帧提取
│       ├── script_generator.py  # LLM 解说文案生成
│       ├── tts_service.py       # Edge TTS 语音合成
│       ├── subtitle_service.py  # SRT 字幕生成
│       ├── video_editor.py      # 音视频合成
│       └── pipeline.py          # 端到端流水线编排
├── frontend/
│   ├── index.html           # 页面结构
│   ├── style.css            # 样式
│   └── app.js               # 交互逻辑
└── README.md
```

## 注意事项

- 视频文件需包含可识别的画面内容，纯黑屏/静态画面可能导致文案质量较低
- 首次运行 Edge TTS 需要网络连接（下载语音模型）
- 生成耗时取决于视频时长和网络延迟，30秒视频约需 1~2 分钟
- 原视频音轨会被保留并降低音量作为背景音，解说配音为主音轨
