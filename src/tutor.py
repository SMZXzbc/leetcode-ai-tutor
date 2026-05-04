"""LeetCode AI Tutor — 引导式解题教练。

整合 leetcode_api（题目获取）和 mimo_client（AI 对话），
提供三种模式：
  /hint     — 给思路方向，不给答案
  /analyze  — 分析用户提交的代码
  /similar  — 推荐相似题目
"""

import sys

from src.leetcode_api import get_problem, format_problem
from src.mimo_client import chat, get_token_summary


# ---------------------------------------------------------------------------
# Prompt 模板：导师人设
# ---------------------------------------------------------------------------

# 系统提示：定义 AI 教练的角色和行为准则
SYSTEM_PROMPT = """你是一位资深的算法教练，名叫"小Mo"。你的教学风格：

1. **引导式教学**：永远不直接给出完整代码答案。用提问引导学生自己思考。
2. **启发思路**：先帮学生理解题目本质，再引导他想到合适的数据结构和算法。
3. **循序渐进**：
   - 先让学生理解问题
   - 再引导思考暴力解法
   - 然后启发优化方向
   - 最后讨论复杂度
4. **鼓励为主**：肯定学生的思路，温和地指出可以改进的地方。
5. **中文交流**：用中文回答，技术术语可以保留英文。

记住：你是教练，不是答题器。你的目标是让学生学会自己解题。"""


def build_hint_prompt(problem: dict) -> list[dict]:
    """构建"要提示"的消息列表。"""
    user_msg = f"""请给我一道题的思考方向提示：

题目：#{problem['number']}. {problem['title']}
难度：{problem['difficulty']}
标签：{', '.join(problem['tags'])}

题目描述：
{problem['description']}

请给我：
1. 这道题的核心考点是什么？
2. 适合用什么数据结构/算法？（不要直接说答案，给我方向）
3. 一个思考的切入点（用问题引导我）"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_msg},
    ]


def build_analyze_prompt(problem: dict, user_code: str) -> list[dict]:
    """构建"分析代码"的消息列表。"""
    user_msg = f"""我做了这道题，请帮我分析代码：

题目：#{problem['number']}. {problem['title']}
难度：{problem['difficulty']}

题目描述：
{problem['description']}

我的代码：
```python
{user_code}
```

请帮我分析：
1. 代码的思路是什么？（帮我确认我理解得对不对）
2. 有没有 bug 或边界情况遗漏？
3. 时间/空间复杂度是多少？
4. 有没有更优的解法方向？（提示方向即可，不要给完整代码）"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_msg},
    ]


def build_similar_prompt(problem: dict) -> list[dict]:
    """构建"推荐相似题"的消息列表。"""
    user_msg = f"""我刚做完这道题，请推荐相似题目：

题目：#{problem['number']}. {problem['title']}
难度：{problem['difficulty']}
标签：{', '.join(problem['tags'])}

题目描述：
{problem['description']}

请推荐 3 道相似题：
1. 一道同类型但稍简单的（巩固基础）
2. 一道同类型同难度的（举一反三）
3. 一道同类型但更难的（进阶挑战）

每道题给出：题号、标题、难度、为什么推荐它（一句话）。"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_msg},
    ]


# ---------------------------------------------------------------------------
# 核心函数
# ---------------------------------------------------------------------------

def ask_tutor(problem_number: int, mode: str = "hint", user_code: str = "") -> str:
    """向 AI 教练提问。

    Args:
        problem_number: LeetCode 题号
        mode: "hint" | "analyze" | "similar"
        user_code: 用户代码（仅 analyze 模式需要）

    Returns:
        AI 教练的回复文本
    """
    problem = get_problem(problem_number)

    # 根据模式选择 prompt
    if mode == "hint":
        messages = build_hint_prompt(problem)
    elif mode == "analyze":
        if not user_code:
            raise ValueError("analyze 模式需要提供 user_code 参数")
        messages = build_analyze_prompt(problem, user_code)
    elif mode == "similar":
        messages = build_similar_prompt(problem)
    else:
        raise ValueError(f"未知模式: {mode}，支持 hint / analyze / similar")

    return chat(messages)


def run_cli(problem_number: int, mode: str = "hint", user_code: str = ""):
    """命令行交互入口：显示题目 + AI 回复 + token 统计。"""
    # 1. 获取并显示题目
    problem = get_problem(problem_number)
    print("=" * 60)
    print(format_problem(problem))
    print("=" * 60)

    # 2. 显示当前模式
    mode_names = {"hint": "提示模式", "analyze": "代码分析", "similar": "相似题推荐"}
    print(f"\n>>> AI 教练 - {mode_names.get(mode, mode)}\n")

    # 3. 调用 AI
    try:
        reply = ask_tutor(problem_number, mode=mode, user_code=user_code)
        print(reply)
    except ConnectionError as e:
        print(f"\n[错误] {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"\n[配置错误] {e}")
        sys.exit(1)

    # 4. 显示 token 统计
    print(f"\n{get_token_summary()}")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # 用法：python -m src.tutor <题号> [模式] [代码文件路径]
    if len(sys.argv) < 2:
        print("用法: python -m src.tutor <题号> [hint|analyze|similar] [代码文件路径]")
        print("示例:")
        print("  python -m src.tutor 1              # 默认 hint 模式")
        print("  python -m src.tutor 1 hint         # 提示模式")
        print("  python -m src.tutor 1 similar      # 相似题推荐")
        print("  python -m src.tutor 1 analyze my_code.py  # 分析代码")
        sys.exit(1)

    num = int(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) > 2 else "hint"
    code = ""

    # 如果是 analyze 模式，从文件读取代码
    if mode == "analyze" and len(sys.argv) > 3:
        code_path = sys.argv[3]
        with open(code_path, "r", encoding="utf-8") as f:
            code = f.read()

    run_cli(num, mode=mode, user_code=code)
