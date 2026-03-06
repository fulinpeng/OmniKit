# YouTube视频下载指南

## 方法一：使用 yt-dlp（推荐，最强大）

### 安装步骤

1. **下载 yt-dlp**（适用于Windows）：
   - 访问：https://github.com/yt-dlp/yt-dlp/releases
   <!-- - 下载 `yt-dlp.exe`
   - 将其放到 `C:\Windows\System32\` 或任何在PATH中的文件夹 -->

2. **或者使用包管理器安装**：
```bash
# 使用 pip 安装（需要先安装 Python）
pip install yt-dlp
```

## 重要说明：自动合并视频和音频

### 使用 `--merge-output-format mp4` 确保合并

当使用 `bestvideo+bestaudio` 格式时，yt-dlp 会自动下载视频和音频，然后合并为一个文件。

**确保合并为MP4的关键参数：**
```bash
--merge-output-format mp4
```

### 完整的1080p下载命令（推荐）

```bash
# 这个命令会自动下载视频+音频，并合并为一个MP4文件
yt-dlp --proxy "http://127.0.0.1:15715" \
  -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
  --merge-output-format mp4 \
  -o "%(title)s.%(ext)s" \
  "https://www.youtube.com/watch?v=VIDEO_ID"
```

### 如果需要安装 ffmpeg（用于合并）

如果遇到合并失败或下载两个文件的情况，需要安装 ffmpeg。

**⚠️ 注意：** Chocolatey 安装需要管理员权限。如果当前终端没有管理员权限，请使用手动安装方法。

**快速安装（需要管理员权限）：**
```bash
# 以管理员身份运行 PowerShell，然后执行：
choco install ffmpeg -y
```

**详细安装指南：** 请查看 [FFMPEG_INSTALL.md](FFMPEG_INSTALL.md) 文件，包含：
- 手动安装方法（无需管理员权限）
- 详细的步骤说明
- 故障排除指南

**验证 ffmpeg 是否安装：**
```bash
ffmpeg -version
```

如果显示版本信息，说明安装成功。安装后请**关闭并重新打开终端**，PATH 才会生效。

### 如果下载后是两个文件，手动合并

如果下载后得到两个文件（一个视频文件和一个音频文件），可以手动合并：

```bash
# 使用 ffmpeg 合并（假设视频文件是 video.mp4，音频文件是 audio.m4a）
ffmpeg -i video.mp4 -i audio.m4a -c copy output.mp4
```

**注意：** 使用 yt-dlp 时，只要添加了 `--merge-output-format mp4` 参数，通常会自动合并，不需要手动操作。


完整的命令（包含文件名和文件夹）：

```bash
yt-dlp --proxy "http://127.0.0.1:15715" \
  -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
  --merge-output-format mp4 \
  -o "downloads/%(title)s.%(ext)s" \
  "https://youtu.be/itEZC-Rn-4Q"
```

---

## 方法二：下载字幕并转换为 TXT 文件

### 快速开始

#### 使用 Python 脚本（推荐）

```bash
# 安装依赖
pip install yt-dlp

# 下载字幕并自动转换为 TXT
python download_subtitles.py https://www.youtube.com/watch?v=VIDEO_ID

# 指定中英文字幕和代理
python download_subtitles.py https://www.youtube.com/watch?v=VIDEO_ID \
  --lang zh,en \
  --proxy http://127.0.0.1:15715 \
  --output subtitles

# 只转换已有的字幕文件（不下载）
python download_subtitles.py --convert-only --output subtitles
```

#### 使用 Bash 脚本（Linux/Mac/Windows Git Bash）

```bash
# 先给脚本执行权限（仅首次需要）
chmod +x download_subtitles.sh

# 下载字幕并自动转换为 TXT
./download_subtitles.sh https://www.youtube.com/watch?v=VIDEO_ID

# 指定参数
./download_subtitles.sh https://www.youtube.com/watch?v=VIDEO_ID \
  --lang zh,en \
  --proxy http://127.0.0.1:15715 \
  --output subtitles

# 只转换已有的字幕文件
./download_subtitles.sh --convert-only --output subtitles
```

### 功能说明

- ✅ **自动下载字幕**：支持 YouTube、Bilibili 等平台
- ✅ **多语言支持**：可指定多种字幕语言（如 `zh,en`）
- ✅ **自动转换**：将 SRT/VTT 格式自动转换为纯文本 TXT
- ✅ **清理文本**：自动去除时间戳、序号和 HTML 标签
- ✅ **代理支持**：支持使用代理下载（如需要）

### 支持的参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--lang` | 字幕语言代码（逗号分隔） | `zh,en` |
| `--proxy` | 代理地址 | 无 |
| `--output` / `-o` | 输出目录 | `subtitles` |
| `--convert-only` | 只转换已有字幕，不下载 | `false` |

### 字幕语言代码示例

- `zh` - 中文
- `en` - 英文
- `zh,en` - 中英文（下载两种语言）
- `zh-CN,zh-TW,en` - 简体中文、繁体中文、英文

### 输出文件

下载完成后，会在输出目录中生成：
- `视频标题.zh.srt` - 中文原始字幕（SRT格式）
- `视频标题.zh.txt` - 中文纯文本字幕（TXT格式）
- `视频标题.en.srt` - 英文原始字幕（SRT格式）
- `视频标题.en.txt` - 英文纯文本字幕（TXT格式）

TXT 文件包含纯文本内容，去除了所有时间戳和格式标记，适合阅读和学习。


