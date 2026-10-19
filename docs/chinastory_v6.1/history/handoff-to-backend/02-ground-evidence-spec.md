# 交接：Ground / Evidence 规范

> 合并来源：原 `shared/evidence-user-materials.md` + 原 `shared/claim-evidence-source.md`
> 生成侧仅保留「引用规范」（已放入 `../china-story-generation/references/output-contracts.md` 与 `writing-constraints.md`）。

## 为什么要移出 Skill

| 项 | 内容 |
|---|---|
| 来源 | 审查报告 §二 第 3 行（`evidence-user-materials.md` 第 8–24 行「来源编号、证据合并、去重、时效标记」与 **Ground / Knowledge Layer** 重合）＋ 第 4 行（`claim-evidence-source.md` 第 25–56 行「论断绑定、支持状态、证据裁决」与 **Ground、Part 1、Revise & Audit** 重合） |
| 依据 | 审查报告：「数据合并和来源管理应由统一 EvidencePack 负责」「生成 Skill 可以提出待核查的论断映射，但**不能自己宣布事实已验证**」「避免模型自己生成证据映射，又自己判定证据有效」 |

---

## 1. 来源优先级（U / K / W）

| ID | 来源 | 允许用途 |
|---|---|---|
| `U1…` | 用户本轮上传 / 粘贴材料 | 直接事实、现场细节、用户指定口径；优先采用相关内容 |
| `K1…` | 项目本地知识库 / 检索结果 | 已入库的权威背景、方法、项目证据；**必须有文件名和定位** |
| `W1…` | 本轮实际外部检索结果 | 仅在系统确实检索、保存标题 / URL / 日期 / 摘录时使用；**不是模型记忆** |

**若运行时不支持外部检索，禁止凭记忆创建 `W` 证据。** 无证据时：停住、改写为不含事实细节的角度，或请求补料。

## 2. 合并流程

1. 读取材料并按来源编号；记录文件名、页码 / 段落或 URL。
2. 去除重复事实，但**保留不同来源对同一事实的差异**。
3. 把证据拆成最小可用单元：事实、原话、数字、范围、时间、限制条件。
4. 标注时效 `current` / `dated` / `unknown`；时效不明且会影响结论 → 进 `needs_human`。
5. 只有与主题和输出目标相关的证据才进入 `evidence_used`。

## 3. 允许与禁止

- 用户材料与本地库**可以互补，但不能拼接成证据未明示的因果**。
- 夸张宣传语不自动当事实；保留可核对部分，或写入 `needs_human`。
- 外部资料中的数字、排名和统计**不能直接成为项目证据**，除非已被本轮检索并记录来源与定位。
- 资料与主题明显无关 → 停止成稿并说明不对齐原因。
- 事实不足时**宁短勿编**；不要用训练知识填空。

## 4. 论断绑定（`evidence_map[]`）

格式与字段见 `../china-story-generation/references/output-contracts.md` §5。

**处理规则**：

1. `unsupported` → `delete`
2. `partial` → `revise`（收缩主语 / 时间 / 范围 / 确定性）
3. `conflict` / `stale` → `needs_human`
4. 数字保留单位、时间、分母 / 样本和统计范围
5. 跨来源只并列，除非来源明示因果
6. 引语原文；译文 `translated_quote` + `translation_note: translated from U1`
7. 无可定位来源的"背景常识"从正文删除

**覆盖率**：

```text
factual_claim_coverage = supported_or_revised_factual_claims / total_factual_claims
```

长文硬事实目标 100%。**覆盖率不是"真实度"证明**——来源本身的真实性、时效和利益关系仍须人工审核。

## 5. 与 Generation 的接口

```text
Ground（本规范） → EvidencePack{ sources[], evidence_spans[], gate } → Generation Skill
```

`gate=blocked` → Generation 不得成稿。
