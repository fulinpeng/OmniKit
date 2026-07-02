#!/usr/bin/env python3
"""从已登录的本机 Chrome 直接抓取 Boss 登录态（auth.json / cookies.json）。

无需重新登录。适用于：
  - 之前用 scrape.py --login 打开的 Chrome（仍保持打开）
  - chrome_login 配置里已有登录记录，用 --launch 启动后抓取

用法：
  python capture_auth.py              # 自动扫描本机调试端口并抓取
  python capture_auth.py --port 9222    # 指定 CDP 端口
  python capture_auth.py --launch       # 用已保存的 chrome_login 配置启动 Chrome 再抓取
"""

from __future__ import annotations

import argparse
import subprocess
from typing import Any

from scrape import (
    _launch_chrome_profile,
    _pick_debug_port,
    capture_auth_from_port,
    find_active_cdp_port,
)

BOSS_JOB_URL = "https://www.zhipin.com/web/geek/job"


def launch_chrome_with_profile(port: int) -> subprocess.Popen[Any]:
    """用 chrome_login 用户目录启动 Chrome（磁盘上的登录态会自动加载）。"""
    print(f"[info] 启动 Chrome（配置 chrome_login，端口 {port}）")
    proc, _ = _launch_chrome_profile(BOSS_JOB_URL, port)
    return proc


def capture_auth(
    port: int | None = None,
    *,
    launch: bool = False,
    close_after: bool = False,
) -> bool:
    proc: subprocess.Popen[Any] | None = None

    if port is None:
        port = find_active_cdp_port()

    if port is None and launch:
        port = _pick_debug_port()
        proc = launch_chrome_with_profile(port)
    elif port is None:
        print("[error] 未找到已开启远程调试的 Chrome。")
        print("可选方案：")
        print("  1. 保持 scrape.py --login 打开的 Chrome 不要关，再运行本脚本")
        print("  2. python capture_auth.py --launch")
        print("  3. python capture_auth.py --port 9222")
        return False

    ok = capture_auth_from_port(port)

    if close_after and proc is not None and proc.poll() is None:
        proc.terminate()
        print("[info] 已按 --close 关闭 Chrome")

    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description="从已登录 Chrome 抓取 Boss 登录态")
    parser.add_argument("--port", type=int, help="Chrome remote-debugging 端口（默认自动扫描 9222-9331）")
    parser.add_argument(
        "--launch",
        action="store_true",
        help="用 .browser_profile/chrome_login 启动 Chrome 后抓取（配置里已有登录记录时可用）",
    )
    parser.add_argument(
        "--close",
        action="store_true",
        help="仅配合 --launch：抓取后关闭 Chrome（默认不关闭，由你手动关）",
    )
    args = parser.parse_args()

    ok = capture_auth(args.port, launch=args.launch, close_after=args.close)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
