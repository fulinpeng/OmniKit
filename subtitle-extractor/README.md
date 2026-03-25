# faster-whisper 本地字幕提取

将本地视频/音频转为字幕，输出到新文件夹内（`outputs/`）。

## 1) 安装依赖

在 `subtitle-extractor` 目录执行：

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

## 2) 执行提取

```bash
python transcribe.py --input "E:/你的视频路径/video.mp4" --output-dir "outputs"
```

执行后会生成：

- `outputs/xxx.srt` 字幕文件
- `outputs/xxx.txt` 纯文本文案
- `outputs/xxx.json` 分段和元数据

## 常用参数

- `--model`: `tiny/base/small/medium/large-v3`（默认 `small`）
- `--device`: `auto/cpu/cuda`（默认 `auto`）
- `--compute-type`: 默认 `int8`，GPU 常用 `float16`
- `--language`: 手动指定语言，如 `zh`、`en`
- `--task`: `transcribe`（转写）或 `translate`（翻译成英文）
- `--vad-filter`: 开启静音过滤

示例（中文、较快）：

```bash
python transcribe.py --input "E:/videos/demo.mp4" --model small --language zh --vad-filter
```
