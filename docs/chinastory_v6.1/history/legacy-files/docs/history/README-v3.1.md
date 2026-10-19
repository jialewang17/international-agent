# ChinaStory-final-skills-v3.1｜Post & News 专项修订包

> 更新日期：2026-10-18。**本次实际修改范围：Generation Skill 内部 Post 与 News 两张体裁参考卡。**

## 升级概览

- `china-story-generation/references/genres/post.md`：升级至 Post v3.1；新增证据条件下的叙事模式、受众/身份规则、动态平台配置、真实图像 Alt Text、利益关系披露与自检。
- `china-story-generation/references/genres/news.md`：升级至 News v3.1；区分独立报道与机构新闻稿、倒金字塔导语、新闻源归属、匿名来源、引语翻译、AI 编辑责任与自检。
- `china-story-generation/docs/Post_News_v3.1_Changes_and_Sources.md`：24 项修改记录，含 v2.1 原位置、每项修改理由、资料来源和测试映射。
- `china-story-generation/docs/Post_News_v3.1_Tests.md`：24 条验收测试用例（**并非已运行的模型评估结果**）。
- `china-story-generation/agents/openai.yaml`：为标准 Skill 包补充 UI 元数据；**不改变 ChinaStory 自有 Agent 的运行方式**。

**未更改**：Generation 主 `SKILL.md`，其余 Feature/Indepth/Script/FAQ 方法、Transcreation、Writing Constraints、Output Contracts、Evaluation Skill 全部文件、后端交接文档。此处“整个包 v3.1”指交付包版本，**不表示所有体裁或 Evaluation 都已经升级到 v3.1**。

## 架构职责说明

1. `Define / Ground / Plan` 提供 TaskContext、EvidencePack、ContentPlan。
2. Generation 使用当前 Post 或 News v3.1 方法生产母稿与目标语草稿，不自行接管事实核验。
3. Evaluation Part 1 负责事实和来源验证，Evaluation Skill 负责 Part 3 D1–D6 内容质量评分。
4. 修改进入 Revision 和 Part 1 必要复核，Gate C 由人工批准。

## 安装/应用方式

在项目代码中，按照原路径替换 Generation 的 `references/genres/post.md` 和 `news.md`；其它文件不要直接覆盖线上实际新于本压缩包的代码。对于正式 AI Agent 运行，确认 Registry 仍指向对应 `SKILL.md` 并可按需读取体裁卡。

**注意**：Instagram 标签限制本次使用的是行业媒体二手报道转引 Instagram 声明；X 与 LinkedIn 的限制应在发布时检查官方文档与 API。纸面规则升级不等于已经通过真实模型端到端验收。
