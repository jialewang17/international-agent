# 跨文化表达评审细则（D1 / D2 / D3 / D6；按需辅助 D5）· v5.1

> 本文是 **Part 3 操作参考**，不是独立评价者，也不产生“跨文化总分”。对 Part 1/Part 2 的裁决不越权。[E02][S01–S03]

## 1. 仅根据已提供受众画像做判断

| 条目 | 对应维度 | 可观察依据 | 何时移交 |
|---|---|---|---|
| 文化专有名词 | D1 | 首次出现的位置；是否解释其含义与上下文，且解释不过度 | 术语的历史归属真实性有争议 → Part 1 |
| 文化背景与知识跳跃 | D1 | 是否预设读者理解中国特定制度/习俗 | 对原文翻译是否忠实 → Part 2 |
| 文化主体性与语境 | D2 | 是否尊重群体/传承人，避免物化、异国情调化或单一叙述 | 对社区“真实回应/授权”的证据问题 → Part 1/人工 |
| 文化类比 | D2 | 是否把不同传统直接“等同”，忽略界限与差异 | 某项文化起源、专有名称不实 → Part 1 |
| 受众适配 | D3 | 是否符合 `prior_knowledge`、`desired_depth`、传播目标 | 受众画像未提供 → `INSUFFICIENT_CONTEXT` |
| 文风与语气 | D6 | 是否自然、清晰，不以刻板印象羞辱或对抗受众 | 新增未支持的事实句 → Part 1 |
| 内容形式 | D5 | 文字信息密度、平台可读性（按 Genre 卡） | 真实图像/视频未提供 → 标记素材限制 |

### 特别澄清 [E02]

- `translation_fidelity`（翻译忠实度、错译/漏译）由 **Part 2** 检测；本 Skill 仍可以报告目标语是否自然、文化解释是否有效，但不据此宣布译文“与母稿完全等值”。
- “是否添加原文没有的事实”由 **Part 1** 追溯证据裁决；本 Skill 发现疑点只设置 `return_to_part1=true`。
- `confidence` 不用于证明文化解释的真伪或作者意图。

## 2. D2 的伦理与文化主体性 [E09]

重点观察**具体文本行为**而不是政治立场或国别印象：

1. 是否允许文化实践者以自己的声音或经证实的行动出现，而不是虚构“传承人一致认为……”的群体代言。
2. 是否因追求异国情调而把传统描绘成停止发展的“古老奇观”。
3. 是否保留必要的地区/社区/时代差异和文化术语，不把复杂概念粗暴等同为一个外国概念。
4. 不以“西方人都喜欢/无法理解”作为受众推断依据；只使用明确的 Audience Profile。
5. 对 UNESCO 相关的**社区知情同意、肖像授权和原始事实**风险，仅提示回到 Ground/Part 1/人工，而不自称已检查授权文件。

**依据**：[S09] UNESCO 非遗伦理原则明确强调社区主体性、相互尊重、防止去语境化和误表述；这些原则可用于解释 D2 中的可观察质量问题，但不提供额外积分或自动宣告文化真实性。

## 3. 操作流程

1. 在 `content.text` 定位真实措辞；避免“整体感觉怪”这类不可复核评价。
2. 把问题映射到**最合适的一个主要维度**，必要时说明次要影响，不因同一片段重复机械扣分。
3. 给最小必要的修改方向，如解释术语、调整语序、补充来自 EvidencePack 的已有背景，**不要求新造事实**。
4. 保留 D1–D6 独立评分，不另发 `cross_cultural_score`。
5. 真实受众理解与信任必须另行实验，不能以模型自评代替。

## 4. 可核查来源

- [S01] [Rubric v2.1](https://github.com/jialewang17/international-agent/blob/main/eval/CHINASTORY_CONTENT_QUALITY_RUBRIC_v2.1.md)：D1/D2/D3/D6 及事实门控原则。
- [S02] [Evaluation Pipeline v1.2](https://github.com/jialewang17/international-agent/blob/main/eval/CHINASTORY_EVALUATION_PIPELINE_SPEC_v1.2_CN.md)：Part 1 / Part 2 / Part 3 分离。
- [S09] [UNESCO Ethics and Intangible Cultural Heritage](https://ich.unesco.org/en/ethics-and-ich-00866)。
