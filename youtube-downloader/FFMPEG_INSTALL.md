# FFmpeg 安装指南

FFmpeg 是用于合并视频和音频的工具。yt-dlp 在下载高清视频时需要它来自动合并视频和音频。

## 检查是否已安装

```bash
ffmpeg -version
```

如果显示版本信息，说明已安装。如果显示 "command not found"，需要安装。

## 安装方法

### 方法1：使用 Chocolatey（需要管理员权限）

1. **以管理员身份运行 PowerShell 或 CMD**
   - 右键点击开始菜单
   - 选择 "Windows PowerShell (管理员)" 或 "命令提示符 (管理员)"

2. **运行安装命令：**
   ```bash
   choco install ffmpeg -y
   ```

3. **关闭并重新打开终端**，然后验证：
   ```bash
   ffmpeg -version
   ```

### 方法2：手动安装（推荐，无需管理员权限）

#### Windows 手动安装步骤：

1. **下载 FFmpeg**
   - 访问：https://www.gyan.dev/ffmpeg/builds/
   - 点击 "ffmpeg-release-essentials.zip" 下载
   - 或者直接访问：https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip

2. **解压文件**
   - 解压到任意文件夹，例如：`C:\ffmpeg`
   - 或解压到用户目录：`C:\Users\你的用户名\ffmpeg`

3. **添加到系统 PATH**
   
   **方法A：通过系统设置（推荐）**
   - 右键 "此电脑" → "属性"
   - 点击 "高级系统设置"
   - 点击 "环境变量"
   - 在 "用户变量" 或 "系统变量" 中找到 "Path"，点击 "编辑"
   - 点击 "新建"，添加 FFmpeg 的 bin 文件夹路径
     - 例如：`C:\ffmpeg\bin` 或 `C:\Users\你的用户名\ffmpeg\bin`
   - 点击 "确定" 保存
   - **关闭所有终端窗口，重新打开**

   **方法B：临时添加到当前终端**
   ```bash
   # 假设 FFmpeg 解压在 C:\ffmpeg
   export PATH="$PATH:/c/ffmpeg/bin"
   
   # 或者使用 Windows CMD 语法（在 Git Bash 中）
   export PATH="$PATH:/c/Users/你的用户名/ffmpeg/bin"
   ```

4. **验证安装**
   ```bash
   ffmpeg -version
   ```

### 方法3：使用 Scoop（无需管理员权限）

1. **先安装 Scoop**（如果未安装）：
   ```powershell
   # 在 PowerShell 中运行
   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
   irm get.scoop.sh | iex
   ```

2. **安装 FFmpeg**：
   ```bash
   scoop install ffmpeg
   ```

3. **验证**：
   ```bash
   ffmpeg -version
   ```

## 验证安装

安装完成后，关闭并重新打开终端，运行：

```bash
ffmpeg -version
```

如果显示版本信息，说明安装成功。

## 使用 yt-dlp 下载视频

安装 FFmpeg 后，使用以下命令下载并自动合并视频：

```bash
yt-dlp --proxy "http://127.0.0.1:15715" \
  -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
  --merge-output-format mp4 \
  --user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  --extractor-args "youtube:player_client=android" \
  -o "downloads/%(title)s.%(ext)s" \
  "https://www.youtube.com/watch?v=To1pZnOFMp4"
```

## 常见问题

### Q: 安装后仍然显示 "command not found"

**A:** 检查以下几点：
1. 确保已将 FFmpeg 的 bin 文件夹添加到 PATH
2. **关闭所有终端窗口并重新打开**（PATH 更新需要重启终端）
3. 确认 bin 文件夹中有 `ffmpeg.exe`、`ffprobe.exe` 等文件

### Q: 权限不足错误

**A:** 
- 手动安装方法不需要管理员权限
- 如果使用 Chocolatey，需要以管理员身份运行 PowerShell/CMD

### Q: 如何在当前终端会话中测试（不重启）

**A:** 临时添加 PATH：
```bash
# Git Bash 或 WSL
export PATH="$PATH:/c/ffmpeg/bin"

# 然后测试
ffmpeg -version
```

## 下载链接

- **官方网站**：https://ffmpeg.org/download.html
- **Windows 预编译版本**：https://www.gyan.dev/ffmpeg/builds/
- **直接下载**：https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip

