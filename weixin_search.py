#!/usr/bin/env python3
"""微信公众号搜索 - 多引擎 Playwright 浏览器版

搜索引擎：搜狗微信、百度、Google
内容获取：Playwright 直接渲染 + web.archive.org 兜底
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import quote


# ── 工具函数 ──────────────────────────────────────────────

def _deduplicate(results: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    unique = []
    for r in results:
        key = re.sub(r'\s+', '', r.get("title", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(r)
    return unique


def _parse_sogou_time(raw: str) -> str:
    m = re.search(r"timeConvert\('(\d+)'\)", raw)
    if m:
        return datetime.fromtimestamp(int(m.group(1))).strftime("%Y-%m-%d %H:%M")
    return raw.strip() if raw else ""


def _parse_date_text(text: str) -> str:
    if not text:
        return ""
    m = re.search(r'(\d{4})[年./-](\d{1,2})[月./-](\d{1,2})', text)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
    m = re.search(r'(\d+)\s*天前', text)
    if m:
        return (datetime.now() - timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")
    m = re.search(r'(\d+)\s*小时前', text)
    if m:
        return (datetime.now() - timedelta(hours=int(m.group(1)))).strftime("%Y-%m-%d %H:%M")
    m = re.search(r'(\d+)\s*分钟前', text)
    if m:
        return (datetime.now() - timedelta(minutes=int(m.group(1)))).strftime("%Y-%m-%d %H:%M")
    return text.strip()


# ── 搜索引擎 ─────────────────────────────────────────────

def _search_sogou(page, query: str, pages: int) -> List[Dict[str, str]]:
    results = []
    for pg in range(1, pages + 1):
        url = f"https://weixin.sogou.com/weixin?type=2&s_from=input&query={quote(query)}&ie=utf8&page={pg}"
        try:
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)
            if "antispider" in page.url.lower():
                break
            items = page.query_selector_all("ul.news-list li .txt-box")
            if not items:
                break
            for item in items:
                title_el = item.query_selector("h3 a")
                time_el = item.query_selector(".s-p .s2")
                if not title_el:
                    continue
                title = (title_el.inner_text() or "").strip()
                link = title_el.get_attribute("href") or ""
                if link and not link.startswith("http"):
                    link = "https://weixin.sogou.com" + link
                raw_time = (time_el.inner_text() or "").strip() if time_el else ""
                results.append({
                    "title": title,
                    "link": link,
                    "real_url": "",
                    "publish_time": _parse_sogou_time(raw_time),
                    "source": "sogou",
                })
        except Exception:
            break
        if pg < pages:
            page.wait_for_timeout(1500)
    return results


def _search_baidu(page, query: str, pages: int) -> List[Dict[str, str]]:
    results = []
    for pg in range(pages):
        url = f"https://www.baidu.com/s?wd=site%3Aqq.com+{quote(query)}&pn={pg * 10}"
        try:
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            items = page.query_selector_all("#content_left .c-container")
            if not items:
                break
            for item in items:
                title_el = item.query_selector("h3 a") or item.query_selector(".c-title a")
                if not title_el:
                    continue
                title = (title_el.inner_text() or "").strip()
                link = title_el.get_attribute("href") or ""
                mu = item.get_attribute("mu") or ""
                real_url = mu if "qq.com" in mu else ""
                time_text = ""
                for sel in [".c-color-gray2", ".c-color-gray", "span.c-font-normal"]:
                    el = item.query_selector(sel)
                    if el:
                        t = (el.inner_text() or "").strip()
                        if re.search(r'\d', t):
                            time_text = t
                            break
                results.append({
                    "title": title,
                    "link": link,
                    "real_url": real_url,
                    "publish_time": _parse_date_text(time_text),
                    "source": "baidu",
                })
        except Exception:
            break
        if pg < pages:
            page.wait_for_timeout(1500)
    return results


def _search_google(page, query: str, pages: int) -> List[Dict[str, str]]:
    results = []
    for pg in range(pages):
        url = f"https://www.google.com/search?q=site%3Aqq.com+{quote(query)}&start={pg * 10}&hl=zh-CN"
        try:
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            if "sorry" in page.url.lower():
                break
            items = page.query_selector_all("div.g")
            if not items:
                break
            for item in items:
                title_el = item.query_selector("h3")
                link_el = item.query_selector("a")
                if not title_el or not link_el:
                    continue
                title = (title_el.inner_text() or "").strip()
                href = link_el.get_attribute("href") or ""
                real_url = href if "qq.com" in href else ""
                time_text = ""
                snippet_el = item.query_selector(".VwiC3b")
                if snippet_el:
                    text = snippet_el.inner_text() or ""
                    dm = re.match(r'(\d{4}年\d{1,2}月\d{1,2}日)', text)
                    if dm:
                        time_text = dm.group(1)
                results.append({
                    "title": title,
                    "link": href,
                    "real_url": real_url,
                    "publish_time": _parse_date_text(time_text),
                    "source": "google",
                })
        except Exception:
            break
        if pg < pages:
            page.wait_for_timeout(2000)
    return results


# ── URL 解析 ─────────────────────────────────────────────

def _resolve_redirect(page, url: str) -> str:
    try:
        page.goto(url, timeout=15000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        final = page.url
        if "qq.com" in final:
            return final
    except Exception:
        pass
    return ""


# ── 内容获取 ─────────────────────────────────────────────

_CONTENT_SELECTORS = [
    "#js_content",           # 微信公众号
    ".content-article",      # 腾讯新闻
    "#ArticleContent",       # 腾讯新闻旧版
    ".LEFT .content",        # QQ 看点
    "article",               # 通用
    ".rich_media_content",   # 微信备用
]


def _get_content_direct(page, url: str) -> str:
    page.goto(url, timeout=20000, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    for sel in _CONTENT_SELECTORS:
        el = page.query_selector(sel)
        if el:
            text = el.inner_text().strip()
            if text:
                return text
    return ""


def _get_content_archive(page, url: str) -> str:
    archive = f"https://web.archive.org/web/{url}"
    page.goto(archive, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    for sel in _CONTENT_SELECTORS:
        el = page.query_selector(sel)
        if el:
            text = el.inner_text().strip()
            if text:
                return text
    return ""


# ── 主入口 ───────────────────────────────────────────────

def search(query: str, pages: int = 3, engines: Optional[List[str]] = None) -> List[Dict[str, str]]:
    from playwright.sync_api import sync_playwright

    if engines is None:
        engines = ["sogou", "baidu"]

    engine_funcs = {
        "sogou": _search_sogou,
        "baidu": _search_baidu,
        "google": _search_google,
    }

    all_results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/137.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
        )
        page = ctx.new_page()

        for engine in engines:
            fn = engine_funcs.get(engine)
            if not fn:
                continue
            try:
                all_results.extend(fn(page, query, pages))
            except Exception as e:
                sys.stderr.write(f"[{engine}] 搜索失败: {e}\n")

        # 在同一会话中解析搜狗重定向链接，避免新会话被反爬拦截
        for r in all_results:
            if r["source"] == "sogou" and not r["real_url"] and r["link"]:
                try:
                    resolved = _resolve_redirect(page, r["link"])
                    if resolved:
                        r["real_url"] = resolved
                except Exception:
                    pass

        browser.close()

    return _deduplicate(all_results)


def get_content(url: str) -> str:
    from playwright.sync_api import sync_playwright

    if not url:
        return "未提供 URL"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/137.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
        )
        page = ctx.new_page()
        content = ""
        weixin_url = url

        # Step 1: 如果是重定向链接，先解析到真实 URL
        if "sogou.com" in url or "baidu.com" in url:
            resolved = _resolve_redirect(page, url)
            if resolved:
                weixin_url = resolved
            else:
                browser.close()
                return "无法解析文章链接（可能触发反爬）"

        # Step 2: 直接获取微信文章内容
        try:
            content = _get_content_direct(page, weixin_url)
        except Exception:
            pass

        # Step 3: web.archive.org 兜底
        if not content and "qq.com" in weixin_url:
            try:
                content = _get_content_archive(page, weixin_url)
                if content:
                    content = "[来源: web.archive.org 存档]\n\n" + content
            except Exception:
                pass

        browser.close()

    return content if content else "获取文章内容失败"


# ── requests 降级（Playwright 不可用时） ──────────────────

def _fallback_search(query: str, pages: int) -> List[Dict[str, str]]:
    import requests
    from lxml import html

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": f"https://weixin.sogou.com/weixin?query={quote(query)}",
    }
    all_results = []
    for pg in range(1, pages + 1):
        params = {"type": "2", "s_from": "input", "query": query, "ie": "utf8", "page": pg}
        try:
            resp = requests.get("https://weixin.sogou.com/weixin", params=params,
                                headers=headers, timeout=15)
            if resp.status_code != 200 or "antispider" in resp.url.lower():
                break
            tree = html.fromstring(resp.text)
            elements = tree.xpath("//a[contains(@id, 'sogou_vr_11002601_title_')]")
            times = tree.xpath(
                "//li[contains(@id, 'sogou_vr_11002601_box_')]"
                "/div[@class='txt-box']/div[@class='s-p']/span[@class='s2']"
            )
            if not elements:
                break
            for elem, time_elem in zip(elements, times):
                title = elem.text_content().strip()
                link = elem.get("href", "")
                if link and not link.startswith("http"):
                    link = "https://weixin.sogou.com" + link
                all_results.append({
                    "title": title, "link": link, "real_url": "",
                    "publish_time": _parse_sogou_time(time_elem.text_content().strip()),
                    "source": "sogou",
                })
        except Exception:
            break
        if pg < pages:
            import time; time.sleep(1)
    return all_results


# ── CLI ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="微信公众号搜索（多引擎）")
    sub = parser.add_subparsers(dest="command")

    sp = sub.add_parser("search", help="搜索文章")
    sp.add_argument("query", help="搜索关键词")
    sp.add_argument("--pages", type=int, default=3, help="每个引擎搜索页数")
    sp.add_argument("--engines", default="sogou,baidu",
                    help="搜索引擎，逗号分隔 (sogou,baidu,google)")

    cp = sub.add_parser("content", help="获取文章内容")
    cp.add_argument("url", help="文章 URL（支持微信/搜狗/百度链接）")

    args = parser.parse_args()

    if args.command == "search":
        engines = [e.strip() for e in args.engines.split(",")]
        try:
            results = search(args.query, args.pages, engines)
        except Exception:
            sys.stderr.write("[weixin_search] Playwright 不可用，降级为 requests\n")
            results = _fallback_search(args.query, args.pages)
        print(json.dumps(results, ensure_ascii=False, indent=2))

    elif args.command == "content":
        text = get_content(args.url)
        print(text)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
