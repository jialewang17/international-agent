# 追溯样例（step_audit trace samples）

这四份 JSON 不是手写的，是 `scripts/make_step_trace_samples.py` **调用真实代码**跑出来的：

| 文件 | 场景 | 终态 | 说明 |
|---|---|---|---|
| `generation_ok.json` | post 体裁一次完整生成 | `COMPLETE` | C00–C06 七步全 OK，含 `skill_load` 诊断 |
| `generation_blocked_c05.json` | 模型输出不是 JSON | `FAILED`（停在 C05） | C00–C04 已跑，C06 标 `NOT_RUN` |
| `evaluation_ok.json` | Part 3 六维评分 | `COMPLETE` | E00–E05 全 OK，含 E05 五项确定性检查 |
| `evaluation_blocked_e03.json` | `evidence_spans` 偏移与原文不符 | `FAILED`（停在 E03） | 偏移不一致被转成 blocking issue |

## 哪些是真的，哪些是替身

| 部分 | 真实性 |
|---|---|
| 步骤流转、门禁判定、加载诊断、跨度核对、确定性校验 | **真实**：走的是生产代码路径 |
| 模型成稿正文 | **替身**：`_llm_text` 返回固定 JSON，不联网、不花钱 |
| 六维分数与 `confidence` | **替身**：`StubJudge` 固定给 4 分 / 0.5，仅用于结构样例 |

因此：**这些文件不能用来证明"模型写得好"或"评分准确"**，只能用来证明
"每一步跑没跑、依据对不对、拦没拦住"。文件里的 `_note` 字段已写明这一点，
测试 `test_committed_trace_samples_stay_consistent` 会强制每个文件都带 `_note`。

## 怎么复核

```bash
# 逐份复核（退出码 0 = 结构与状态自洽）
python scripts/step_audit_check.py docs/chinastory_v6.1/step_trace_samples/generation_ok.json
python scripts/step_audit_check.py docs/chinastory_v6.1/step_trace_samples/evaluation_ok.json

# 要求必须 COMPLETE（交付前自检用）
python scripts/step_audit_check.py docs/chinastory_v6.1/step_trace_samples/generation_ok.json --require-complete

# 顺带校验 13 步 / 40 个方法依据锚点是否还在
python scripts/step_audit_check.py --evidence
```

## 怎么重新生成

代码行为一变（新增步骤、改状态、改门禁），样例就会过期，必须重跑：

```bash
python scripts/make_step_trace_samples.py
python -m pytest tests/test_step_audit.py -q
```

> 建议把"重跑样例 + 复核 + 测试"作为提交前动作。样例过期而不自知，
> 等于把旧证据当新证据用——这正是本次任务要消灭的那类问题。
