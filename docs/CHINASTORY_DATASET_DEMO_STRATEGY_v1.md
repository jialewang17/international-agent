# ChinaStory Dataset / Demo Strategy v1

本文档定义 ChinaStory 当前四层 Dataset / Demo Strategy，作为后续 Codex 与团队开发的统一基线。

## 1. 苏绣｜Engineering Baseline

苏绣是当前第一优先的 Evidence / Chroma 测试案例，用于快速跑通最小工程闭环：

```text
Source → EvidenceSpan → Claim → Retrieval → Generation → Traceability
```

重点验证：

- 最小工程测试；
- Claim–Evidence baseline；
- Evidence / Chroma 检索与追溯；
- 生成内容与证据的基本关联。

苏绣案例保持最小规模，不扩展为大型 Knowledge Graph。

## 2. 泉州｜Deep Knowledge / Graph Case

泉州用于验证深层知识组织与图检索能力：

- Deep KG；
- Graph Retrieval；
- Multi-source Evidence；
- Historical Fact Traceability。

该案例在苏绣 Evidence baseline 跑通后进入。

## 3. 茶文化｜International Communication Case

茶文化用于验证国际传播中的内容重构：

- Transcreation；
- Genre Adaptation；
- Cultural Distance。

使用同一事实基础，测试不同平台、受众与体裁下的国际传播表达重构。

## 4. Conflict Case｜Safety & Revision Case

Conflict Case 用于构造可控失败案例与人工审核案例，验证：

- Gate B；
- Revision；
- New Claim Detection；
- Fact Drift；
- Fact Lock。

## 执行原则

- 四个案例不是四个平行的大型文化知识库。
- 每个案例承担不同的研究或工程验证任务。
- 不要求每个案例覆盖全部能力。
- 当前执行顺序：

```text
苏绣 baseline
→ 泉州 Deep KG
→ 茶文化 Transcreation
→ Conflict / Fact Lock stress test
```

当前开发仍从苏绣 Evidence baseline 开始。

本文档是 Dataset / Demo Strategy，不替代项目总 SPEC、Evaluation Spec 或 Rubric。
