# 交接：Plan 阶段规范（原 `entry/china-story-active.md`）

## 为什么要移出 Skill

| 项 | 内容 |
|---|---|
| 来源 | 审查报告 §二「本地文件与位置」第 2 行：`entry/china-story-active.md` 第 8–27 行「选题、受众定位、传播渠道、内容规划」与 **Plan 阶段** 重合；§五 表第 3 行：「主要移至 Plan 规范，部分作为 Generation 参考」 |
| 依据 | v2.1 架构 ③ PLAN 的子模块为 `Audience Profile`、`Cultural Context / Cultural Distance`、`Narrative Strategy`、`Genre Strategy`、`Platform Strategy`，产出 `Content / Narrative Plan`。**选题策划和内容策略已经属于 Plan，不属于 Generation Skill。** |

**保留在 Generation 侧的部分**：仅保留"各体裁擅长什么、能产出什么形态"的能力说明（见 `../china-story-generation/SKILL.md` §2.1 体裁表）。

---

## 原卡内容（移交给 Plan 实现方）

### 工作流

1. 明确主题、传播目标、受众、渠道、时效和可用材料。
2. 只提出**有材料支撑**的选题角度；把事实缺口列为研究问题，**不把缺口写成结论**。
3. 为每个角度标记最合适体裁：`post` / `news` / `feature` / `indepth` / `script` / `faq`。
4. 先给一个**最小可行内容包**，再建议可扩展形态；不要为了"全平台"重复同一段文案。
5. 若需要成稿，交给 Generation Skill 的知识库门禁和体裁工序。

### 规划输出

```yaml
content_plan:
  story_angles: []
  audience_bridge: ""
  primary_format: ""
  repurpose_formats: []
  evidence_ready: []
  research_gaps: []
  risks: []
```

### 边界

- 不承诺传播效果、互动率或"爆款"；
- 不把未经验证的热点、排名和受众偏好写成事实；
- 不自动发布。

---

## 接线要求

- Generation Skill 的输入契约中 `content_plan` 来自本规范；
- 若 `content_plan` 缺失（Skill 被独立调用），Generation 必须输出 `missing_context`，**不得自行生成计划**（来源：审查报告 §二 第 1 行；依据：Define/Plan 属工作流职责）。
