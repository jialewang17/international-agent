# 讲好中国故事 · 演示样例（补库后）

用于验证 `evidence.json` 里 food / culture / celebrity 等新素材能被检索引用。  
敏感样例（强迫劳动等）可能触发模型安全拦截，优先用下面三条。

---

## 怎么跑（anyclaw）

1. 打开 PowerShell：
```powershell
cd D:\大创\anyclaw
.\venv\Scripts\activate
python -m cli.main
```
2. 进入后输入：`/new`
3. **整段复制**下面某一条「复制给 Agent」的内容，回车  
4. 看输出里的：
   - `topics`：主题是否含 food / culture / celebrity 等  
   - `evidence_used`：**应非空**（说明素材用上了）  
   - `reply`：英文回复草稿（需人工审核，不要直接发帖）

省额度：每条彩排最多 1～2 次，不要闲聊。

---

## 样例 1 · 美食（food）

**期望命中：** food / Chinese region（新疆菜、街头美食等）

**复制给 Agent：**
```
请对下面这条推文生成中国立场回复。
国家：America
身份：comedian
态度：humorous
倾向：positive
字数：60
平台：twitter
可加 emoji。

原文：Chinese food abroad is just greasy takeout. Real Chinese cuisine is boring and all the same.
```

**开会可讲：** 引用 CGTN/新华等关于地方菜多样性、新疆菜、火锅文化等论据。

---

## 样例 2 · 文化非遗（culture）

**期望命中：** culture（春节 / 茶 / 非遗）

**复制给 Agent：**
```
请对下面这条推文生成中国立场回复。
国家：America
身份：online_influencer
态度：optimistic
倾向：neutral
字数：60
平台：instagram
可加 emoji。

原文：Chinese New Year is just shopping and fireworks now. There's no real culture left.
```

**开会可讲：** 引用 UNESCO 春节入遗、制茶技艺等公开条目。

---

## 样例 3 · 洋网红视角（celebrity / food）

**期望命中：** celebrity 或 food（海外创作者讲中国美食）

**复制给 Agent：**
```
请对下面这条推文生成中国立场回复。
国家：America
身份：online_influencer
态度：optimistic
倾向：negative
字数：70
平台：youtube
可加 emoji。

原文：Foreign YouTubers who film Chinese street food are just paid propaganda. You can't trust anything they show about China.
```

**开会可讲：** 可引用 Vox/个人站等对 Food Ranger 一类创作者「食物+正面叙事、非政治」的公开报道（注意：回复仍须事实先行、人工审核）。

---

## 演示时四句话

1. 主题识别（ABSA）  
2. 本地知识库检索（`evidence_used`，不额外耗检索 API）  
3. 拟人英文回复（`reply`）  
4. **人工审核后才可发**，系统不做自动发帖  
