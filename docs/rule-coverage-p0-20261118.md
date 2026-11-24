# P0 规则覆盖尖刀 · 2026-11-18

结论：上海切片规则覆盖从 **2.2% → 95.6%**；上海 AI 企业扫描中「尚无结构化规则」占比从 **96% → 22%**，有规则路径且带 verified 证据的 NEED_MORE 达 **39/50**。

## 做法（无 LLM 编造、未混提 dirty collector）

- 新模块：`yance-ai/app/services/policies/rule_seeding.py`
- 运维脚本：`scripts/eligibility_rules/seed_slice.py`、`seed_matched_scan.py`
- 规则来源：原文关键词模板 + **exact-span**（version + chunk）校验后入库，`tenant_id=NULL` 全局规则
- 生产已 apply：
  1. `--province 上海市 --limit 50` → +52 rules（覆盖 43/45 versions）
  2. 对真实扫描命中政策补种 → +61
  3. `--national-topics --limit 120` → +40
- 当前生产 `active` EligibilityRule：**≥154**

## 验证扫描（合成租户）

| 轮次 | scan_id | 缺结构化规则占比 | 有规则路径 | NEED_MORE 且有 verified 证据 | 正例 |
| --- | --- | --- | --- | --- | --- |
| 播种前基线（冒烟） | `0674c422…` | ~98%（49/50） | 1 | 1 | 1（注入政策） |
| 上海+命中补种后 | `37e9a2aa…` | 96% | 2 | 2 | 0 |
| 再加全国主题后 | `fe861f61…` | **22%** | **39** | **39** | 0 |

正例仍为 0 的主因：多数政策缺 `effective_at/expires_at/deadline` 等元数据，`policy_context_issues` 仍会诚实标 NEED_MORE——符合「不编造」；但已不再几乎全是「尚无已审核的结构化资格规则」。

## 命令

```bash
# 指标
python /tmp/seed_slice.py --metrics-only

# 上海切片（先 dry-run 再 --apply）
python /tmp/seed_slice.py --province 上海市 --limit 50 --dry-run
python /tmp/seed_slice.py --province 上海市 --limit 50 --apply

# 全国主题
python /tmp/seed_slice.py --national-topics --limit 120 --apply

# 对某次扫描命中政策补种
python /tmp/seed_matched_scan.py --scan-id <uuid> --apply
```

生产通过 `docker run --network yance-prod_default --env-file production.env -v ...` 挂载脚本执行。

## 风险与下一刀

- Matcher 仍偏全国语料，需持续对「扫描命中但无规则」做 `seed_matched_scan` 闭环
- P1：按有规则/有引用/截止日排序；补齐可核实的日期元数据（禁止臆造）
- P1/P2：可选 LLM 摘要层仍不得改硬事实；Ask 保持关闭
