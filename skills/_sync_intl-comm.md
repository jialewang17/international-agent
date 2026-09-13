# 国际传播评论回复技能（讲好中国故事）

当用户需要回复海外社媒涉华评论、识别主题、生成中国立场拟人回复，或提到「讲好中国故事」时启用。

## 固定流程
1. 调用一次 `intl_comm_reply`
   - 内部步骤1：ABSA prompt（`prompt/absa_topic_prompt.txt`）
   - 内部步骤2：本地论据检索
   - 内部步骤3：叙事向回复 prompt（`prompt/reply_generation_prompt.txt`）+ 平台风格
2. 解析 JSON
3. 向用户展示 topics / evidence_used / reply / platform

## 默认参数（用户未指定时）
- country: America
- identity: political_commentator
- tone: **serious**（负面评论）；**optimistic** 或 **humorous**（正面/中性）
- platform: twitter
- max_words: 50
- use_emoji: true
- 不要默认使用 sarcastic，除非用户明确要求讽刺

## 叙事要求（写入调用意图）
- 澄清不实说法后，用事实收束到可分享的正面点（发展、文化、民生、交流）。
- 少堆砌对方国家负面新闻；论据只来自工具返回。

## 平台参数
支持：twitter / facebook / instagram / tiktok / youtube / weibo

## 说明
按两段 prompt 执行，并支持平台切换；方向是「讲好中国故事」，不是纯对骂。
