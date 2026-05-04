"""LeetCode GraphQL API client with local caching."""

import json
import sys
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
LEETCODE_CN_GRAPHQL_URL = "https://leetcode.cn/graphql"
CACHE_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_FILE = CACHE_DIR / "problems.json"
CN_CACHE_FILE = CACHE_DIR / "problems_cn.json"

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://leetcode.com",
}

CN_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://leetcode.cn",
}

QUERY_BY_SLUG = """
query getQuestionDetail($slug: String!) {
    question(titleSlug: $slug) {
        questionFrontendId
        title
        titleSlug
        difficulty
        content
        topicTags { name }
        exampleTestcases
    }
}
"""

QUERY_ALL_TITLES = """
query problemsetQuestionList {
    problemsetQuestionList: questionList(
        categorySlug: ""
        limit: 3000
        skip: 0
        filters: {}
    ) {
        data {
            frontendQuestionId: questionFrontendId
            title
            titleSlug
            difficulty
        }
    }
}
"""

# 中国站查询语句
QUERY_BY_SLUG_CN = """
query getQuestionDetail($titleSlug: String!) {
    question(titleSlug: $titleSlug) {
        questionFrontendId
        title
        titleCn
        titleSlug
        difficulty
        difficultyCn
        content
        translatedContent
        topicTags {
            name
            nameTranslated
        }
        exampleTestcases
    }
}
"""

QUERY_ALL_TITLES_CN = """
query problemsetQuestionList {
    problemsetQuestionList: questionList(
        categorySlug: ""
        limit: 3000
        skip: 0
        filters: {}
    ) {
        data {
            frontendQuestionId: questionFrontendId
            title
            titleCn
            titleSlug
            difficulty
            difficultyCn
        }
    }
}
"""


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _load_cn_cache() -> dict:
    if CN_CACHE_FILE.exists():
        with open(CN_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cn_cache(cache: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CN_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _graphql(query: str, variables: dict, use_cn: bool = False) -> dict:
    url = LEETCODE_CN_GRAPHQL_URL if use_cn else LEETCODE_GRAPHQL_URL
    headers = CN_HEADERS if use_cn else HEADERS
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = Request(url, data=payload, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        site = "leetcode.cn" if use_cn else "leetcode.com"
        raise ConnectionError(f"LeetCode {site} API returned HTTP {e.code}") from e
    except URLError as e:
        raise ConnectionError(f"Network error: {e.reason}") from e


def _fetch_title_slug_map(use_cn: bool = False) -> dict:
    """Fetch mapping from problem number to titleSlug."""
    query = QUERY_ALL_TITLES_CN if use_cn else QUERY_ALL_TITLES
    data = _graphql(query, {}, use_cn=use_cn)
    items = data["data"]["problemsetQuestionList"]["data"]
    return {item["frontendQuestionId"]: item["titleSlug"] for item in items}


def _parse_html_content(html: str) -> str:
    """Strip HTML tags for readable plain text."""
    import re
    text = re.sub(r"<p>", "\n", html)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<li>", "\n- ", text)
    text = re.sub(r"<sup>", "^", text)
    text = re.sub(r"</sup>", "", text)
    text = re.sub(r"<pre>", "\n```\n", text)
    text = re.sub(r"</pre>", "\n```\n", text)
    text = re.sub(r"<code>", "`", text)
    text = re.sub(r"</code>", "`", text)
    text = re.sub(r"<strong>", "**", text)
    text = re.sub(r"</strong>", "**", text)
    text = re.sub(r"<em>", "*", text)
    text = re.sub(r"</em>", "*", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def get_problem(problem_number: int, use_cn: bool = False) -> dict:
    """Fetch a LeetCode problem by its number.

    Args:
        problem_number: The problem number
        use_cn: If True, fetch from leetcode.cn (Chinese version)

    Returns a dict with keys:
        number, title, difficulty, description, examples, tags, titleSlug
    """
    # Check cache first
    if use_cn:
        cache = _load_cn_cache()
    else:
        cache = _load_cache()
    key = str(problem_number)
    if key in cache:
        return cache[key]

    # Resolve number -> slug
    slug_map = _fetch_title_slug_map(use_cn=use_cn)
    slug = slug_map.get(str(problem_number))
    if not slug:
        site = "leetcode.cn" if use_cn else "LeetCode"
        raise ValueError(f"Problem #{problem_number} not found on {site}")

    # Fetch full detail
    query = QUERY_BY_SLUG_CN if use_cn else QUERY_BY_SLUG
    data = _graphql(query, {"slug": slug, "titleSlug": slug}, use_cn=use_cn)
    q = data["data"]["question"]
    if not q:
        raise ValueError(f"Problem #{problem_number} (slug: {slug}) returned no data")

    # 获取描述（优先使用翻译版本）
    if use_cn:
        description = _parse_html_content(q.get("translatedContent") or q.get("content") or "")
    else:
        description = _parse_html_content(q["content"] or "")

    # Extract example blocks from description
    examples = []
    import re
    for m in re.finditer(
        r"\*\*(?:Example|示例)\s*(\d+):\*\*\s*\n(.*?)(?=\n\*\*(?:Example|示例)|\n\*\*(?:Constraints|限制条件)|\Z)",
        description,
        re.DOTALL,
    ):
        examples.append(m.group(2).strip())

    # 构建问题对象
    if use_cn:
        problem = {
            "number": problem_number,
            "title": q.get("titleCn") or q.get("title"),
            "titleSlug": q["titleSlug"],
            "difficulty": q.get("difficultyCn") or q.get("difficulty"),
            "description": description,
            "examples": examples,
            "tags": [t.get("nameTranslated") or t["name"] for t in q.get("topicTags", [])],
        }
    else:
        problem = {
            "number": problem_number,
            "title": q["title"],
            "titleSlug": q["titleSlug"],
            "difficulty": q["difficulty"],
            "description": description,
            "examples": examples,
            "tags": [t["name"] for t in q.get("topicTags", [])],
        }

    # Save to cache
    if use_cn:
        _save_cn_cache(cache)
    else:
        _save_cache(cache)

    # Update cache
    cache[key] = problem
    if use_cn:
        _save_cn_cache(cache)
    else:
        _save_cache(cache)

    return problem


def format_problem(p: dict) -> str:
    """Format a problem dict into a readable string."""
    lines = [
        f"#{p['number']}. {p['title']}",
        f"Difficulty: {p['difficulty']}",
        f"Tags: {', '.join(p['tags'])}",
        "",
        p["description"],
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.leetcode_api <problem_number>")
        sys.exit(1)

    num = int(sys.argv[1])
    try:
        problem = get_problem(num)
        print(format_problem(problem))
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except ConnectionError as e:
        print(f"Error: {e}")
        sys.exit(1)
