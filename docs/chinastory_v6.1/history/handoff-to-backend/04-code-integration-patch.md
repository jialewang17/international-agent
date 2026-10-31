# 代码接线补丁（最小修改集）

> 本文件不是自动应用的 Python 补丁。先在分支中修改并运行回归测试。
> 状态栏依据：2026-10-17 对 https://github.com/jialewang17/international-agent 当前 `main` 分支源码的实际核查。

## 总览：哪些已经修好了，哪些还没

| 检查点 | ZIP 中的记录（`verification-results.md`） | GitHub 当前代码核查 | 判断 |
|---|---|---|---|
| `feature` 格式归一化 | 被错误转换成 `news_article` | `_FORMAT_TO_GENRE` 已是 `longform → feature` | ✅ **已经修复** |
| 知识文件缺失 | 可能仍返回 `ready_to_generate` | 当前代码检查缺失文件，返回 `gate=blocked` | ✅ **已经修复** |
| 深度报道路由 | 应新增 `indepth` | `_GENRE_PATTERNS` 中 `feature` 排第一且含 `深度报道`、`\bin[- ]?depth\b`；无 `indepth` 条目 | 🔴 **仍需修复** |
| Skill 文件注册路径 | 需要兼容新子目录 | `config/skills.yaml` 仍引用旧扁平文件路径 | 🔴 **仍需修改** |
| 两个顶层 Skill | ZIP 希望整合为最终方案 | 仍按 `china_story_post`、`china_story_news` 等多个 Skill ID 注册 | 🔴 **仍需整合** |
| 六类体裁专用生成 | 新版 Skill 已分别定义输出协议 | 生成器主要区分 News 与非 News，未分别处理全部六类结构 | 🔴 **仍需开发** |

> **重要**：ZIP 中的部分工程检查结论已经落后于 GitHub 当前代码。不要照着旧补丁全量修改，先跑一遍下面的验证命令确认现状。

---

## 1. `tools/genre_router.py`

### 1.1 路由表：把 `indepth` 提到 `feature` 之前，并从 feature 删除抢匹配的词

当前代码（问题所在）：

```python
_GENRE_PATTERNS = [
    ("feature", [
        r"深度报道",          # ← 会抢走深度报道
        r"专题稿", r"特稿", r"长篇深度",
        r"\bfeature\b", r"\blongform\b",
        r"\bin[- ]?depth\b",  # ← 会抢走 in-depth
    ]),
    ("news", [...]),
    ("script", [...]),
    ("faq", [...]),
    ("post", [...]),
]
```

改为：

```python
_GENRE_PATTERNS = [
    ("indepth", [
        r"深度报道", r"解释性报道", r"调查报道", r"专题报道",
        r"in[- ]?depth(?:\s+report|\s+story)?",
        r"explainer\s+(?:report|longform|story)",
    ]),
    ("feature", [
        r"特稿", r"非虚构长文", r"长篇特写", r"\bfeature\b", r"\blongform\b",
    ]),
    # news / script / faq / post 原有表保持不变，整体顺序仍为
    # indepth → feature → news → script → faq → post
]
```

### 1.2 映射表与状态表

```python
_FORMAT_TO_GENRE.update({
    "longform": "feature",
    "in_depth_report": "indepth",
    "indepth": "indepth",
})

_GENRE_STATUS["indepth"] = "methods_in"
_GENRE_SKILL_REL["indepth"] = "skills/genres/indepth/china-story-indepth.md"
_DEFAULT_FORMAT["indepth"] = "in_depth_report"
```

> 注意：当前 `_FORMAT_TO_GENRE` 中 `longform → feature` **已正确**，不要重复添加；关键是新增 `in_depth_report` / `indepth`，并让 `indepth` 在路由顺序上先于 `feature`。

---

## 2. `tools/load_story_knowledge.py`

### 2.1 格式集合与别名

```python
TIER2 = {
    # 原有 Tier-2...
    "longform", "in_depth_report",
}
ALL_FORMATS = TIER1 | TIER2

_MEETHOD_HINTS_FIXED = True   # 见下
_MEETHOD_HINTS_PLACEHOLDER = None
```

实际写法（把上面两行占位替换掉）：

```python
_METHOD_HINTS["in_depth_report"] = [
    "Agent调用总流程", "Agent禁止清单", "背景", "模块A", "模块B", "模块F"
]

aliases["feature"] = "longform"
aliases["indepth"] = "in_depth_report"
aliases["deep_dive_report"] = "in_depth_report"
```

### 2.2 缺失知识库硬失败（**当前代码已修复，此节为回归保护**）

确认现有实现满足：在构造 payload 前检查三个文件内容是否为空，任一为空即返回：

```python
{
    "ok": False,
    "gate": "blocked",
    "error": "知识库缺失：" + ", ".join(missing),
    "knowledge_paths": {
        "framework": "knowledge/storytelling_framework.txt",
        "methodology": "knowledge/writing_methodology.txt",
        "formats": "knowledge/content_formats.md",
    },
}
```

> **要求**：该检查必须覆盖**空文件**和**路径错配**，不能只检查 `Path.exists()`。
> 来源：`code-integration-patch.md` §2.2 + `implementation-checklist.md` P0 第 1 条。

---

## 3. `config/skills.yaml`

> **警告：只改 YAML 不够。** 现有生成器仍使用 `skill_ids_for_genre()` 返回的旧 Skill ID；注册器、路由器、生成工具必须一起调整。
> 来源：审查报告 §七.1。

目标：把顶层注册收敛为两个能力。

```yaml
manual_activation:
  always_on:
    - intl_comm
    - evidence_user_materials

max_active_skills: 4
max_total_chars: 20000

skills:
  china_story_generation:
    file: skills/china-story-generation/SKILL.md
    title: 中国故事内容生成（Create / Revision）
    enabled: true
    priority: 80

  china_story_evaluation:
    file: skills/china-story-evaluation/SKILL.md
    title: 中国故事内容质量评测（Part 3）
    enabled: true
    priority: 80
```

过渡期保留原 `china_story_post` / `china_story_news` / `china_story_feature` / `china_story_script` 等条目时，须同步更新其 `file` 指向新子目录，避免路径失效：

```yaml
  genre_feature:
    file: skills/genres/feature/china-story-feature.md
  genre_indepth:
    file: skills/genres/indepth/china-story-indepth.md
```

> 若 `skill_registry.py` 已把体裁卡额外注入 prompt，就不要再把 `genre_*` 作为完整技能再注入一次。**二选一**，防止重复占用上下文预算（来源：`code-integration-patch.md` §3 末）。

---

## 4. `tools/story_post_gen.py`

当前显式体裁允许集合为 `post` / `news` / `feature` / `script`；`faq` 与 `indepth` 尚未完整接入，非 News 分支主要复用同一帖文 Prompt。

目标结构：

```text
通用内容生成器 + 专业体裁参考 + 独立输出 Schema
```

改动要点：

1. 允许集合扩展为 `post|news|feature|indepth|script|faq`。
2. 按 genre 载入对应输出 Schema，而不是统一帖文结构。
3. 不再给 Post Prompt 继续累加特殊规则。

---

## 5. 验证命令（先跑这些，确认现状）

```powershell
python -c "from tools.genre_router import detect_genre; print(detect_genre('写一篇深度报道'))"
python -c "from tools.genre_router import detect_genre; print(detect_genre('写一篇特稿'))"
python -m pytest -q
```

### 最小断言

```python
assert detect_genre("写一篇深度报道")["genre"] == "indepth"
assert detect_genre("写一篇特稿")["genre"] == "feature"
assert _normalize_format("feature")[0] == "longform"
assert _normalize_format("in_depth_report")[0] == "in_depth_report"
```

### 缺失知识库测试

临时将某个文件内容置空 / 移出测试夹具，断言 `gate == "blocked"`。
**不要在真实工作树上删除文件。**
