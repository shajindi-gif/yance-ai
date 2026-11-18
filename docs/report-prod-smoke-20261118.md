# 生产冒烟 · 报告交付 · 2026-11-18

结论：**通过**（合成租户、合成 paid，无真实扣款）。

## 环境

- API：`report-20261118-01` / `2cd6cdb`
- DB：`20261117_0043`
- Ask：关闭

## 路径与 ID（合成冒烟，非真实客户）

| 项 | 值 |
| --- | --- |
| tenant_id | `eb7ce8e9-8b42-430b-8dcb-1c35d67a1556` |
| company_id | `32f1716b-a4a3-4be6-96ef-b2071a91d9d3` |
| scan_id | `0674c422-a5cf-446a-b5cd-3388222c4a00` |
| deliverable_id | `f192ac4a-d0a9-444e-9210-97a0891c3c7d` |
| order_id | `cd4050a4-6679-5aa7-bdf3-e2e1f59b06b1` |
| smoke_policy_id | `4331882d-14ba-45bf-811f-2f139a4ce65f` |

脚本：服务器 `/opt/yance/releases/report-20261118-01/prod_smoke.py`  
产物：容器内 `/tmp/report_prod_smoke_20261118.json`

## 断言结果

- `content_json.schema_version = report-card-v1`，`total_matches = 50`
- 门禁：`release_gate_passed=true`；`unsupported_claim_ratio=0`；`ungrounded_sentence_ratio=0`
- 状态分布：`NEED_MORE_INFORMATION=49`，`POTENTIALLY_ELIGIBLE=1`（仅冒烟注入的租户私有政策+规则）
- 订单绑定 `report_deliverable_id` 正确；下载 PDF SHA256 与 `frozen_pdf` 一致
- 失败清单：空

## 风险 / 下一步

生产全局 **几乎没有 active EligibilityRule**（冒烟注入后库内仅 1 条）→ 真实客户扫描会大量 NEED_MORE。下一步做规则覆盖运营（见证据不足清单），勿开放 Ask、勿混提采集脏文件。
