#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube/Bilibili 字幕下载器
下载视频字幕并转换为 TXT 格式
"""

import os
import sys
import subprocess
import re
from pathlib import Path

def check_yt_dlp():
    """检查 yt-dlp 是否安装"""
    try:
        subprocess.run(['yt-dlp', '--version'], 
                      capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("错误: 未找到 yt-dlp")
        print("请先安装: pip install yt-dlp")
        return False

def download_subtitles(url, lang='zh,en', proxy=None, output_dir='subtitles'):
    """
    下载视频字幕
    
    Args:
        url: 视频URL
        lang: 字幕语言代码，逗号分隔（默认：zh,en）
        proxy: 代理地址（可选）
        output_dir: 输出目录
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 构建 yt-dlp 命令
    cmd = [
        'yt-dlp',
        '--write-subs',           # 下载字幕
        '--write-auto-subs',      # 下载自动生成的字幕
        '--sub-langs', lang,      # 字幕语言
        '--skip-download',        # 不下载视频
        '--sub-format', 'srt/vtt', # 字幕格式
        '--convert-subs', 'srt',   # 转换为srt格式
        '-o', f'{output_dir}/%(title)s.%(ext)s',  # 输出文件名
    ]
    
    # 添加代理（如果提供）
    if proxy:
        cmd.extend(['--proxy', proxy])
    
    # 添加视频URL
    cmd.append(url)
    
    print(f"正在下载字幕: {url}")
    print(f"命令: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        print(f"\n字幕下载完成！保存在: {output_dir}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"错误: {e.stderr}")
        return False

def srt_to_txt(srt_file, txt_file):
    """
    将 SRT 字幕文件转换为 TXT 格式（纯文本，去除时间戳）
    
    Args:
        srt_file: SRT 文件路径
        txt_file: 输出的 TXT 文件路径
    """
    try:
        with open(srt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用正则表达式提取字幕文本（去除序号和时间戳）
        # SRT格式: 序号\n时间戳\n文本\n
        pattern = r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n(.*?)(?=\n\d+\n|\n*$)'
        matches = re.findall(pattern, content, re.DOTALL)
        
        # 清理文本（去除HTML标签、多余空格等）
        texts = []
        for match in matches:
            # 去除HTML标签
            text = re.sub(r'<[^>]+>', '', match)
            # 去除多余空白字符
            text = re.sub(r'\s+', ' ', text).strip()
            if text:
                texts.append(text)
        
        # 写入TXT文件
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(texts))
        
        print(f"已转换为 TXT: {txt_file}")
        return True
    except Exception as e:
        print(f"转换失败 {srt_file}: {e}")
        return False

def vtt_to_txt(vtt_file, txt_file):
    """
    将 VTT 字幕文件转换为 TXT 格式
    
    Args:
        vtt_file: VTT 文件路径
        txt_file: 输出的 TXT 文件路径
    """
    try:
        with open(vtt_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        texts = []
        in_cue = False
        
        for line in lines:
            line = line.strip()
            # 跳过VTT头部和元数据
            if line.startswith('WEBVTT') or line.startswith('NOTE') or not line:
                continue
            # 跳过时间戳行
            if '-->' in line:
                in_cue = True
                continue
            # 提取文本行
            if in_cue and line and not line.isdigit():
                # 去除HTML标签
                text = re.sub(r'<[^>]+>', '', line).strip()
                if text:
                    texts.append(text)
                in_cue = False
        
        # 写入TXT文件
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(texts))
        
        print(f"已转换为 TXT: {txt_file}")
        return True
    except Exception as e:
        print(f"转换失败 {vtt_file}: {e}")
        return False

def convert_all_to_txt(output_dir='subtitles'):
    """
    将输出目录中的所有字幕文件转换为TXT格式
    """
    output_path = Path(output_dir)
    if not output_path.exists():
        print(f"目录不存在: {output_dir}")
        return
    
    converted_count = 0
    
    # 查找所有SRT和VTT文件
    for sub_file in output_path.glob('*.srt'):
        txt_file = sub_file.with_suffix('.txt')
        if srt_to_txt(str(sub_file), str(txt_file)):
            converted_count += 1
    
    for sub_file in output_path.glob('*.vtt'):
        txt_file = sub_file.with_suffix('.txt')
        if vtt_to_txt(str(sub_file), str(txt_file)):
            converted_count += 1
    
    print(f"\n转换完成！共转换 {converted_count} 个字幕文件")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='下载视频字幕并转换为TXT格式',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 下载中英文字幕
  python download_subtitles.py https://www.youtube.com/watch?v=VIDEO_ID
  
  # 指定语言和代理
  python download_subtitles.py https://www.youtube.com/watch?v=VIDEO_ID --lang zh,en --proxy http://127.0.0.1:15715
  
  # 只转换已有的字幕文件
  python download_subtitles.py --convert-only
        """
    )
    
    parser.add_argument('url', nargs='?', help='视频URL')
    parser.add_argument('--lang', default='zh,en', 
                       help='字幕语言代码（默认: zh,en）')
    parser.add_argument('--proxy', 
                       help='代理地址（例如: http://127.0.0.1:15715）')
    parser.add_argument('--output', '-o', default='subtitles',
                       help='输出目录（默认: subtitles）')
    parser.add_argument('--convert-only', action='store_true',
                       help='只转换已有的字幕文件，不下载')
    
    args = parser.parse_args()
    
    # 如果只是转换已有文件
    if args.convert_only:
        convert_all_to_txt(args.output)
        return
    
    # 需要URL才能下载
    if not args.url:
        parser.print_help()
        sys.exit(1)
    
    # 检查 yt-dlp
    if not check_yt_dlp():
        sys.exit(1)
    
    # 下载字幕
    if download_subtitles(args.url, args.lang, args.proxy, args.output):
        # 转换所有字幕文件为TXT
        convert_all_to_txt(args.output)
        print("\n✅ 完成！所有字幕已转换为 TXT 格式")
    else:
        print("\n❌ 下载失败")
        sys.exit(1)

if __name__ == '__main__':
    main()

