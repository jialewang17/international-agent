# 周四演示说明（省额度）

## 启动前
1. 终端进入 `D:\大创\anyclaw`
2. 激活环境：`.\venv\Scripts\activate`
3. 启动：`python -m cli.main`
4. 输入：`/new`

## 推荐演示话术（复制即可）

请对下面这条推文生成中国立场回复。
国家：America
身份：political_commentator
态度：sarcastic
字数：50
可加 emoji。

原文：Companies that use Uyghur slave labor in Xinjiang should be boycotted. This is forced labor and a human rights disaster.

## 若模型拒答，改用温和样例

请回复：Tried Uyghur food in midtown and it was amazing. More people should try Xinjiang cuisine instead of believing random Twitter rumors.
国家 America，身份 comedian，态度 humorous。

## 演示时讲什么
1. 主题识别（topics 三元组）
2. 本地外交部论据检索（evidence_used，不耗 API）
3. 拟人回复（reply）
4. 说明：草稿需人工审核，未做自动发帖

## 省额度提醒
- 不要用 anyclaw 闲聊
- 会前彩排最多 2～3 次
- 同一条评论不要反复重生成
