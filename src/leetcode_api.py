"""LeetCode GraphQL API client with local caching."""

import json
import sys
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
CACHE_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_FILE = CACHE_DIR / "problems.json"

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://leetcode.com",
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


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _graphql(query: str, variables: dict) -> dict:
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = Request(LEETCODE_GRAPHQL_URL, data=payload, headers=HEADERS, method="POST")
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        raise ConnectionError(f"LeetCode API returned HTTP {e.code}") from e
    except URLError as e:
        raise ConnectionError(f"Network error: {e.reason}") from e


def _fetch_title_slug_map() -> dict:
    """Fetch mapping from problem number to titleSlug."""
    data = _graphql(QUERY_ALL_TITLES, {})
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


def get_problem(problem_number: int) -> dict:
    """Fetch a LeetCode problem by its number.

    Returns a dict with keys:
        number, title, difficulty, description, examples, tags, titleSlug
    """
    # Check cache first
    cache = _load_cache()
    key = str(problem_number)
    if key in cache:
        return cache[key]

    # Resolve number -> slug
    slug_map = _fetch_title_slug_map()
    slug = slug_map.get(str(problem_number))
    if not slug:
        raise ValueError(f"Problem #{problem_number} not found on LeetCode")

    # Fetch full detail
    data = _graphql(QUERY_BY_SLUG, {"slug": slug})
    q = data["data"]["question"]
    if not q:
        raise ValueError(f"Problem #{problem_number} (slug: {slug}) returned no data")

    description = _parse_html_content(q["content"] or "")

    # Extract example blocks from description
    examples = []
    import re
    for m in re.finditer(
        r"\*\*Example\s*(\d+):\*\*\s*\n(.*?)(?=\n\*\*Example|\n\*\*Constraints|\Z)",
        description,
        re.DOTALL,
    ):
        examples.append(m.group(2).strip())

    problem = {
        "number": problem_number,
        "title": q["title"],
        "titleSlug": q["titleSlug"],
        "difficulty": q["difficulty"],
        "description": description,
        "examples": examples,
        "tags": [t["name"] for t in q["topicTags"]],
    }

    # Save to cache
    cache[key] = problem
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
