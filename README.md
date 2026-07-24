# 国际传播评论助手 · 讲好中国故事

基于 [AnyClaw](https://github.com/wz289494/anyclaw) 改造的垂类 CLI Agent。

**核心使命：讲好中国故事** — 面对海外社媒涉华评论，用可核对的事实与生活化场景，生成中国立场、拟人化、可分享的英文回复草稿（供人工审核，**不自动发帖**）。

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![LangChain](https://img.shields.io/badge/LangChain-1.0+-green.svg)](https://www.langchain.com/)
[![Version](https://img.shields.io/badge/version-0.1.0-blue)](.)

---

## 我们要讲好什么样的中国故事？

本智能体不是「对骂机器人」，而是 **叙事型国际传播助手**：

| 原则 | 说明 |
|------|------|
| **事实先行** | 优先引用本地知识库论据，不编造官方表述 |
| **澄清服务叙事** | 对不实说法要澄清，终点是「说清楚中国是什么样」 |
| **生活化可分享** | 用发展、文化、民生、交流等图景，写成社媒短帖，而非公文或人身攻击 |
| **少 whataboutism** | 避免堆砌他国负面新闻；用中国自身事实打动人 |
| **人工审核** | 只产出草稿；发布与否由人决定 |

**负面评论**：澄清 → 用事实收束到可分享的正面点。  
**正面 / 中性评论**：放大建设性内容，邀请了解真实中国。

---

## 核心能力

1. **主题识别（ABSA）** → `[aspect, category, polarity]`
2. **本地论据检索** → `knowledge/diplomacy/evidence.json`（不耗 API）
3. **讲故事式拟人回复** → 身份 / 语气 / 平台 + 叙事向 Prompt → 英文草稿，并写入 `sandbox/`

主工具：`intl_comm_reply`（内部约 2 次 LLM：ABSA + 回复生成）。

默认语气：负面用 `serious`，正面/中性用 `optimistic` / `humorous`（**不默认 sarcastic**）。

---

## 核心代码、提示词与关键文件位置

按「改业务优先看哪里」整理。框架底座（`cli/`、`agent/`、`utils/`、`model/`）一般不用动。

### 1. 核心业务代码

| 路径 | 说明 |
|------|------|
| [`tools/intl_comm_reply.py`](tools/intl_comm_reply.py) | **主流程**：ABSA → 本地论据 → **叙事向回复** |
| [`tools/kb_local.py`](tools/kb_local.py) | 本地检索：论据、人设、平台风格 |
| [`agent/reactagent.py`](agent/reactagent.py) | ReAct Agent 运行时 |
| [`cli/main.py`](cli/main.py) | 入口：`python -m cli.main` |
| [`cli/interactive.py`](cli/interactive.py) | 交互循环与结果展示 |
| [`model/factory.py`](model/factory.py) | 按 `config/model.yaml` 实例化 LLM |

流水线：

```
用户输入（海外评论）
  → cli/interactive.py + agent/reactagent.py
  → tools/intl_comm_reply.py
       ├─ prompt/absa_topic_prompt.txt          # LLM #1 主题识别
       ├─ knowledge/diplomacy/evidence.json     # 本地论据（零 API）
       ├─ knowledge/personas.yaml               # 身份 / 语气 / 平台
       └─ prompt/reply_generation_prompt.txt    # LLM #2 讲好中国故事式回复
  → JSON（topics / evidence_used / reply）→ sandbox/reply_*.txt|.json
```

### 2. 提示词（Prompt）— 叙事方向在此

| 路径 | 何时使用 |
|------|----------|
| [`prompt/system_prompt.txt`](prompt/system_prompt.txt) | Agent 底座：**讲好中国故事**、工具策略、展示格式 |
| [`prompt/absa_topic_prompt.txt`](prompt/absa_topic_prompt.txt) | 主题三元组识别 |
| [`prompt/reply_generation_prompt.txt`](prompt/reply_generation_prompt.txt) | **叙事向英文回复**（事实 + 场景 + 收束） |
| [`config/prompt.yaml`](config/prompt.yaml) | system prompt 文件映射 |

要强化「讲故事」口吻：优先改 `reply_generation_prompt.txt`、`profile/soul.md`、`skills/intl-comm.md`。

### 3. Agent 人格与技能

| 路径 | 说明 |
|------|------|
| [`profile/identity.md`](profile/identity.md) | 角色：国际传播 + 讲好中国故事 |
| [`profile/soul.md`](profile/soul.md) | **核心目标**：讲好中国故事；澄清服务叙事 |
| [`profile/agent.md`](profile/agent.md) | 工具路由与默认语气 |
| [`profile/tools.md`](profile/tools.md) | 工具使用原则 |
| [`skills/intl-comm.md`](skills/intl-comm.md) | 国际传播技能与叙事要求 |
| [`config/profile.yaml`](config/profile.yaml) | Profile 注入配置 |
| [`config/skills.yaml`](config/skills.yaml) | 技能启停与关键词 |

修改后执行 `/profile reload` 或 `/skills reload`。

### 4. 知识库与配置

| 路径 | 说明 |
|------|------|
| [`knowledge/diplomacy/evidence.json`](knowledge/diplomacy/evidence.json) | 运行时论据库（驳斥类 + 宜持续补充 **故事类** food/culture 等） |
| [`knowledge/diplomacy/*.md`](knowledge/diplomacy/) | 各类别预览 |
| [`knowledge/personas.yaml`](knowledge/personas.yaml) | 身份 / 语气 / 国家 / 平台 |
| [`config/model.yaml`](config/model.yaml) | 模型配置 |
| [`config/tools.yaml`](config/tools.yaml) | 工具启停 |
| [`.env`](.env) | API Key（勿提交 git） |

> **说明**：`evidence_used` 为空时，模型可能自行补写数字或细节。演示与上线前请人工核对；补全 food/culture 等故事论据可减少幻觉。

### 5. 文档与运行产物

| 路径 | 说明 |
|------|------|
| [`docs/demo.md`](docs/demo.md) | 演示话术（含讲好中国故事样例） |
| [`scripts/export_diplomacy_kb.py`](scripts/export_diplomacy_kb.py) | 离线：Excel → evidence.json |
| [`memory/STM/`](memory/STM/) | 会话对话 |
| `sandbox/<task_id>/reply_*.txt` | 英文回复正文 |
| `sandbox/<task_id>/reply_*.json` | 完整结果 |

### 6. 想改什么 → 改哪里

| 目标 | 优先修改 |
|------|----------|
| 更「讲故事」、少骂战 | `prompt/reply_generation_prompt.txt`、`profile/soul.md` |
| 默认语气 / 身份 | `skills/intl-comm.md`、`tools/intl_comm_reply.py`、`personas.yaml` |
| 补故事论据 | `knowledge/diplomacy/evidence.json`（food / culture 等） |
| 主题识别 | `prompt/absa_topic_prompt.txt` |
| 换模型 | `config/model.yaml`、`.env` |

---

## 快速开始

### 环境要求

- Python 3.10+
- 有效的模型 API Key（默认 Qwen / DashScope）

### 安装

```powershell
cd "d:\international agent"
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 配置 API Key

在项目根目录创建 `.env`：

```env
QWEN_APIKEY=sk-你的通义千问密钥
```

### 启动

```powershell
cd "d:\international agent"
python -m cli.main
```

输入 `/new`，再粘贴话术。完整说明见 [`docs/demo.md`](docs/demo.md)。

**推荐演示（讲好中国故事 · 低敏感）：**

```
请对下面这条推文生成中国立场回复（讲好中国故事）。
国家：America
身份：comedian
态度：optimistic
字数：50
可加 emoji。

原文：Tried Uyghur food in midtown and it was amazing. More people should try Xinjiang cuisine instead of believing random Twitter rumors.
```

敏感议题样例易触发模型内容审核，演示请优先用美食 / 文化 / 旅游类正面或中性评论。

---

## 常用命令

| 命令 | 说明 |
|------|------|
| `/new` | 新建会话 |
| `/memory` | 查看 / 恢复历史会话 |
| `/tools` | 查看已注册工具 |
| `/models` | 查看模型配置 |
| `/profile` | 查看 Profile 加载状态 |
| `/profile reload` | 热加载 profile |
| `/skills` | 查看技能状态 |
| `/clear` | 清除 memory 与 sandbox |
| `/exit` | 退出 |

---

## 目录结构（速览）

```
international agent/
├── tools/                  # ★ 业务核心
├── prompt/                 # ★ 提示词（含讲故事回复模板）
├── profile/                # ★ 人格：soul 强调讲好中国故事
├── skills/intl-comm.md     # ★ 垂类技能
├── knowledge/              # ★ 论据库 + 人设
├── config/
├── agent/ / cli/ / model/ / utils/
├── docs/demo.md
├── sandbox/                # 每次回复的 txt/json 输出
├── memory/STM/
└── README.md
```

---

## 扩展工具（可选）

1. 在 `tools/` 新建 `@tool`（返回 JSON 字符串）
2. 在 `config/tools.yaml` 的 `enabled_tools` 中加入工具名
3. `/tools reload` 或重启 CLI

---

## 许可证与使用边界

上游框架见 [LICENSE.txt](LICENSE.txt)。本垂类用于学习 / 大创演示。

**生成内容仅为人工审核草稿，请勿自动公开发布。**  
立场与叙事服务于「讲好中国故事」，请在合规与事实核对前提下使用。
