#!/usr/bin/env python3
"""Boss 直聘区块链 / Web3 / 钱包 开发岗采集。

匹配：title 含「区块链 / 以太坊 / web3 / 钱包」之一，且为开发岗。
活跃：近一月（activeTimeDesc 含本月活跃及更近档位）。

用法：
  python scrape.py --login              # 浏览器登录并保存 auth.json
  python scrape.py --fetch-detail --max-pages 20   # 默认 browser 模式
  python scrape.py --mode api --fetch-detail       # 直连 API（易触发反爬）
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent
OUT_JSON = ROOT / "jobs.json"
SEED_DIR = ROOT / "seed_pages"
AUTH_FILE = ROOT / "auth.json"
COOKIES_FILE = ROOT / "cookies.json"
PW_PROFILE = ROOT / ".browser_profile"
BOSS_LOGIN_URL = "https://www.zhipin.com/web/user/?ka=header-login"
CHROME_CDP_EXTRA_ARGS = (
    "--no-first-run",
    "--no-default-browser-check",
    "--remote-allow-origins=*",
)
CITY_CODES = {
    "北京": "101010100",
    "上海": "101020100",
    "广州": "101280100",
    "深圳": "101280600",
    "成都": "101270100",
    "武汉": "101200100",
    "杭州": "101210100",
    "西安": "101110100",
}

SEARCH_QUERIES = ("区块链", "web3", "钱包", "以太坊", "区块链开发", "web3开发")

TITLE_KEYWORDS = ("区块链", "以太坊", "web3", "钱包")

DEV_TITLE_HINT = (
    "开发", "工程师", "engineer", "developer", "研发", "程序员", "架构师",
    "backend", "frontend", "全栈", "golang", "go开发", "java", "node",
)
NON_DEV_TITLE = (
    "产品", "设计", "ui", "ux", "运营", "市场", "销售", "hr", "人事", "行政",
    "测试", "qa", "运维", "投研", "分析师", "策划", "文案", "商务", "实习",
    "实习生", "校招", "合伙人", "总监", "经理", "顾问", "客服", "投资",
    "商务", "推广", "招聘", "猎头", "讲师", "培训", "主播", "销售",
)

# Boss activeTimeDesc：近一月内活跃
ACTIVE_30D_OK = (
    "刚刚活跃", "今日活跃", "3日内活跃", "本周活跃", "近一周活跃", "7日内活跃",
    "两周内活跃", "本月活跃",
)
ACTIVE_30D_NO = (
    "半年前活跃", "半年前", "3月内活跃", "半年内活跃", "四月内", "一年内",
)

REMOTE_KEYWORDS = ("远程", "居家办公", "居家", "remote", "work from home", "wfh")

LOGIN_COOKIE_NAMES = {"wt2", "bst"}  # 仅认 Boss 登录后的核心 Cookie

BOSS_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
)
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
window.chrome = { runtime: {} };
"""

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.zhipin.com/web/geek/job",
    "X-Requested-With": "XMLHttpRequest",
}


@dataclass
class Job:
    city: str
    title: str
    salary: str
    location: str
    experience: str
    education: str
    company: str
    description: str
    url: str
    match_tags: list[str] = field(default_factory=list)
    active_time: str | None = None
    active_within_30d: bool | None = None
    jd: str = ""
    job_id: str = ""
    security_id: str = ""
    source_page: str = ""
    boss_name: str = ""
    remote: bool = False


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def title_has_keyword(title: str) -> bool:
    t = title.lower()
    for kw in TITLE_KEYWORDS:
        if kw == "web3":
            if "web3" in t:
                return True
        elif kw in title:
            return True
    return False


def is_dev_title(title: str) -> bool:
    if any(x in title for x in NON_DEV_TITLE):
        return False
    t = title.lower()
    return any(h.lower() in t or h in title for h in DEV_TITLE_HINT)


def is_match(title: str, description: str = "", jd: str = "") -> bool:
    _ = description, jd
    if not title_has_keyword(title):
        return False
    return is_dev_title(title)


def detect_tags(title: str) -> list[str]:
    tags: list[str] = []
    t = title.lower()
    if "区块链" in title:
        tags.append("区块链")
    if "web3" in t:
        tags.append("web3")
    if "钱包" in title:
        tags.append("钱包")
    if "以太坊" in title:
        tags.append("以太坊")
    return tags or ["区块链"]


def is_remote(job: Job) -> bool:
    blob = f"{job.title} {job.description} {job.jd} {job.location}".lower()
    return any(k.lower() in blob for k in REMOTE_KEYWORDS)


def active_within_30d(desc: str | None) -> bool | None:
    if not desc:
        return None
    if any(x in desc for x in ACTIVE_30D_NO):
        return False
    if any(x in desc for x in ACTIVE_30D_OK):
        return True
    return None


def parse_markdown_blocks(text: str, default_city: str, source: str) -> list[Job]:
    jobs: list[Job] = []
    blocks = re.split(r"###\s+", text)
    i = 0
    while i < len(blocks):
        block = blocks[i].strip()
        if not block:
            i += 1
            continue
        m = re.match(
            r"(?:\[)?([^\]\n]+?)\s+([\d\.\-~Kk元/天·薪]+)\]?\s*\n",
            block,
        )
        if not m:
            i += 1
            continue
        title, salary = _norm(m.group(1)), _norm(m.group(2))
        url_m = re.search(
            r"(https://(?:www|m)\.zhipin\.com/job_detail/[A-Za-z0-9~_.-]+\.html)",
            block,
        )
        if not url_m:
            i += 1
            continue
        url = url_m.group(1).replace("m.zhipin.com", "www.zhipin.com")
        location = experience = education = company = description = ""
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        for ln in lines:
            if re.search(r"\d+-\d+年|经验不限|\d+年以内|10年以上|在校", ln):
                parts = re.split(r"\s{2,}|\s+", ln)
                location = parts[0] if parts else ln
                for p in parts[1:]:
                    if "年" in p or p == "经验不限":
                        experience = p
                    elif p in ("本科", "大专", "硕士", "博士", "学历不限", "中专/中技"):
                        education = p
            if any(
                ln.startswith(p)
                for p in ("岗位职责", "主要职责", "职位描述", "工作内容", "任职要求")
            ):
                description = (description + " " + ln).strip()
        if i + 1 < len(blocks):
            nxt = blocks[i + 1]
            cm = re.search(r"^([^\n]+)\n", nxt)
            if cm and "gongsi" not in cm.group(1):
                company = _norm(cm.group(1).split("\n")[0])
        city = default_city
        for c in CITY_CODES:
            if c in location or c in title:
                city = c
                break
        jid_m = re.search(r"job_detail/([^.]+)\.html", url)
        jobs.append(
            Job(
                city=city,
                title=title,
                salary=salary,
                location=location,
                experience=experience,
                education=education,
                company=company,
                description=description,
                url=url,
                jd=description,
                job_id=jid_m.group(1) if jid_m else "",
                source_page=source,
            )
        )
        i += 1
    return jobs


def load_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    cookies: list[dict[str, Any]] = []
    if COOKIES_FILE.exists():
        data = json.loads(COOKIES_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            cookies = data
            _apply_cookies_to_session(s, data)
        elif isinstance(data, dict):
            s.cookies.update(data)
    if AUTH_FILE.exists() and not COOKIES_FILE.exists():
        state = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
        cookies = state.get("cookies", [])
        _apply_cookies_to_session(s, cookies)
    for c in cookies:
        if c.get("name") == "__zp_stoken__" and c.get("value"):
            s.headers["zp_token"] = c["value"]
            break
    return s


def api_joblist_retry(
    session: requests.Session, query: str, city_code: str, page: int, *, retries: int = 2
) -> dict[str, Any]:
    last: dict[str, Any] = {"code": -1}
    for attempt in range(retries + 1):
        last = api_joblist(session, query, city_code, page)
        if last.get("code") == 0:
            return last
        if last.get("code") in (36, 37) and attempt < retries:
            wait = 12 * (attempt + 1)
            print(f"[info] code={last.get('code')}，等待 {wait}s 后重试 {query}/{city_code} p{page}")
            time.sleep(wait)
            continue
        break
    return last


def _apply_cookies_to_session(session: requests.Session, cookies: list[dict[str, Any]]) -> None:
    for c in cookies:
        if not isinstance(c, dict) or not c.get("name"):
            continue
        domain = c.get("domain") or ".zhipin.com"
        if domain and not domain.startswith(".") and "zhipin" in domain:
            domain = f".{domain.lstrip('.')}"
        session.cookies.set(
            c["name"],
            c["value"],
            domain=domain,
            path=c.get("path", "/"),
        )


def api_joblist(session: requests.Session, query: str, city_code: str, page: int) -> dict[str, Any]:
    r = session.get(
        "https://www.zhipin.com/wapi/zpgeek/search/joblist.json",
        params={
            "scene": "1",
            "query": query,
            "city": city_code,
            "page": str(page),
            "pageSize": "30",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def api_detail(session: requests.Session, security_id: str) -> dict[str, Any]:
    r = session.get(
        "https://www.zhipin.com/wapi/zpgeek/job/detail.json",
        params={"securityId": security_id},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def job_from_api(item: dict[str, Any], city: str) -> Job:
    desc = _norm(item.get("jobDesc") or "")
    active = item.get("activeTimeDesc") or item.get("activeTime") or ""
    enc_id = item.get("encryptJobId") or ""
    url = f"https://www.zhipin.com/job_detail/{enc_id}.html" if enc_id else ""
    loc_parts = [item.get("cityName"), item.get("areaDistrict"), item.get("businessDistrict")]
    location = " ".join(p for p in loc_parts if p)
    return Job(
        city=city,
        title=_norm(item.get("jobName") or ""),
        salary=_norm(item.get("salaryDesc") or ""),
        location=location,
        experience=_norm(item.get("jobExperience") or ""),
        education=_norm(item.get("jobDegree") or ""),
        company=_norm(item.get("brandName") or ""),
        description=desc[:500],
        url=url,
        jd=desc,
        job_id=enc_id,
        security_id=item.get("securityId") or "",
        active_time=active or None,
        active_within_30d=active_within_30d(active),
        boss_name=_norm(item.get("bossName") or ""),
        source_page="joblist.json",
    )


def _accept_job(job: Job, seen: set[str], require_active: bool) -> bool:
    key = job.job_id or job.url
    if not key or key in seen:
        return False
    if require_active and job.active_within_30d is False:
        return False
    if not is_match(job.title):
        return False
    seen.add(key)
    return True


def collect_api_requests(
    session: requests.Session, max_pages: int, require_active: bool
) -> list[Job]:
    all_jobs: list[Job] = []
    seen: set[str] = set()
    for city, code in CITY_CODES.items():
        for query in SEARCH_QUERIES:
            page = 1
            while page <= max_pages:
                try:
                    data = api_joblist_retry(session, query, code, page)
                except requests.RequestException as exc:
                    print(f"[warn] {city}/{query} p{page}: {exc}")
                    break
                if data.get("code") != 0:
                    print(f"[warn] API {city}/{query} p{page}: code={data.get('code')}")
                    break
                zp = data.get("zpData") or {}
                items = zp.get("jobList") or []
                if not items:
                    break
                for item in items:
                    job = job_from_api(item, city)
                    if _accept_job(job, seen, require_active):
                        job.match_tags = detect_tags(job.title)
                        all_jobs.append(job)
                if not zp.get("hasMore"):
                    break
                page += 1
                time.sleep(2.5)
    return all_jobs


def _browser_fetch_json(page: Any, url: str) -> dict[str, Any]:
    return page.evaluate(
        """async (url) => {
            const r = await fetch(url, { credentials: 'include' });
            return await r.json();
        }""",
        url,
    )


def _find_chrome() -> Path | None:
    candidates = (
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
        / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    )
    for path in candidates:
        if path.is_file():
            return path
    return None


def _pick_debug_port() -> int:
    for port in range(9222, 9322):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return 9222


def _wait_cdp_port(port: int, proc: subprocess.Popen[Any], timeout_sec: float = 15) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("Chrome 启动后立即退出")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                return
        except OSError:
            time.sleep(0.3)
    raise RuntimeError(f"Chrome 调试端口 {port} 未就绪")


def find_active_cdp_port(start: int = 9222, end: int = 9332) -> int | None:
    """扫描本机已开启 remote-debugging 的 Chrome，优先含 zhipin.com 标签页。"""
    fallback: int | None = None
    for port in range(start, end):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=0.4) as resp:
                if resp.status != 200:
                    continue
                version = json.loads(resp.read().decode())
                if "Chrome" not in version.get("Browser", ""):
                    continue
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=0.4) as resp:
                targets = json.loads(resp.read().decode())
            if any("zhipin.com" in (t.get("url") or "") for t in targets):
                return port
            if fallback is None:
                fallback = port
        except Exception:
            continue
    return fallback


def _launch_chrome_profile(url: str, port: int | None = None) -> tuple[subprocess.Popen[Any], int]:
    chrome = _find_chrome()
    if not chrome:
        raise RuntimeError("未找到 Google Chrome")
    if port is None:
        port = _pick_debug_port()
    profile = PW_PROFILE / "chrome_login"
    profile.mkdir(parents=True, exist_ok=True)
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    proc = subprocess.Popen(
        [
            str(chrome),
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile}",
            *CHROME_CDP_EXTRA_ARGS,
            "--start-maximized",
            url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    _wait_cdp_port(port, proc)
    time.sleep(1.0)
    return proc, port


def _launch_chrome_for_login() -> tuple[subprocess.Popen[Any], int]:
    """仅启动本机 Chrome 打开登录页，不连接 Playwright（避免窗口被连带关闭）。"""
    print(f"[info] 正在打开本机 Chrome → {BOSS_LOGIN_URL}")
    proc, port = _launch_chrome_profile(BOSS_LOGIN_URL)
    print("[info] Chrome 已启动，请在浏览器中完成登录（窗口会一直保持打开）")
    return proc, port


def _connect_cdp(p: Any, port: int) -> tuple[Any, Any, Any]:
    """连接已启动的 Chrome CDP，返回 browser/context/page。"""
    browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
    page: Any | None = None
    for pg in ctx.pages:
        if "zhipin.com" in (pg.url or ""):
            page = pg
            break
    if page is None:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
    return browser, ctx, page


def _normalize_cdp_cookies(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for c in raw:
        name = c.get("name")
        if not name:
            continue
        same = c.get("sameSite")
        if isinstance(same, str):
            same = same[:1].upper() + same[1:].lower() if same else "Lax"
        out.append(
            {
                "name": name,
                "value": c.get("value", ""),
                "domain": c.get("domain") or ".zhipin.com",
                "path": c.get("path", "/"),
                "expires": c.get("expires", -1),
                "httpOnly": bool(c.get("httpOnly", False)),
                "secure": bool(c.get("secure", False)),
                "sameSite": same or "Lax",
            }
        )
    return out


def _cdp_browser_ws_url(port: int) -> str:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=5) as resp:
        data = json.loads(resp.read().decode())
    ws_url = data.get("webSocketDebuggerUrl")
    if not ws_url:
        raise RuntimeError("CDP 未返回 webSocketDebuggerUrl")
    return ws_url


def _cdp_list_targets(port: int) -> list[dict[str, Any]]:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as resp:
        data = json.loads(resp.read().decode())
    return data if isinstance(data, list) else []


class _CdpSession:
    def __init__(self, ws_url: str) -> None:
        from websocket import create_connection

        self._ws = create_connection(ws_url, timeout=30)
        self._seq = 0

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._seq += 1
        req_id = self._seq
        self._ws.send(json.dumps({"id": req_id, "method": method, "params": params or {}}))
        deadline = time.time() + 30
        while time.time() < deadline:
            msg = json.loads(self._ws.recv())
            if msg.get("id") != req_id:
                continue
            if "error" in msg:
                err = msg["error"]
                raise RuntimeError(err.get("message") if isinstance(err, dict) else str(err))
            return msg.get("result") or {}
        raise RuntimeError(f"CDP 超时: {method}")

    def close(self) -> None:
        self._ws.close()


def _cdp_ensure_page_ws(port: int) -> str:
    """获取或新建 zhipin.com 标签页的 CDP WebSocket（不用 Playwright）。"""
    for t in _cdp_list_targets(port):
        if t.get("type") == "page" and "zhipin.com" in (t.get("url") or ""):
            ws = t.get("webSocketDebuggerUrl")
            if ws:
                return ws
    browser_ws = _cdp_browser_ws_url(port)
    session = _CdpSession(browser_ws)
    try:
        created = session.call(
            "Target.createTarget", {"url": "https://www.zhipin.com/web/geek/job"}
        )
        target_id = created.get("targetId")
    finally:
        session.close()
    time.sleep(2)
    for t in _cdp_list_targets(port):
        if t.get("id") == target_id:
            ws = t.get("webSocketDebuggerUrl")
            if ws:
                return ws
        if t.get("type") == "page" and "zhipin.com" in (t.get("url") or ""):
            ws = t.get("webSocketDebuggerUrl")
            if ws:
                return ws
    raise RuntimeError("无法打开 Boss 页面标签")


def _cdp_navigate(page_ws: str, url: str) -> None:
    session = _CdpSession(page_ws)
    try:
        session.call("Page.enable")
        session.call("Page.navigate", {"url": url})
    finally:
        session.close()
    time.sleep(2.5)


def _cdp_evaluate(page_ws: str, expression: str, *, await_promise: bool = False) -> Any:
    session = _CdpSession(page_ws)
    try:
        session.call("Runtime.enable")
        params: dict[str, Any] = {"expression": expression, "returnByValue": True}
        if await_promise:
            params["awaitPromise"] = True
        result = session.call("Runtime.evaluate", params)
        if result.get("exceptionDetails"):
            raise RuntimeError(str(result["exceptionDetails"]))
        return (result.get("result") or {}).get("value")
    finally:
        session.close()


def _cdp_fetch_json(page_ws: str, url: str) -> dict[str, Any]:
    expr = f"fetch({json.dumps(url)}, {{credentials:'include'}}).then(r=>r.json())"
    data = _cdp_evaluate(page_ws, expr, await_promise=True)
    if not isinstance(data, dict):
        raise RuntimeError("fetch 返回非 JSON")
    return data


def _cdp_call(ws_url: str, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    session = _CdpSession(ws_url)
    try:
        return session.call(method, params)
    finally:
        session.close()


def _fetch_cookies_from_ws(ws_url: str) -> list[dict[str, Any]]:
    session = _CdpSession(ws_url)
    try:
        try:
            session.call("Network.enable")
        except Exception:
            pass
        attempts: list[tuple[str, dict[str, Any]]] = [
            ("Network.getAllCookies", {}),
            (
                "Network.getCookies",
                {"urls": ["https://www.zhipin.com", "https://login.zhipin.com"]},
            ),
            (
                "Storage.getCookies",
                {"urls": ["https://www.zhipin.com", "https://login.zhipin.com"]},
            ),
        ]
        for method, params in attempts:
            try:
                result = session.call(method, params)
                cookies = _normalize_cdp_cookies(result.get("cookies", []))
                if cookies:
                    return cookies
            except Exception:
                continue
    finally:
        session.close()
    return []


def _fetch_cookies_via_cdp_port(port: int) -> list[dict[str, Any]]:
    """纯 CDP 读 Cookie，不经过 Playwright，不会关闭 Chrome 窗口。"""
    errors: list[str] = []

    try:
        cookies = _fetch_cookies_from_ws(_cdp_browser_ws_url(port))
        if cookies:
            return cookies
    except Exception as exc:
        errors.append(f"browser: {exc}")

    for target in _cdp_list_targets(port):
        if target.get("type") != "page":
            continue
        ws_url = target.get("webSocketDebuggerUrl")
        if not ws_url:
            continue
        try:
            cookies = _fetch_cookies_from_ws(ws_url)
            if cookies:
                return cookies
        except Exception as exc:
            errors.append(f"page {target.get('url', '')}: {exc}")

    if errors:
        joined = "; ".join(errors[:3])
        if "403" in joined or "Forbidden" in joined or "remote-allow-origins" in joined:
            raise RuntimeError(
                "Chrome 拒绝了 CDP 连接（缺少 --remote-allow-origins）。"
                " 请关闭当前 Boss Chrome 窗口后重新运行: python scrape.py --login"
            )
        raise RuntimeError(joined)
    return []


def _extract_cookies_from_cdp(browser: Any) -> list[dict[str, Any]]:
    """Playwright connect_over_cdp 场景下通过 CDP session 读 Cookie。"""
    attempts: list[tuple[str, dict[str, Any]]] = [
        (
            "Storage.getCookies",
            {"urls": ["https://www.zhipin.com", "https://login.zhipin.com"]},
        ),
        ("Network.getAllCookies", {}),
        ("Storage.getCookies", {}),
    ]
    try:
        cdp = browser.new_browser_cdp_session()
        for method, params in attempts:
            try:
                result = cdp.send(method, params)
                cookies = _normalize_cdp_cookies(result.get("cookies", []))
                if cookies:
                    return cookies
            except Exception:
                continue
    except Exception:
        pass

    for ctx in browser.contexts:
        try:
            cookies = ctx.cookies(["https://www.zhipin.com", "https://login.zhipin.com"])
            if cookies:
                return list(cookies)
        except Exception:
            try:
                cookies = ctx.cookies()
                if cookies:
                    return list(cookies)
            except Exception:
                continue
    return []


def _save_auth_cookies(cookies: list[dict[str, Any]]) -> None:
    AUTH_FILE.write_text(
        json.dumps({"cookies": cookies, "origins": []}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    COOKIES_FILE.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")


def _cookie_names(cookies: list[dict[str, Any]]) -> set[str]:
    return {c["name"] for c in cookies if c.get("name")}


def _has_login_cookies_list(cookies: list[dict[str, Any]]) -> bool:
    return bool(_cookie_names(cookies) & LOGIN_COOKIE_NAMES)


def _probe_joblist_requests(cookies: list[dict[str, Any]]) -> tuple[bool, str]:
    session = requests.Session()
    session.headers.update(HEADERS)
    _apply_cookies_to_session(session, cookies)
    try:
        data = api_joblist(session, "区块链", "101010100", 1)
        if data.get("code") == 0:
            return True, "joblist ok (requests)"
        return False, f"joblist code={data.get('code')} msg={data.get('message', '')}"
    except Exception as exc:
        return False, f"requests: {exc}"


def _disconnect_cdp(browser: Any | None) -> None:
    """占位：CDP 抓取已改为纯 WebSocket，不持有 Playwright browser 引用。"""
    _ = browser


def capture_auth_from_port(port: int) -> bool:
    """从指定 CDP 端口抓取 Boss 登录态并写入 auth.json / cookies.json。"""
    print(f"[info] 连接 Chrome CDP :{port} …")
    try:
        cookies = _fetch_cookies_via_cdp_port(port)
    except Exception as exc:
        print(f"[error] 连接失败: {exc}")
        return False

    if not cookies:
        print("[error] 未能读取 Cookie，请保持 Chrome 窗口打开后重试")
        return False

    names = sorted(_cookie_names(cookies))
    print(f"[info] 读到 Cookie: {names}")

    if not _has_login_cookies_list(cookies):
        print("[error] 未检测到 wt2/bst，当前浏览器未登录 Boss")
        return False

    ok, detail = _probe_joblist_requests(cookies)
    _save_auth_cookies(cookies)
    try:
        PW_PROFILE.mkdir(parents=True, exist_ok=True)
        state = {"cookies": cookies, "origins": []}
        (PW_PROFILE / "state.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass

    if ok:
        print(f"已保存 {AUTH_FILE.name} 与 {COOKIES_FILE.name}（{detail}）")
    else:
        print(f"[warn] API 探测: {detail}")
        print(f"已保存 {AUTH_FILE.name} 与 {COOKIES_FILE.name}（含 wt2/bst）")
    print("[info] Chrome 窗口保持打开，请手动关闭")
    return True


def _launch_browser(
    p: Any,
    *,
    headless: bool = False,
    persist: bool = True,
    start_urls: tuple[str, ...] | None = None,
) -> tuple[Any, Any]:
    """启动本机 Chrome/Edge，尽量避免 about:blank 首屏。"""
    args = [
        "--disable-blink-features=AutomationControlled",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    ignore = ["--enable-automation", "--no-sandbox"]
    base = dict(
        headless=headless,
        args=args,
        ignore_default_args=ignore,
        locale="zh-CN",
        viewport={"width": 1366, "height": 900},
        user_agent=BOSS_UA,
        extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
    )
    last_err: Exception | None = None
    for channel in ("chrome", "msedge", None):
        try:
            ch_kw = {"channel": channel} if channel else {}
            if persist:
                PW_PROFILE.mkdir(parents=True, exist_ok=True)
                ctx = p.chromium.launch_persistent_context(
                    str(PW_PROFILE), **ch_kw, **base
                )
            else:
                browser = p.chromium.launch(**ch_kw, headless=headless, args=args, ignore_default_args=ignore)
                ctx_kw: dict[str, Any] = {
                    "locale": base["locale"],
                    "viewport": base["viewport"],
                    "user_agent": base["user_agent"],
                    "extra_http_headers": base["extra_http_headers"],
                }
                if AUTH_FILE.exists():
                    ctx_kw["storage_state"] = str(AUTH_FILE)
                ctx = browser.new_context(**ctx_kw)
            ctx.add_init_script(STEALTH_JS)
            page = _open_boss_page(ctx, urls=start_urls)
            return ctx, page
        except Exception as exc:
            last_err = exc
            continue
    raise RuntimeError(f"无法启动浏览器: {last_err}")


def _open_boss_page(ctx: Any, *, urls: tuple[str, ...] | None = None) -> Any:
    """在首个标签页打开 Boss，避免多标签时焦点停在 about:blank。"""
    targets = urls or (
        "https://www.zhipin.com/",
        "https://www.zhipin.com/web/geek/job",
        "https://m.zhipin.com/",
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    for url in targets:
        try:
            print(f"[info] 正在打开 {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
            if page.url and "zhipin.com" in page.url:
                print(f"[info] 已打开 {page.url}")
                break
        except Exception as exc:
            print(f"[warn] 打开失败: {exc}")
    page.bring_to_front()
    for old in list(ctx.pages):
        if old is page:
            continue
        try:
            if (old.url or "").startswith("about:blank"):
                old.close()
        except Exception:
            pass
    if not (page.url and "zhipin.com" in page.url):
        hint = targets[0] if targets else BOSS_LOGIN_URL
        print(f"[warn] 未能自动打开 Boss，请在浏览器地址栏粘贴: {hint}")
    return page


def _goto_zhipin(page: Any, url: str = "https://www.zhipin.com/") -> bool:
    """打开 Boss 首页；若被重定向到 about:blank 则重试。"""
    if page.url and "zhipin.com" in page.url and "blank" not in page.url:
        return True
    for target in (url, "https://www.zhipin.com/", "https://www.zhipin.com/web/geek/job"):
        try:
            page.goto(target, wait_until="domcontentloaded", timeout=60000)
            if page.url and "zhipin.com" in page.url:
                return True
        except Exception:
            pass
        try:
            page.evaluate("(u) => { window.location.href = u; }", target)
            time.sleep(3)
            if page.url and "zhipin.com" in page.url:
                return True
        except Exception:
            pass
    return bool(page.url and "zhipin.com" in page.url)


def _save_auth(ctx: Any) -> None:
    ctx.storage_state(path=str(AUTH_FILE))
    try:
        cookies = ctx.cookies(["https://www.zhipin.com", "https://login.zhipin.com"])
    except TypeError:
        cookies = ctx.cookies()
    COOKIES_FILE.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")


def _probe_joblist_api(ctx: Any, page: Any) -> tuple[bool, str]:
    """探测 joblist API；code==0 即视为登录有效（不要求一定有岗位）。"""
    url = (
        "https://www.zhipin.com/wapi/zpgeek/search/joblist.json"
        "?scene=1&query=%E5%8C%BA%E5%9D%97%E9%93%BE&city=101010100&page=1&pageSize=5"
    )
    referer = "https://www.zhipin.com/web/geek/job"
    headers = {"Referer": referer, "Accept": "application/json, text/plain, */*"}

    last_err = ""
    try:
        resp = ctx.request.get(url, headers=headers, timeout=30000)
        data = resp.json()
        if data.get("code") == 0:
            return True, "joblist ok (request)"
        last_err = f"joblist code={data.get('code')} msg={data.get('message', '')}"
    except Exception as exc:
        last_err = f"request: {exc}"

    try:
        if "zhipin.com" not in (page.url or ""):
            page.goto(referer, wait_until="domcontentloaded", timeout=60000)
        data = _browser_fetch_json(page, url)
        if data.get("code") == 0:
            return True, "joblist ok (fetch)"
        return False, f"{last_err}; fetch code={data.get('code')} msg={data.get('message', '')}"
    except Exception as exc:
        return False, f"{last_err}; fetch: {exc}"


def _verify_logged_in(page: Any, ctx: Any) -> bool:
    """有登录 Cookie 且 joblist API 返回 code=0。"""
    ok, _ = _verify_logged_in_detail(page, ctx)
    return ok


def _verify_logged_in_detail(page: Any, ctx: Any) -> tuple[bool, str]:
    cookies = _extract_cookies_from_cdp(ctx.browser) if hasattr(ctx, "browser") else []
    if not cookies:
        try:
            cookies = list(ctx.cookies(["https://www.zhipin.com"]))
        except Exception:
            try:
                cookies = list(ctx.cookies())
            except Exception:
                cookies = []
    if not _has_login_cookies_list(cookies):
        return False, "缺少 wt2/bst Cookie"
    ok, detail = _probe_joblist_requests(cookies)
    if ok:
        return True, detail
    if page is not None:
        try:
            return _probe_joblist_api(ctx, page)
        except Exception as exc:
            return False, f"{detail}; browser: {exc}"
    return False, detail


def _has_login_cookies(ctx: Any) -> bool:
    try:
        browser = ctx.browser
        cookies = _extract_cookies_from_cdp(browser)
        if cookies:
            return _has_login_cookies_list(cookies)
    except Exception:
        pass
    try:
        names = {c["name"] for c in ctx.cookies()}
        return bool(names & LOGIN_COOKIE_NAMES)
    except Exception:
        return False


def _is_logged_in(page: Any, ctx: Any) -> bool:
    return _verify_logged_in(page, ctx)


def _prompt_login() -> None:
    """等待用户在独立 Chrome 窗口中完成登录。"""
    print(
        "\n请在本机 Chrome 中完成登录：\n"
        f"  1. 若未显示登录页，在地址栏打开 {BOSS_LOGIN_URL}\n"
        "  2. 手机号+验证码 或 扫码登录\n"
        "  3. 确认登录成功（能看到用户头像/职位页）后，回到终端\n"
        "  4. 按 Enter 保存（未完成登录前不要按 Enter）\n"
        "  说明：登录期间 Chrome 与脚本互不干扰，窗口不会自动关闭。\n"
    )
    input("登录完成后按 Enter… ")


def _wait_for_login(page: Any, ctx: Any, timeout_sec: int = 300) -> bool:
    """采集模式：优先手动确认，避免自动跳转打断登录。"""
    _ = timeout_sec
    _prompt_login()
    return _verify_logged_in(page, ctx)


def _open_scrape_browser() -> tuple[Any, Any, Any, subprocess.Popen[Any] | None]:
    """连接/启动 chrome_login Chrome，返回 (playwright, browser, page, proc)。"""
    from playwright.sync_api import sync_playwright

    proc: subprocess.Popen[Any] | None = None
    port = find_active_cdp_port()
    if port is None:
        print("[info] 启动 chrome_login Chrome…")
        proc, port = _launch_chrome_profile("https://www.zhipin.com/web/geek/job")
    else:
        print(f"[info] 复用已打开的 Chrome（端口 {port}）")
    pw = sync_playwright().start()
    browser, _ctx, page = _connect_cdp(pw, port)
    return pw, browser, page, proc


DOM_EXTRACT_JS = """
() => {
  const cards = document.querySelectorAll(
    '.job-card-wrapper, .job-list-box .job-card, li.job-card-box, .job-list li'
  );
  const rows = [];
  cards.forEach((card) => {
    const link = card.querySelector('a[href*="job_detail"], .job-name a, .job-title a');
    const href = link?.href || '';
    const title = (link?.innerText || card.querySelector('.job-name, .job-title')?.innerText || '').trim();
    if (!title) return;
    const jobId = (href.match(/job_detail\\/([^.?]+)/) || [])[1] || '';
    const salary = (card.querySelector('.salary')?.innerText || '').trim();
    const company = (card.querySelector('.company-name, .company-text .name, .company-name a')?.innerText || '').trim();
    const area = (card.querySelector('.job-area, .job-area-wrapper')?.innerText || '').trim();
    const info = (card.querySelector('.job-info, .tag-list')?.innerText || '').trim();
    const active = (card.querySelector('.info-public, .boss-active-time, .job-card-footer')?.innerText || '').trim();
    rows.push({ title, href, jobId, salary, company, area, info, active });
  });
  return rows;
}
"""


def job_from_dom(row: dict[str, Any], city: str) -> Job:
    title = _norm(row.get("title") or "")
    job_id = _norm(row.get("jobId") or "")
    url = _norm(row.get("href") or "")
    if not job_id and url:
        m = re.search(r"job_detail/([^.?]+)", url)
        job_id = m.group(1) if m else ""
    if not url and job_id:
        url = f"https://www.zhipin.com/job_detail/{job_id}.html"
    info = _norm(row.get("info") or "")
    active = _norm(row.get("active") or "")
    exp, edu = "", ""
    for part in re.split(r"[\\s·|]+", info):
        p = part.strip()
        if re.search(r"年|经验|应届|在校", p):
            exp = p
        elif re.search(r"科|学历|博士|硕士|大专", p):
            edu = p
    return Job(
        city=city,
        title=title,
        salary=_norm(row.get("salary") or ""),
        location=_norm(row.get("area") or ""),
        experience=exp,
        education=edu,
        company=_norm(row.get("company") or ""),
        description="",
        url=url,
        active_time=active or None,
        active_within_30d=active_within_30d(active) if active else None,
        job_id=job_id,
        source_page="dom",
    )


def _goto_search_page_cdp(
    page_ws: str, query: str, city_code: str, page_num: int
) -> dict[str, Any] | None:
    """纯 CDP：打开搜索页，页面内 fetch 或解析 DOM。"""
    q = requests.utils.quote(query)
    page_url = f"https://www.zhipin.com/web/geek/job?city={city_code}&query={q}&page={page_num}"
    api_url = (
        f"https://www.zhipin.com/wapi/zpgeek/search/joblist.json"
        f"?scene=1&query={q}&city={city_code}&page={page_num}&pageSize=30"
    )
    try:
        _cdp_navigate(page_ws, page_url)
        try:
            data = _cdp_fetch_json(page_ws, api_url)
            if data.get("code") == 0:
                return {"kind": "api", "data": data}
        except Exception:
            pass
        rows = _cdp_evaluate(page_ws, DOM_EXTRACT_JS.strip())
        if rows:
            return {"kind": "dom", "rows": rows}
        return None
    except Exception as exc:
        print(f"[warn] 搜索页失败 {query} p{page_num}: {exc}")
        return None


def _scrape_detail_cdp(page_ws: str, job: Job) -> None:
    if not job.url:
        return
    try:
        _cdp_navigate(page_ws, job.url)
        if job.security_id:
            api_url = (
                f"https://www.zhipin.com/wapi/zpgeek/job/detail.json"
                f"?securityId={job.security_id}"
            )
            try:
                data = _cdp_fetch_json(page_ws, api_url)
                if data.get("code") == 0:
                    info = (data.get("zpData") or {}).get("jobInfo") or data.get("zpData") or {}
                    post = _norm(info.get("postDescription") or info.get("jobDesc") or "")
                    active = info.get("activeTimeDesc") or info.get("activeTime")
                    if post:
                        job.jd = post
                        job.description = post[:500]
                    if active:
                        job.active_time = str(active)
                        job.active_within_30d = active_within_30d(str(active))
                    return
            except Exception:
                pass
        raw = _cdp_evaluate(
            page_ws,
            """(() => {
                const text = document.querySelector(
                  '.job-sec-text, .job-detail-body, .detail-content, .job-detail-section'
                )?.innerText || '';
                const active = document.querySelector('.boss-info-attr, .info-public')?.innerText || '';
                return { text, active };
            })()""",
        )
        if isinstance(raw, dict):
            post = _norm(raw.get("text") or "")
            active = _norm(raw.get("active") or "")
            if post:
                job.jd = post
                job.description = post[:500]
            if active:
                job.active_time = active
                job.active_within_30d = active_within_30d(active)
    except Exception:
        pass


def _goto_search_page(page: Any, query: str, city_code: str, page_num: int) -> dict[str, Any] | None:
    """打开搜索页，优先拦截页面自己发出的 joblist.json，失败则解析 DOM。"""
    q = requests.utils.quote(query)
    url = f"https://www.zhipin.com/web/geek/job?city={city_code}&query={q}&page={page_num}"
    captured: list[dict[str, Any]] = []

    def on_resp(resp: Any) -> None:
        if "joblist.json" not in resp.url:
            return
        try:
            captured.append(resp.json())
        except Exception:
            pass

    page.on("response", on_resp)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
        for _ in range(40):
            if captured:
                break
            time.sleep(0.25)
        if captured:
            data = captured[-1]
            if data.get("code") == 0:
                return {"kind": "api", "data": data}
        rows = page.evaluate(DOM_EXTRACT_JS)
        if rows:
            return {"kind": "dom", "rows": rows}
        return None
    except Exception as exc:
        print(f"[warn] 搜索页加载失败 {query} p{page_num}: {exc}")
        return None
    finally:
        page.remove_listener("response", on_resp)


def _scrape_detail_dom(page: Any, job: Job) -> None:
    if not job.url:
        return
    detail_json: dict[str, Any] | None = None

    def on_resp(resp: Any) -> None:
        nonlocal detail_json
        if "detail.json" in resp.url and detail_json is None:
            try:
                detail_json = resp.json()
            except Exception:
                pass

    page.on("response", on_resp)
    try:
        page.goto(job.url, wait_until="domcontentloaded", timeout=90000)
        for _ in range(30):
            if detail_json:
                break
            time.sleep(0.2)
        if detail_json and detail_json.get("code") == 0:
            info = (detail_json.get("zpData") or {}).get("jobInfo") or detail_json.get("zpData") or {}
            post = _norm(info.get("postDescription") or info.get("jobDesc") or "")
            active = info.get("activeTimeDesc") or info.get("activeTime")
        else:
            raw = page.evaluate(
                """() => {
                    const text = document.querySelector(
                      '.job-sec-text, .job-detail-body, .detail-content, .job-detail-section'
                    )?.innerText || '';
                    const active = document.querySelector('.boss-info-attr, .info-public')?.innerText || '';
                    return { text, active };
                }"""
            )
            post = _norm(raw.get("text") or "")
            active = _norm(raw.get("active") or "")
        if post:
            job.jd = post
            job.description = post[:500]
        if active:
            job.active_time = active
            job.active_within_30d = active_within_30d(active)
    except Exception:
        pass
    finally:
        page.remove_listener("response", on_resp)


def collect_browser(
    max_pages: int, require_active: bool, *, fetch_detail: bool = False
) -> list[Job]:
    """纯 CDP 远程调试 Chrome：打开真实搜索页，不经过 Playwright 导航。"""
    proc: subprocess.Popen[Any] | None = None
    port = find_active_cdp_port()
    if port is None:
        print("[info] 启动 chrome_login Chrome…")
        proc, port = _launch_chrome_profile("https://www.zhipin.com/web/geek/job")
    else:
        print(f"[info] 复用已打开的 Chrome（端口 {port}）")

    try:
        page_ws = _cdp_ensure_page_ws(port)
    except Exception as exc:
        print(f"[error] 无法打开 Boss 页面: {exc}")
        return []

    all_jobs: list[Job] = []
    seen: set[str] = set()
    try:
        for city, code in CITY_CODES.items():
            for query in SEARCH_QUERIES:
                empty_streak = 0
                for page_num in range(1, max_pages + 1):
                    result = _goto_search_page_cdp(page_ws, query, code, page_num)
                    if not result:
                        empty_streak += 1
                        if empty_streak >= 2:
                            break
                        time.sleep(3)
                        continue
                    added = 0
                    if result["kind"] == "api":
                        zp = result["data"].get("zpData") or {}
                        items = zp.get("jobList") or []
                        has_more = bool(zp.get("hasMore"))
                        for item in items:
                            job = job_from_api(item, city)
                            if _accept_job(job, seen, require_active):
                                job.match_tags = detect_tags(job.title)
                                all_jobs.append(job)
                                added += 1
                        tag = "页面API"
                        if not items:
                            break
                    else:
                        for row in result["rows"]:
                            job = job_from_dom(row, city)
                            if _accept_job(job, seen, require_active):
                                job.match_tags = detect_tags(job.title)
                                all_jobs.append(job)
                                added += 1
                        tag = "DOM"
                        if not result["rows"]:
                            break
                        has_more = added > 0
                    print(f"  {city}/{query} p{page_num}: +{added} (累计 {len(all_jobs)}) [{tag}]")
                    empty_streak = 0 if added else empty_streak + 1
                    if empty_streak >= 2:
                        break
                    if result["kind"] == "api" and not has_more:
                        break
                    time.sleep(2.5)

        if fetch_detail and all_jobs:
            print(f"拉取 {len(all_jobs)} 条详情…")
            for i, job in enumerate(all_jobs, 1):
                _scrape_detail_cdp(page_ws, job)
                if i % 10 == 0:
                    print(f"  详情 {i}/{len(all_jobs)}")
                time.sleep(1.2)
    except Exception as exc:
        print(f"[error] 浏览器采集失败: {exc}")
    finally:
        print("[info] 采集结束，Chrome 保持打开，请手动关闭")
        _ = proc
    return all_jobs


def collect_api_cdp(
    max_pages: int, require_active: bool, *, fetch_detail: bool = False
) -> list[Job]:
    """在已登录 Chrome 内用 fetch 翻页采集，绕过 requests 反爬。"""
    from playwright.sync_api import sync_playwright

    proc: subprocess.Popen[Any] | None = None
    port = find_active_cdp_port()
    if port is None:
        print("[info] 启动 chrome_login Chrome 用于采集…")
        proc, port = _launch_chrome_profile("https://www.zhipin.com/web/geek/job")
    else:
        print(f"[info] 复用已打开的 Chrome（端口 {port}）")

    all_jobs: list[Job] = []
    seen: set[str] = set()
    pw = sync_playwright().start()
    try:
        browser, _ctx, page = _connect_cdp(pw, port)
        _goto_zhipin(page, "https://www.zhipin.com/web/geek/job")

        for city, code in CITY_CODES.items():
            for query in SEARCH_QUERIES:
                page_num = 1
                while page_num <= max_pages:
                    q = requests.utils.quote(query)
                    url = (
                        f"https://www.zhipin.com/wapi/zpgeek/search/joblist.json"
                        f"?scene=1&query={q}&city={code}&page={page_num}&pageSize=30"
                    )
                    try:
                        data = _browser_fetch_json(page, url)
                    except Exception as exc:
                        print(f"[warn] browser {city}/{query} p{page_num}: {exc}")
                        _goto_zhipin(
                            page,
                            f"https://www.zhipin.com/web/geek/job?query={q}&city={code}",
                        )
                        time.sleep(3)
                        try:
                            data = _browser_fetch_json(page, url)
                        except Exception:
                            break
                    if data.get("code") != 0:
                        print(f"[warn] browser API {city}/{query} p{page_num}: code={data.get('code')}")
                        _goto_zhipin(
                            page,
                            f"https://www.zhipin.com/web/geek/job?query={q}&city={code}",
                        )
                        time.sleep(4)
                        try:
                            data = _browser_fetch_json(page, url)
                        except Exception:
                            break
                        if data.get("code") != 0:
                            break
                    zp = data.get("zpData") or {}
                    items = zp.get("jobList") or []
                    if not items:
                        break
                    added = 0
                    for item in items:
                        job = job_from_api(item, city)
                        if _accept_job(job, seen, require_active):
                            job.match_tags = detect_tags(job.title)
                            all_jobs.append(job)
                            added += 1
                    print(f"  {city}/{query} p{page_num}: +{added} (累计 {len(all_jobs)})")
                    if not zp.get("hasMore"):
                        break
                    page_num += 1
                    time.sleep(2.5)

        if fetch_detail and all_jobs:
            print(f"拉取 {len(all_jobs)} 条详情（浏览器内）…")
            enrich_details_page(page, all_jobs)
    except Exception as exc:
        print(f"[error] 浏览器采集失败: {exc}")
    finally:
        print("[info] 采集结束，Chrome 窗口保持打开，请手动关闭")
        _ = proc
    return all_jobs


def enrich_details_page(page: Any, jobs: list[Job]) -> None:
    for i, job in enumerate(jobs, 1):
        if not job.security_id:
            continue
        url = f"https://www.zhipin.com/wapi/zpgeek/job/detail.json?securityId={job.security_id}"
        try:
            data = _browser_fetch_json(page, url)
        except Exception:
            continue
        if data.get("code") != 0:
            continue
        detail = (data.get("zpData") or {}).get("jobInfo") or data.get("zpData") or {}
        post = _norm(detail.get("postDescription") or detail.get("jobDesc") or "")
        if post:
            job.jd = post
            job.description = post[:500]
        active = detail.get("activeTimeDesc") or detail.get("activeTime")
        if active:
            job.active_time = active
            job.active_within_30d = active_within_30d(active)
        if i % 10 == 0:
            print(f"  详情 {i}/{len(jobs)}")
        time.sleep(0.8)


def collect_api_playwright(max_pages: int, require_active: bool) -> list[Job]:
    from playwright.sync_api import sync_playwright

    all_jobs: list[Job] = []
    seen: set[str] = set()

    with sync_playwright() as p:
        ctx, page = _launch_browser(p, headless=False, persist=True)
        _goto_zhipin(page, "https://www.zhipin.com/web/geek/job")

        if not _is_logged_in(page, ctx):
            print("需要登录后才能采集。")
            _prompt_login()
            if not _verify_logged_in(page, ctx):
                print("[error] 未检测到登录，采集中止")
                ctx.close()
                return all_jobs

        _save_auth(ctx)

        for city, code in CITY_CODES.items():
            for query in SEARCH_QUERIES:
                page_num = 1
                while page_num <= max_pages:
                    q = requests.utils.quote(query)
                    url = (
                        f"https://www.zhipin.com/wapi/zpgeek/search/joblist.json"
                        f"?scene=1&query={q}&city={code}&page={page_num}&pageSize=30"
                    )
                    try:
                        data = _browser_fetch_json(page, url)
                    except Exception as exc:
                        print(f"[warn] browser {city}/{query} p{page_num}: {exc}")
                        break
                    if data.get("code") != 0:
                        print(f"[warn] browser API {city}/{query} p{page_num}: code={data.get('code')}")
                        break
                    zp = data.get("zpData") or {}
                    items = zp.get("jobList") or []
                    if not items:
                        break
                    added = 0
                    for item in items:
                        job = job_from_api(item, city)
                        if _accept_job(job, seen, require_active):
                            job.match_tags = detect_tags(job.title)
                            all_jobs.append(job)
                            added += 1
                    print(f"  {city}/{query} p{page_num}: +{added} (累计 {len(all_jobs)})")
                    if not zp.get("hasMore"):
                        break
                    page_num += 1
                    time.sleep(1.0)

        ctx.close()
    return all_jobs


def enrich_details_requests(session: requests.Session, jobs: list[Job]) -> None:
    for i, job in enumerate(jobs, 1):
        if not job.security_id:
            continue
        try:
            data = api_detail(session, job.security_id)
        except requests.RequestException:
            continue
        if data.get("code") != 0:
            continue
        detail = (data.get("zpData") or {}).get("jobInfo") or data.get("zpData") or {}
        post = _norm(detail.get("postDescription") or detail.get("jobDesc") or "")
        if post:
            job.jd = post
            job.description = post[:500]
        active = detail.get("activeTimeDesc") or detail.get("activeTime")
        if active:
            job.active_time = active
            job.active_within_30d = active_within_30d(active)
        if i % 10 == 0:
            print(f"  详情 {i}/{len(jobs)}")
        time.sleep(0.6)


def enrich_details_playwright(jobs: list[Job]) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=True, args=["--disable-blink-features=AutomationControlled"])
        except Exception:
            browser = p.chromium.launch(headless=True)
        ctx_kwargs: dict[str, Any] = {"locale": "zh-CN"}
        if AUTH_FILE.exists():
            ctx_kwargs["storage_state"] = str(AUTH_FILE)
        ctx = browser.new_context(**ctx_kwargs)
        page = ctx.new_page()
        page.goto("https://www.zhipin.com/", wait_until="domcontentloaded", timeout=60000)

        for i, job in enumerate(jobs, 1):
            if not job.security_id:
                continue
            url = f"https://www.zhipin.com/wapi/zpgeek/job/detail.json?securityId={job.security_id}"
            try:
                data = _browser_fetch_json(page, url)
            except Exception:
                continue
            if data.get("code") != 0:
                continue
            detail = (data.get("zpData") or {}).get("jobInfo") or data.get("zpData") or {}
            post = _norm(detail.get("postDescription") or detail.get("jobDesc") or "")
            if post:
                job.jd = post
                job.description = post[:500]
            active = detail.get("activeTimeDesc") or detail.get("activeTime")
            if active:
                job.active_time = active
                job.active_within_30d = active_within_30d(active)
            if i % 10 == 0:
                print(f"  详情 {i}/{len(jobs)}")
            time.sleep(0.6)
        browser.close()


def collect_api(
    max_pages: int, require_active: bool, *, fetch_detail: bool = False
) -> list[Job]:
    session = load_session()
    probe = api_joblist_retry(session, "区块链", "101010100", 1)
    if probe.get("code") == 0:
        print("使用 requests + Cookie 采集（带退避重试）…")
        jobs = collect_api_requests(session, max_pages, require_active)
        if fetch_detail and jobs:
            print(f"拉取 {len(jobs)} 条详情（浏览器）…")
            enrich_details_via_browser(jobs)
        return jobs

    cookies: list[dict[str, Any]] = []
    if COOKIES_FILE.exists():
        raw = json.loads(COOKIES_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            cookies = raw
    if _has_login_cookies_list(cookies):
        print("requests 受限，改用 Chrome 浏览器内 fetch 采集…")
        return collect_api_cdp(max_pages, require_active, fetch_detail=fetch_detail)

    print("requests 不可用 (code=%s)，改用 Playwright 浏览器采集…" % probe.get("code"))
    jobs = collect_api_playwright(max_pages, require_active)
    if fetch_detail and jobs:
        enrich_details_playwright(jobs)
    return jobs


def enrich_details_via_browser(jobs: list[Job]) -> None:
    port = find_active_cdp_port()
    proc: subprocess.Popen[Any] | None = None
    if port is None:
        proc, port = _launch_chrome_profile("https://www.zhipin.com/web/geek/job")
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    try:
        _browser, _ctx, page = _connect_cdp(pw, port)
        enrich_details_page(page, jobs)
    except Exception as exc:
        print(f"[warn] 浏览器详情失败: {exc}")
    finally:
        _ = proc


def collect_cache() -> list[Job]:
    all_jobs: list[Job] = []
    seen: set[str] = set()
    if not SEED_DIR.exists():
        return all_jobs
    for path in sorted(SEED_DIR.glob("*.md")):
        city = path.stem
        for c in CITY_CODES:
            if c in path.stem:
                city = c
                break
        for job in parse_markdown_blocks(path.read_text(encoding="utf-8"), city, str(path)):
            key = job.job_id or job.url
            if key in seen:
                continue
            if is_match(job.title):
                seen.add(key)
                job.match_tags = detect_tags(job.title)
                all_jobs.append(job)
    return all_jobs



def _clear_session() -> None:
    import shutil

    for p in (AUTH_FILE, COOKIES_FILE):
        if p.exists():
            p.unlink()
    if PW_PROFILE.exists():
        shutil.rmtree(PW_PROFILE, ignore_errors=True)
    print("已清除 auth.json / cookies.json / .browser_profile")


def login_and_save() -> None:
    proc: subprocess.Popen[Any] | None = None
    port = 0
    try:
        proc, port = _launch_chrome_for_login()
    except Exception as exc:
        print(f"[error] 无法启动 Chrome: {exc}")
        print("请确认已安装 Google Chrome，或手动打开 Chrome 登录后重试。")
        return

    print("浏览器已打开。未完成登录前，脚本不会保存任何文件。")
    _prompt_login()

    if proc.poll() is not None:
        print("[error] Chrome 已关闭，请重新运行: python scrape.py --login")
        return

    capture_auth_from_port(port)


def _render_city_md(city: str, items: list[Job], *, show_home_city: bool = False) -> str:
    if not items:
        return (
            f"# {city} · 区块链 / Web3 开发岗\n\n"
            f"共 **0** 条 · 采集日 {date.today()}\n\n"
            f"暂无岗位。请 `python scrape.py --mode api --fetch-detail` 重新采集。\n"
        )
    lines = [
        f"# {city} · 区块链 / Web3 开发岗",
        "",
        f"共 **{len(items)}** 条 · 采集日 {date.today()} · 近一月活跃",
        "",
    ]
    if show_home_city:
        lines += [
            "| 职位 | 薪资 | 归属城市 | 活跃 | 标签 | 公司 |",
            "|------|------|----------|------|------|------|",
        ]
        for j in items:
            lines.append(
                f"| [{j.title}]({j.url}) | {j.salary} | {j.city} | {j.active_time or '—'} | "
                f"{'·'.join(j.match_tags)} | {j.company} |"
            )
    else:
        lines += [
            "| 职位 | 薪资 | 活跃 | 标签 | 公司 |",
            "|------|------|------|------|------|",
        ]
        for j in items:
            lines.append(
                f"| [{j.title}]({j.url}) | {j.salary} | {j.active_time or '—'} | "
                f"{'·'.join(j.match_tags)} | {j.company} |"
            )
    lines.append("")
    for idx, j in enumerate(items, 1):
        lines += [
            f"## {idx}. {j.title}",
            "",
            f"- **薪资**：{j.salary}",
            f"- **地点**：{j.location}",
        ]
        if show_home_city:
            lines.append(f"- **归属城市**：{j.city}")
        lines += [
            f"- **经验/学历**：{j.experience} · {j.education}",
            f"- **公司**：{j.company}",
            f"- **活跃**：{j.active_time or '—'}",
            f"- **链接**：{j.url}",
            "",
            "**职位描述（JD）**",
            "",
            j.jd or j.description or "（无详情）",
            "",
            "---",
            "",
        ]
    return "\n".join(lines)


def write_city_md(jobs: list[Job], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    by_city: dict[str, list[Job]] = {c: [] for c in CITY_CODES}
    for j in jobs:
        by_city.setdefault(j.city, []).append(j)
    for city, items in by_city.items():
        (out_dir / f"{city}.md").write_text(_render_city_md(city, items), encoding="utf-8")
    remote_jobs = sorted([j for j in jobs if j.remote], key=lambda j: (j.city, j.title))
    (out_dir / "远程.md").write_text(
        _render_city_md("远程", remote_jobs, show_home_city=True), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Boss 直聘区块链/Web3/钱包 开发岗采集")
    parser.add_argument("--login", action="store_true", help="浏览器登录并保存 Cookie")
    parser.add_argument("--clear-session", action="store_true", help="清除登录缓存后退出")
    parser.add_argument("--mode", choices=("browser", "api", "cache"), default="browser")
    parser.add_argument("--max-pages", type=int, default=20, help="每关键词最大翻页数")
    parser.add_argument("--no-active-filter", action="store_true", help="不过滤近一月活跃")
    parser.add_argument("--fetch-detail", action="store_true", help="拉取 detail.json 完整 JD")
    args = parser.parse_args()

    if args.clear_session:
        _clear_session()
        return

    if args.login:
        login_and_save()
        return

    require_active = not args.no_active_filter

    if args.mode == "browser":
        jobs = collect_browser(args.max_pages, require_active, fetch_detail=args.fetch_detail)
    elif args.mode == "api":
        jobs = collect_api(args.max_pages, require_active, fetch_detail=args.fetch_detail)
    else:
        jobs = collect_cache()

    jobs.sort(key=lambda j: (j.city, j.title))
    for j in jobs:
        j.remote = is_remote(j)

    if not jobs and OUT_JSON.exists():
        try:
            old = json.loads(OUT_JSON.read_text(encoding="utf-8"))
            if int(old.get("count") or 0) > 0:
                print(f"[warn] 本次采集 0 条，保留原 jobs.json（{old['count']} 条）")
                return
        except Exception:
            pass

    payload = {
        "updated": str(date.today()),
        "filter": "近一月活跃 + title 含区块链/以太坊/web3/钱包 + 开发岗",
        "activity_rule": "activeTimeDesc：本月活跃及更近档位保留；半年前等排除",
        "search_queries": list(SEARCH_QUERIES),
        "mode": args.mode,
        "count": len(jobs),
        "jobs": [asdict(j) for j in jobs],
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_city_md(jobs, ROOT / "cities")
    print(f"写入 {len(jobs)} 条 -> {OUT_JSON}")


if __name__ == "__main__":
    main()
