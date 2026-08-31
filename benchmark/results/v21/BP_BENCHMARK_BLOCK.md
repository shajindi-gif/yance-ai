# BP_BENCHMARK_BLOCK.md — Yance Policy Engine V2.2 Benchmark 冻结块

- 生成时间: 2026-08-31 21:44
- 引擎版本: policy-engine-v2.2 (commit 1a6269b) — 冻结 commit，禁改码
- 冻结 Dataset: benchmark_cases.jsonl (S01-S16) — frozen_input_sha256 已落盘，禁止修改
- 冻结 Gold: gold_answers.jsonl — 只读派生 gold_eligibility.jsonl，禁止为提分修改
- Track A: DeepSeek Raw (deepseek-chat, T=0)
- Track B: Yance + Same DeepSeek
- 评分规则: 禁止 hardcode case id；准确率=overall_result 与 gold_q1 一致率
- 红线: env.prod 不入库/不打印/不入报告
- 结论: 未超越（与裸 DeepSeek 持平，见失败归因）（Yance 43.8% vs DeepSeek Raw 43.8%）
- 状态: 完整跑通
- 下一步: V3 扩样本至 50-100、冻结参考日期、补 Track C(Qwen)、公开评分脚本复现
