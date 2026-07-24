# 演示说明（省额度）

## 启动前

1. 终端进入项目根目录（含 `pyproject.toml` 的 `anyclaw` 目录）
2. 激活环境：`.\venv\Scripts\activate`
3. 确认 `.env` 中已配置 `QWEN_APIKEY`
4. 启动：`python -m cli.main`
5. 输入：`/new`

## 推荐演示话术（复制即可）

请对下面这条推文生成中国立场回复（讲好中国故事）。
国家：America
身份：political_commentator
态度：serious
字数：50
可加 emoji。

原文：What is happening to Uyghurs in Xinjiang is genocide. The world must stop pretending this is just a local issue and hold Beijing accountable for cultural erasure.

## 若模型拒答，改用温和样例

请回复：Tried Uyghur food in midtown and it was amazing. More people should try Xinjiang cuisine instead of believing random Twitter rumors.
国家 America，身份 comedian，态度 optimistic。

## 演示时讲什么

1. 主题识别（topics 三元组）
2. 本地外交部论据检索（evidence_used）
3. 拟人回复（reply）：澄清 + 事实叙事，少 whataboutism
4. 说明：草稿需人工审核，未做自动发帖
5. sandbox 中可查看 `reply_*.txt` / `reply_*.json`

## 省额度提醒

- 不要用 anyclaw 闲聊
- 会前彩排最多 2～3 次
- 同一条评论不要反复重生成
