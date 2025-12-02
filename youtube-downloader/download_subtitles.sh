#!/bin/bash
# YouTube/Bilibili 字幕下载器 (Bash版本)
# 下载视频字幕并转换为 TXT 格式

set -e

# 默认参数
LANG="zh,en"
PROXY=""
OUTPUT_DIR="subtitles"
URL=""
CONVERT_ONLY=false

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --lang)
            LANG="$2"
            shift 2
            ;;
        --proxy)
            PROXY="$2"
            shift 2
            ;;
        --output|-o)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --convert-only)
            CONVERT_ONLY=true
            shift
            ;;
        --help|-h)
            echo "用法: $0 [URL] [选项]"
            echo ""
            echo "选项:"
            echo "  --lang LANG       字幕语言代码（默认: zh,en）"
            echo "  --proxy PROXY     代理地址（例如: http://127.0.0.1:15715）"
            echo "  --output DIR      输出目录（默认: subtitles）"
            echo "  --convert-only    只转换已有的字幕文件，不下载"
            echo ""
            echo "示例:"
            echo "  $0 https://www.youtube.com/watch?v=VIDEO_ID"
            echo "  $0 https://www.youtube.com/watch?v=VIDEO_ID --lang zh,en --proxy http://127.0.0.1:15715"
            echo "  $0 --convert-only"
            exit 0
            ;;
        *)
            if [[ -z "$URL" ]]; then
                URL="$1"
            fi
            shift
            ;;
    esac
done

# 检查 yt-dlp 是否安装
check_yt_dlp() {
    if ! command -v yt-dlp &> /dev/null; then
        echo "错误: 未找到 yt-dlp"
        echo "请先安装: pip install yt-dlp"
        exit 1
    fi
}

# 下载字幕
download_subtitles() {
    local url=$1
    local lang=$2
    local proxy=$3
    local output_dir=$4
    
    # 创建输出目录
    mkdir -p "$output_dir"
    
    # 构建命令
    local cmd=(
        yt-dlp
        --write-subs
        --write-auto-subs
        --sub-langs "$lang"
        --skip-download
        --sub-format "srt/vtt"
        --convert-subs "srt"
        -o "$output_dir/%(title)s.%(ext)s"
    )
    
    # 添加代理（如果提供）
    if [[ -n "$proxy" ]]; then
        cmd+=(--proxy "$proxy")
    fi
    
    # 添加URL
    cmd+=("$url")
    
    echo "正在下载字幕: $url"
    echo "命令: ${cmd[*]}"
    echo ""
    
    "${cmd[@]}"
    
    echo ""
    echo "字幕下载完成！保存在: $output_dir"
}

# SRT转TXT（简化版，使用sed和awk）
srt_to_txt() {
    local srt_file=$1
    local txt_file=$2
    
    # 使用awk提取字幕文本（去除序号和时间戳）
    awk '
    BEGIN { RS=""; ORS="\n" }
    /^[0-9]+$/ { getline; getline; }
    { 
        gsub(/<[^>]+>/, "");  # 去除HTML标签
        gsub(/[[:space:]]+/, " ");  # 合并空格
        gsub(/^[[:space:]]+|[[:space:]]+$/, "");  # 去除首尾空格
        if ($0) print $0
    }
    ' "$srt_file" > "$txt_file"
    
    if [[ $? -eq 0 ]]; then
        echo "已转换为 TXT: $txt_file"
        return 0
    else
        echo "转换失败: $srt_file"
        return 1
    fi
}

# VTT转TXT（简化版）
vtt_to_txt() {
    local vtt_file=$1
    local txt_file=$2
    
    # 提取VTT中的文本内容
    awk '
    BEGIN { in_cue = 0 }
    /^WEBVTT/ || /^NOTE/ || /^$/ { next }
    /-->/ { in_cue = 1; next }
    in_cue && !/^[0-9]+$/ {
        gsub(/<[^>]+>/, "");
        gsub(/[[:space:]]+/, " ");
        gsub(/^[[:space:]]+|[[:space:]]+$/, "");
        if ($0) print $0
        in_cue = 0
    }
    ' "$vtt_file" > "$txt_file"
    
    if [[ $? -eq 0 ]]; then
        echo "已转换为 TXT: $txt_file"
        return 0
    else
        echo "转换失败: $vtt_file"
        return 1
    fi
}

# 转换所有字幕文件
convert_all_to_txt() {
    local output_dir=$1
    local converted_count=0
    
    if [[ ! -d "$output_dir" ]]; then
        echo "目录不存在: $output_dir"
        return
    fi
    
    # 转换SRT文件
    while IFS= read -r -d '' srt_file; do
        txt_file="${srt_file%.srt}.txt"
        if srt_to_txt "$srt_file" "$txt_file"; then
            ((converted_count++))
        fi
    done < <(find "$output_dir" -name "*.srt" -print0 2>/dev/null || true)
    
    # 转换VTT文件
    while IFS= read -r -d '' vtt_file; do
        txt_file="${vtt_file%.vtt}.txt"
        if vtt_to_txt "$vtt_file" "$txt_file"; then
            ((converted_count++))
        fi
    done < <(find "$output_dir" -name "*.vtt" -print0 2>/dev/null || true)
    
    echo ""
    echo "转换完成！共转换 $converted_count 个字幕文件"
}

# 主流程
main() {
    if [[ "$CONVERT_ONLY" == true ]]; then
        convert_all_to_txt "$OUTPUT_DIR"
        return
    fi
    
    if [[ -z "$URL" ]]; then
        echo "错误: 请提供视频URL"
        echo "使用 --help 查看帮助信息"
        exit 1
    fi
    
    check_yt_dlp
    
    if download_subtitles "$URL" "$LANG" "$PROXY" "$OUTPUT_DIR"; then
        convert_all_to_txt "$OUTPUT_DIR"
        echo ""
        echo "✅ 完成！所有字幕已转换为 TXT 格式"
    else
        echo ""
        echo "❌ 下载失败"
        exit 1
    fi
}

# 运行主函数
main

