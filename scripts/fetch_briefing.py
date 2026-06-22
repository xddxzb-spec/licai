#!/usr/bin/env python3
"""
理财简报 — 每日自动抓取脚本
从配置的新闻源抓取理财相关新闻，生成简报 JSON 数据
输出：data/briefings.json
"""
import json
import os
import re
import sys
import hashlib
import time
from datetime import datetime, timedelta
from collections import OrderedDict

import requests
import feedparser
from bs4 import BeautifulSoup

# 添加脚本目录到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sources import SOURCES, FINANCE_KEYWORDS, VALUATION_KEYWORDS

# ============================================================
# 配置
# ============================================================
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
DATA_FILE = os.path.join(DATA_DIR, "briefings.json")
MAX_ITEMS_PER_SECTION = 5  # 每个板块最多保留几条新闻
MAX_SUMMARY_LENGTH = 800    # 简报摘要总字数上限
REQUEST_TIMEOUT = 15        # 请求超时秒数
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# ============================================================
# 工具函数
# ============================================================
def today_str():
    return datetime.now().strftime("%Y-%m-%d")

def clean_html(html_text):
    """去除 HTML 标签，保留纯文本"""
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "lxml")
    return soup.get_text(separator=" ", strip=True)

def normalize_text(text):
    """规范化文本：去除多余空白、控制字符"""
    if not text:
        return ""
    text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def text_contains_keywords(text, keywords):
    """检查文本是否包含任意关键词"""
    if not text:
        return False
    text_lower = text.lower()
    for kw in keywords:
        if kw.lower() in text_lower:
            return True
    return False

def classify_item(title, text):
    """根据标题和内容分类到理财估值新闻或行业泛新闻"""
    combined = f"{title} {text}"
    if text_contains_keywords(combined, VALUATION_KEYWORDS):
        return "理财估值新闻"
    return "理财行业泛新闻"

def generate_id(title, source):
    """生成新闻条目的唯一 ID"""
    raw = f"{source}:{title}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]

# ============================================================
# RSS 抓取
# ============================================================
def fetch_rss(source):
    """抓取 RSS 源，返回新闻条目列表"""
    items = []
    try:
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(source["url"], headers=headers,
                           timeout=REQUEST_TIMEOUT, allow_redirects=True)
        resp.raise_for_status()

        # 尝试用 feedparser 解析
        feed = feedparser.parse(resp.content)
        if feed.entries:
            for entry in feed.entries[:10]:
                title = normalize_text(entry.get("title", ""))
                summary = normalize_text(clean_html(entry.get("summary", entry.get("description", ""))))
                link = entry.get("link", "")
                published = entry.get("published", entry.get("updated", ""))

                if not title:
                    continue
                if not text_contains_keywords(f"{title} {summary}", FINANCE_KEYWORDS):
                    continue

                items.append({
                    "id": generate_id(title, source["name"]),
                    "title": title[:100],
                    "text": summary[:300] if summary else title,
                    "source": source["name"],
                    "siteUrl": source.get("site_url", ""),
                    "url": link,
                    "category": classify_item(title, summary),
                })
        else:
            # feedparser 解析失败，尝试作为普通 HTML 抓取
            items = _scrape_html_items(resp.text, source)
    except Exception as e:
        print(f"  [WARN] {source['name']} RSS 抓取失败: {e}")
    return items

def _scrape_html_items(html, source):
    """从 HTML 页面中提取新闻标题和链接"""
    items = []
    try:
        soup = BeautifulSoup(html, "lxml")
        # 查找常见的新闻列表结构
        candidates = []
        for tag in soup.find_all(["a", "h2", "h3", "h4"]):
            text = normalize_text(tag.get_text())
            href = tag.get("href", "") if tag.name == "a" else ""
            if not href and tag.name != "a":
                parent_a = tag.find_parent("a")
                if parent_a:
                    href = parent_a.get("href", "")
            if text and len(text) >= 8:
                candidates.append((text, href))

        seen = set()
        for text, href in candidates[:20]:
            if text in seen:
                continue
            seen.add(text)
            if not text_contains_keywords(text, FINANCE_KEYWORDS):
                continue
            item = {
                "id": generate_id(text, source["name"]),
                "title": text[:100],
                "text": text[:300],
                "source": source["name"],
                "siteUrl": source.get("site_url", ""),
                "url": href if href.startswith("http") else "",
                "category": classify_item(text, ""),
            }
            items.append(item)
    except Exception as e:
        print(f"  [WARN] HTML 解析失败: {e}")
    return items

# ============================================================
# API 抓取
# ============================================================
def fetch_api(source):
    """抓取 API 类型来源（如财联社）"""
    items = []
    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
        }
        resp = requests.get(source["url"], headers=headers,
                           timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        # 财联社电报 API 格式
        if source.get("api_type") == "telegraph":
            entries = data.get("data", {}).get("roll_data", [])[:20]
            for entry in entries:
                title = normalize_text(entry.get("title", ""))
                content = normalize_text(clean_html(entry.get("content", "")))
                if not title:
                    continue
                if not text_contains_keywords(f"{title} {content}", FINANCE_KEYWORDS):
                    continue
                items.append({
                    "id": generate_id(title, source["name"]),
                    "title": title[:100],
                    "text": content[:300] if content else title,
                    "source": source["name"],
                    "siteUrl": source.get("site_url", ""),
                    "url": entry.get("shareurl", entry.get("url", "")),
                    "category": classify_item(title, content),
                })
    except Exception as e:
        print(f"  [WARN] {source['name']} API 抓取失败: {e}")
    return items

# ============================================================
# 通用网页抓取
# ============================================================
def fetch_scrape(source):
    """通用网页抓取"""
    items = []
    try:
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(source["url"], headers=headers,
                           timeout=REQUEST_TIMEOUT, allow_redirects=True)
        resp.raise_for_status()
        # 尝试检测编码
        if source.get("encoding"):
            resp.encoding = source["encoding"]
        elif resp.apparent_encoding:
            resp.encoding = resp.apparent_encoding
        items = _scrape_html_items(resp.text, source)
    except Exception as e:
        print(f"  [WARN] {source['name']} 网页抓取失败: {e}")
    return items

# ============================================================
# 主流程：从所有源抓取
# ============================================================
def fetch_all_sources():
    """从所有配置的来源抓取新闻"""
    all_items = []
    fetch_map = {
        "rss": fetch_rss,
        "api": fetch_api,
        "scrape": fetch_scrape,
    }

    for source in SOURCES:
        name = source["name"]
        src_type = source["type"]
        print(f"[FETCH] {name} ({src_type})...")
        try:
            fetcher = fetch_map.get(src_type, fetch_scrape)
            items = fetcher(source)
            print(f"  -> 获取 {len(items)} 条相关新闻")
            all_items.extend(items)
        except Exception as e:
            print(f"  [ERROR] {name} 抓取异常: {e}")

    return all_items

# ============================================================
# 去重与排序
# ============================================================
def deduplicate_items(items):
    """按标题相似度去重，保留第一次出现的条目"""
    seen_ids = set()
    seen_titles = []
    result = []

    for item in items:
        tid = item["id"]
        if tid in seen_ids:
            continue
        # 简单标题去重：前30个字符相同视为重复
        title_prefix = item["title"][:30]
        is_dup = False
        for seen in seen_titles:
            if len(title_prefix) >= 15 and title_prefix[:15] == seen[:15]:
                is_dup = True
                break
        if is_dup:
            continue

        seen_ids.add(tid)
        seen_titles.append(title_prefix)
        result.append(item)

    return result

# ============================================================
# 生成简报
# ============================================================
def build_summary(valuation_items, general_items):
    """根据抓取的新闻生成一段摘要"""
    parts = []
    today = today_str()

    total = len(valuation_items) + len(general_items)
    if total == 0:
        return f"{today}，暂无理财相关重大新闻。请检查信息源配置或稍后重试。"

    parts.append(f"{today}理财市场关注要点：")

    # 估值类摘要
    if valuation_items:
        sources_v = set(i["source"] for i in valuation_items)
        parts.append(f"估值方面共监测到{len(valuation_items)}条相关动态")
        parts.append(f"来源覆盖{'、'.join(list(sources_v)[:4])}等渠道")
        # 取前三条标题加入摘要
        for item in valuation_items[:3]:
            parts.append(f"——{item['title']}（{item['source']}）")

    # 行业类摘要
    if general_items:
        sources_g = set(i["source"] for i in general_items)
        parts.append(f"行业动态方面共监测到{len(general_items)}条相关新闻")
        parts.append(f"来源覆盖{'、'.join(list(sources_g)[:4])}等渠道")
        for item in general_items[:3]:
            parts.append(f"——{item['title']}（{item['source']}）")

    return "；".join(parts)

def generate_briefing():
    """主函数：抓取新闻并生成简报 JSON"""
    print("=" * 60)
    print(f"  理财简报抓取器 — {today_str()}")
    print("=" * 60)

    # 1. 抓取
    print("\n[STEP 1] 抓取新闻...")
    all_items = fetch_all_sources()

    if not all_items:
        print("\n[WARN] 未抓取到任何新闻，将生成空简报")
        briefing = _build_empty_briefing()
        _save_briefing(briefing)
        return briefing

    # 2. 去重
    print(f"\n[STEP 2] 去重前共 {len(all_items)} 条...")
    items = deduplicate_items(all_items)
    print(f"  去重后共 {len(items)} 条")

    # 3. 分类
    valuation_items = [i for i in items if i["category"] == "理财估值新闻"]
    general_items = [i for i in items if i["category"] == "理财行业泛新闻"]

    # 如果某类为空，从另一类中分流一些
    if not valuation_items and general_items:
        for item in general_items[:]:
            if classify_item(item["title"], item["text"]) == "理财估值新闻":
                item["category"] = "理财估值新闻"
                valuation_items.append(item)
                general_items.remove(item)
    if not general_items and valuation_items:
        for item in valuation_items[:]:
            item["category"] = "理财行业泛新闻"
            general_items.append(item)
            valuation_items.remove(item)

    print(f"  理财估值新闻: {len(valuation_items)} 条")
    print(f"  理财行业泛新闻: {len(general_items)} 条")

    # 4. 生成简报
    print(f"\n[STEP 3] 生成简报...")
    today = today_str()
    summary = build_summary(valuation_items, general_items)

    # 截断摘要到 800 字
    if len(summary) > MAX_SUMMARY_LENGTH:
        summary = summary[:MAX_SUMMARY_LENGTH-3] + "..."

    briefing = {
        "date": today,
        "title": "每日理财简报",
        "summary": summary,
        "sections": [
            {
                "title": "理财估值新闻",
                "items": valuation_items[:MAX_ITEMS_PER_SECTION],
            },
            {
                "title": "理财行业泛新闻",
                "items": general_items[:MAX_ITEMS_PER_SECTION],
            },
        ],
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "total_fetched": len(all_items),
            "total_published": len(valuation_items[:MAX_ITEMS_PER_SECTION]) + len(general_items[:MAX_ITEMS_PER_SECTION]),
            "sources_used": list(set(i["source"] for i in items)),
        },
    }

    _save_briefing(briefing)
    return briefing

def _build_empty_briefing():
    """生成一个空简报模板"""
    today = today_str()
    return {
        "date": today,
        "title": "每日理财简报",
        "summary": f"{today}，暂无理财相关重大新闻更新。",
        "sections": [
            {"title": "理财估值新闻", "items": []},
            {"title": "理财行业泛新闻", "items": []},
        ],
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "total_fetched": 0,
            "total_published": 0,
            "sources_used": [],
        },
    }

# ============================================================
# 数据存取
# ============================================================
def load_existing_data():
    """加载已有的简报数据"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, IOError) as e:
            print(f"  [WARN] 读取已有数据失败: {e}")
    return {}


def _save_briefing(briefing):
    """保存当日报简报，合并到已有数据中"""
    os.makedirs(DATA_DIR, exist_ok=True)

    data = load_existing_data()
    date = briefing["date"]
    data[date] = briefing

    # 清理超过 180 天的旧数据
    cutoff = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    dates_to_remove = [d for d in data if d < cutoff]
    for d in dates_to_remove:
        del data[d]
    if dates_to_remove:
        print(f"  清理了 {len(dates_to_remove)} 条超过 180 天的旧简报")

    # 保证日期有序
    sorted_data = OrderedDict(sorted(data.items(), reverse=True))
    # 限制最多保留 200 条
    while len(sorted_data) > 200:
        sorted_data.popitem(last=True)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted_data, f, ensure_ascii=False, indent=2)

    print(f"\n  简报已保存: {DATA_FILE}")
    print(f"  现存 {len(sorted_data)} 条简报数据")


# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    try:
        briefing = generate_briefing()
        print(f"\n{'=' * 60}")
        print(f"  ✅ 抓取完成！今日简报已生成")
        print(f"  日期: {briefing['date']}")
        print(f"  估值新闻: {len(briefing['sections'][0]['items'])} 条")
        print(f"  行业新闻: {len(briefing['sections'][1]['items'])} 条")
        print(f"  摘要字数: {len(briefing['summary'])}")
        print(f"{'=' * 60}")
    except Exception as e:
        print(f"\n[FATAL] 抓取失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
