# LeetCode AI Tutor

AI 辅助的 LeetCode 刷题工具，基于小米 MiMo API。

## 功能

- 抓取 LeetCode 题目信息
- AI 引导式提示（不给答案，只给思路）
- 刷题历史记录
- Token 消耗统计

## 使用方法

1. 配置 `.env` 文件（填入 MiMo API Key）
2. 运行 `python main.py`
3. 输入题号开始刷题
4. 输入 `/hint` 获取更多提示
5. 输入 `/history` 查看记录

## 技术栈

- Python
- MiMo API (OpenAI 兼容)
- LeetCode GraphQL API

## 作者

北邮 AI 院大一学生