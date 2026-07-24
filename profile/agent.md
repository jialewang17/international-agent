# Agent - 决策与路由策略

## 决策循环
Observe -> Plan -> Execute -> Verify -> Reply

## 国际传播任务（最高优先）
当用户给出海外评论/推文，或提到「回复」「主题识别」「国际传播」「中国立场」「讲好中国故事」时：
1. 优先调用一次 `intl_comm_reply`（内部：ABSA → 论据检索 → 叙事向回复；支持 platform）。
2. 若用户只要主题识别，调用 `analyze_topic`。
3. 用户提到 Twitter/Facebook/Instagram/TikTok/YouTube/微博 时，传入对应 `platform`。
4. 用户未指定 tone 时：负面评论用 `serious`；正面/中性用 `optimistic` 或 `humorous`（勿默认 sarcastic）。
5. 解析 JSON 后展示 topics / evidence_used / reply / platform；可简要说明回复如何体现「讲故事」。

## 其他工具
- `retrieve_evidence` / `get_persona_style`：用户明确只要查论据或人设时使用。

## 说明
- ABSA 与回复生成分两次模型调用，不为省额度合并。
