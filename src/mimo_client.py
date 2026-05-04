"""MiMo API client — OpenAI-compatible chat completions."""

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ---------------------------------------------------------------------------
# 从 .env 文件加载环境变量（不依赖第三方库）
# ---------------------------------------------------------------------------

def _load_env():
    """读取项目根目录下的 .env 文件，写入 os.environ。"""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip()
            # 不覆盖已有的环境变量（系统设置优先）
            if key not in os.environ:
                os.environ[key] = value

_load_env()


# ---------------------------------------------------------------------------
# 配置项
# ---------------------------------------------------------------------------

BASE_URL = os.environ.get("MIMO_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")
API_KEY  = os.environ.get("MIMO_API_KEY", "")
MODEL    = os.environ.get("MIMO_MODEL", "mimo-v2-pro")


# ---------------------------------------------------------------------------
# 累计 token 统计
# ---------------------------------------------------------------------------

class TokenUsage:
    """记录本次会话累计消耗的 token 数。"""
    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0

    def update(self, usage: dict):
        """从 API 响应的 usage 字段累加。"""
        self.prompt_tokens     += usage.get("prompt_tokens", 0)
        self.completion_tokens += usage.get("completion_tokens", 0)
        self.total_tokens      += usage.get("total_tokens", 0)

    def summary(self) -> str:
        return (
            f"[Token 统计] prompt: {self.prompt_tokens}, "
            f"completion: {self.completion_tokens}, "
            f"total: {self.total_tokens}"
        )


# 模块级别的全局计数器，整个会话共享
token_usage = TokenUsage()


# ---------------------------------------------------------------------------
# 核心调用函数
# ---------------------------------------------------------------------------

def chat(messages: list[dict], model: str | None = None, temperature: float = 0.7) -> tuple:
    """调用 MiMo Chat Completions API。

    Args:
        messages: OpenAI 格式的消息列表，如 [{"role": "user", "content": "..."}]
        model:    模型名称，默认使用 .env 中的 MIMO_MODEL
        temperature: 温度参数，越低越确定

    Returns:
        (回复文本, token统计字典)
    """
    if not API_KEY:
        raise RuntimeError(
            "未配置 MIMO_API_KEY，请在 .env 文件中填写。\n"
            "示例：MIMO_API_KEY=your-api-key-here"
        )

    url = f"{BASE_URL.rstrip('/')}/chat/completions"
    payload = json.dumps({
        "model": model or MODEL,
        "messages": messages,
        "temperature": temperature,
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    req = Request(url, data=payload, headers=headers, method="POST")

    try:
        with urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise ConnectionError(f"MiMo API HTTP {e.code}: {body}") from e
    except URLError as e:
        raise ConnectionError(f"网络错误: {e.reason}") from e

    # 累计 token 用量
    usage = data.get("usage", {})
    if usage:
        token_usage.update(usage)

    # 提取回复文本
    choice = data["choices"][0]
    content = choice["message"]["content"]
    
    return content, {
        "prompt": usage.get("prompt_tokens", 0),
        "completion": usage.get("completion_tokens", 0),
        "total": usage.get("total_tokens", 0)
    }


def get_token_summary() -> str:
    """返回当前会话的 token 消耗摘要。"""
    return token_usage.summary()
