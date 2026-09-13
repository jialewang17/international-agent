# 主动传播演示样例（立项主线：讲好中国故事帖文生成）

## 怎么跑

```powershell
cd D:\大创\anyclaw
.\venv\Scripts\activate
python -m cli.main
```

1. `/new`
2. 粘贴下面某一条整段提示词

看输出：`five_w` / `evidence_used` / `post` / `hashtags` / `ops_tips`

---

## 样例 A · 美食主动帖（Instagram）

```
请生成一条讲好中国故事的海外社交帖文（主动发布，不是回复评论）。
主题：新疆美食的多样与烟火气（大盘鸡、拉面、馕）
目标国家：America
身份：online_influencer
态度：optimistic
平台：instagram
语言：English
字数：80
可加 emoji。
请给出 5W 策划、正文、标签和简短运营建议。
```

---

## 样例 B · 春节非遗（X/Twitter）

```
请生成一条讲好中国故事的主动帖文。
主题：春节作为联合国教科文组织人类非物质文化遗产的当代生活意义
目标国家：America
身份：online_influencer
态度：optimistic
平台：twitter
语言：English
字数：70
可加 emoji。
需要标题钩子、正文、hashtags 和运营建议。
```

---

## 样例 C · 先选题再成稿

```
我想做讲好中国故事的 Instagram 账号运营。先给我 5 个可选选题，然后挑「春节非遗」生成一条英文帖文草稿。
```

---

## 说明

- 这是**主动议题设置**，不是评论区吵架回复。
- 帖文为人工审核草稿，系统不自动发帖。
