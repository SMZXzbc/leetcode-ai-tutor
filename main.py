#!/usr/bin/env python3
"""
LeetCode AI Tutor - 交互式终端主程序
第三阶段：实现交互式刷题体验
"""

import sys
import os
from datetime import datetime

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from leetcode_api import get_problem
from mimo_client import chat, get_token_summary

# 历史记录存储
HISTORY_FILE = os.path.join(os.path.dirname(__file__), 'data', 'history.txt')

def ensure_data_dir():
    """确保数据目录存在"""
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(data_dir, exist_ok=True)

def save_history(problem_id: str, title: str, tokens_used: int):
    """保存刷题记录"""
    ensure_data_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] #{problem_id} {title} - {tokens_used} tokens\n")

def show_history():
    """显示刷题历史"""
    if not os.path.exists(HISTORY_FILE):
        print("\n[历史] 暂无刷题记录")
        return
    
    print("\n" + "=" * 60)
    print("[历史] 刷题记录")
    print("=" * 60)
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        if not lines:
            print("暂无记录")
        else:
            for line in lines[-10:]:  # 显示最近10条
                print(line.strip())
    print("=" * 60)

def format_problem(problem: dict) -> str:
    """格式化题目显示"""
    lines = [
        "\n" + "=" * 60,
        f"#{problem['number']}. {problem['title']}",
        f"难度: {problem['difficulty']} | 标签: {', '.join(problem['tags'])}",
        "=" * 60,
        problem['description'],
        "=" * 60,
    ]
    return "\n".join(lines)

def get_ai_response(problem: dict, user_input: str, mode: str = "normal") -> tuple:
    """
    获取 AI 回复
    返回: (回复内容, token统计字典)
    """
    if mode == "hint":
        system_prompt = """你是 LeetCode 算法教练。用户需要提示，请给出明确的解题方向提示，但不要直接给出完整代码。
重点提示：
1. 应该使用什么数据结构
2. 算法的核心思路
3. 时间/空间复杂度的优化方向"""
    else:
        system_prompt = """你是 LeetCode 算法教练。请遵循以下原则：
1. 不要直接给出答案，用引导式提问帮助用户思考
2. 分析用户的思路，指出正确或需要改进的地方
3. 如果用户代码有bug，提示测试用例而不是直接修复
4. 鼓励用户自己找到解决方案"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"题目：{problem['title']}\n描述：{problem['description'][:500]}\n\n用户的想法/代码：\n{user_input}"}
    ]
    
    # chat() 返回 (内容, token字典)
    response, tokens = chat(messages)
    
    return response, tokens

def main():
    """主程序入口"""
    print("\n" + "=" * 60)
    print("LeetCode AI Tutor")
    print("   输入题号开始刷题（如 1），或输入命令：")
    print("   /history - 查看刷题记录")
    print("   /quit    - 退出程序")
    print("=" * 60)
    
    while True:
        try:
            user_input = input("\n> 请输入题号或命令: ").strip()
            
            if not user_input:
                continue
            
            # 处理命令
            if user_input.lower() in ['/quit', '/q', 'quit', 'exit']:
                print("\n再见！继续加油刷题！")
                break
            
            if user_input.lower() in ['/history', '/h']:
                show_history()
                continue
            
            # 解析题号
            try:
                problem_id = int(user_input)
            except ValueError:
                print("请输入数字题号，或 /history 查看记录")
                continue
            
            # 获取题目
            print(f"\n[加载] 正在获取题目 #{problem_id}...")
            problem = get_problem(problem_id)
            
            if not problem:
                print(f"[错误] 无法获取题目 #{problem_id}，请检查题号是否正确")
                continue
            
            # 显示题目
            print(format_problem(problem))
            
            # 交互式刷题循环
            session_tokens = 0
            
            while True:
                action = input("\n[输入] 输入你的思路/代码，或 /hint 要提示，/next 换题: ").strip()
                
                if not action:
                    continue
                
                if action.lower() in ['/next', '/n']:
                    # 保存本次记录
                    save_history(str(problem_id), problem['title'], session_tokens)
                    print(f"\n[保存] 已保存记录，本次共消耗 {session_tokens} tokens")
                    break
                
                if action.lower() in ['/hint', '/h']:
                    print("\n[提示] 正在获取提示...")
                    response, tokens = get_ai_response(problem, "请给我一些提示", mode="hint")
                    print(f"\n[AI 提示]:\n{response}")
                    session_tokens += tokens['total']
                    print(f"\n[Token] 本次: {tokens['total']}, 累计: {session_tokens}")
                    continue
                
                # 正常对话
                print("\n[思考] AI 正在思考...")
                response, tokens = get_ai_response(problem, action, mode="normal")
                print(f"\n[AI 教练]:\n{response}")
                
                session_tokens += tokens['total']
                
                print(f"\n[Token] 本次: {tokens['total']}, 累计: {session_tokens}")
        
        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"\n[错误] 出错了: {e}")
            import traceback
            traceback.print_exc()
            continue

if __name__ == "__main__":
    main()
