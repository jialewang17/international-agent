# 讲好中国故事 · 短视频脚本体裁 Skill（script）· 待完善

**状态**：`genre_status: incomplete` —— **尚未**完成「短视频/讲好中国故事」专项研究报告入库。  
**适用识别**：用户要「短视频脚本 / 口播 / 分镜 / tiktok script / short_video」时路由到本 skill。  
**禁止**：用南方周末长文或 Instagram 种草文案冒充分镜脚本。

## 权威依据

1. **老师 2026-08-22**：产出可含短视频脚本；须有**单独研究框架**，可从讲好中国故事相关研究中提炼；**未完成研究前不要冒充完整规范**。  
2. **共通**：`intl-comm.md` + `evidence-user-materials.md`。  
3. **zip 临时字段壳**：`content_formats.md` · `short_video` / `reel_hook`（见 `knowledge/format_examples.md` 分镜示例）——**仅作分镜字段与防编造时点规则**，不作「爆款方法论」权威。

---

## 临时行为（研究报告到位前）

1. 输出须含：`genre: script`；`genre_status: incomplete`。  
2. 开场可一句说明：「短视频脚本体裁仍在完善；本稿按分镜字段起草，非正式研究报告定稿规范。」  
3. **默认时长**：45–60 秒（用户另有指定则尊重）。前 3 秒钩子要具体。  
4. **分镜字段（合并 zip）**：

| 字段 | 含义 |
|------|------|
| `t` | 时间段（如 0-3） |
| `shot` | 镜头（景别/主体） |
| `vo` | 口播 / VO |
| `on_screen` | 屏幕字 |
| `broll` | 空镜建议 |
| `sfx` | 音效（可选） |

整稿字段：`title`；`duration_sec`；`shots[]`；`caption`（成片文案）；`hashtags`（可选）；`evidence_used`。

5. **防编造时点（强制）**：用户未提供精确钟点/秒数时，**禁止**写「7:42」「Thirty seconds」等假精确；改用 morning rush / a short exchange / peak hours 等模糊时段。  
6. 口播中的事实/数字/专名必须能在 `evidence_used` 找到；找不到则删该句，改写为可核验角度或标注缺材料。  
7. 用户只要「前三秒钩子 / reel_hook」时：输出 3 条前 3 秒方案备选，不硬写完整成片。

## 明确不做

- 不把脚本写成 5W 帖文或通稿电头长文。  
- 不虚构未提供的拍摄地点精确地址、未证实的同期声对话。  
- 不宣称已完成短视频传播学完整 skill。

## 后续完善清单（给团队）

- [ ] 入库短视频/口播研究报告并蒸馏结构  
- [ ] 单独 `story_script_prompt.txt` + 分镜评测集  
- [ ] 区分 TikTok / Reels / YouTube Shorts 平台差  
- [ ] 本文件升为 active，更新 README 状态列

## 版本

- v0.3-script-placeholder · 2026-09-06  
- **v0.5-script-interim · 2026-09-14 · 合并 zip short_video 分镜字段与防假精确时点；明确 incomplete**
