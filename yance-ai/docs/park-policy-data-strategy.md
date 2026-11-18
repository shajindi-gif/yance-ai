# 园区政策与资源证据系统 · 数据策略

版本：2026-11-06 / 适用仓库 `/Users/shajindi/yance-backup/yance/`（后端 `yance-ai/`）

本文只陈述**已落地的事实**与**明确的边界**。凡未实测的部分逐项标注为待验证或阻塞。

---

## 1. 目标定位

不是"接入通用模型的聊天页面"，而是可持续积累的数据资产 + 专业工作流：

```
官方来源 → 原文及附件 → 政策版本与申报批次 → 结构化条件
        → 企业证据 → 可解释匹配 → 补证与材料工作稿 → 客户复核 → 授权导出
```

"比通用大模型更精确"是**待验证目标**，不是现成结论。任何对外表述不得使用"准确率 99%"、"全国最全"、"全面超越通用模型"。政策条数、向量数量、合成测试通过率均不作为业务准确率证据。

---

## 2. 两类客户与权限边界

| 角色 | 核心任务 | 权限边界 |
| --- | --- | --- |
| A 园区内企业 | 找机会、核对资格、判断投入、补材料、追踪申报窗口 | 只能读自己租户的数据；授权可撤销、有审计、可到期 |
| B 园区/科创服务机构 | 管理授权企业、发现共性机会、分派补证、追踪进展 | 仅见已获企业授权的范围；不得因"同园区"自动读取财务/研发/知识产权/材料 |

**已实现**：`app/services/park_registry/geography.py` 中 `resolve_park_attachment` 将注册、纳税、实际经营、统计关系四类归属分别判定，互不替代；`address_is_not_entitlement` 守卫禁止以地址文本授予园区资格。检索层 `RetrievalFilters.tenant_id` 为必填，`assert_server_side_tenant_filter` 在缺租户时抛错（fail closed），租户谓词进入 SQL `WHERE`，不做生成后补救。

**未实现**：园区运营方与企业的授权关系表（`enterprise_service_authorizations`）尚未建模，因此园区工作台在当前版本**不可用**，不得展示任何跨企业统计。这是明确的 P2 阻塞项。

---

## 3. 六类数据资产

| # | 资产 | 状态 | 说明 |
| --- | --- | --- | --- |
| 1 | 政策与管理办法 | 有模型，采集在跑 | 复用 `Policy` / `PolicyVersion` / `PolicyChunk` |
| 2 | 当期申报通知、指南、更正、延期、废止 | 部分 | `PolicyApplicationWindow` 支持批次、延期、暂停 |
| 3 | 官方附件、申报表、材料清单 | 有模型 | `PolicyAttachment`；解析失败单独分层 |
| 4 | 官方解读、问答、办理指引 | 未独立建模 | 当前混在政策正文，属缺口 |
| 5 | 园区目录、地域适用条件、公开服务资源 | 已建 | `config/parks/*.yaml` + `parks` 表 |
| 6 | 企业授权事实与证明 | 部分 | 需与 `PolicyCondition` 配对，见 §6 |

**官方获奖/资助公示**：可用于理解政策执行背景，但**不得**作为平台客户案例、不得据此推断其他企业获批概率、不得把公示中的个人信息无差别纳入客户检索库。当前版本未采集任何公示名单。

---

## 4. 质量门槛与分层

不把可疑数据与可信数据混为一类。分层字段：

- `verification_status`：`registered` / `reachable` / `list_verified` / `unreachable` / `needs_site_adapter` / `blocked_by_robots`
- `boundary_status`：`confirmed` / `needs_confirmation` / `disputed`
- 证据层 `PolicyEvidenceState.source_health`：`healthy` / `fetch_failed` / `parse_failed` / `attachment_missing`

**关键约束**：`registered` 不等于已覆盖；`reachable` 不等于已采到原文；`来源异常` 不等于 `政策废止`（`evidence.py` 中两者为独立维度，404 只标记异常并保留旧证据）。

---

## 5. 园区目录口径

`config/parks/national_high_tech_zones.yaml`，`catalog_version: 2026.11.06-parks.1`，共 31 条。

| 维度 | 实测分布 |
| --- | --- |
| 类型 | `national_high_tech_zone` 30、`economic_dev_zone` 1 |
| 核验状态 | `registered` 25、`unreachable` 4、`reachable` 2 |
| 边界状态 | `needs_confirmation` 31（全部） |

刻意留空与保留待确认的原因：

1. **`district`（区县）全部留空**。国家高新区普遍"一区多园"或跨区，从园区名称反推区县属不可靠裁剪，正是上一轮要复核的问题。
2. **`designation_basis` 只陈述层级事实**，不填写未核验的批复文号。
3. **`boundary_status` 统一 `needs_confirmation`**，`catalog.py` 强制：状态为 `confirmed` 却无 `source_url` 直接报错。

**不宣称**存在未经核验的"全国科创前 30 名"官方排名；不将园区目录包装为合作伙伴、已签约客户或平台资源库存。园区所在地 ≠ 园区政策适用范围。

---

## 6. 条件与证据的表达

`app/services/park_policy/conditions.py`：

- 运算符：全部满足 / 任选其一 / 排除条件 / 阈值 / 统计期间 / 单位 / 规模口径 / 例外 / 优先 / 不得重复享受
- 四条结论：`likely_satisfied` / `not_satisfied` / `insufficient_evidence` / `needs_review`
- 保守优先序：`not_satisfied > needs_review > insufficient > likely_satisfied`
- 单位或统计期间不一致时**直接拦截计算**（`单位不一致：政策要求 %，企业事实为 万元`）
- `review_status != confirmed` 的条件一律返回 `needs_review`，不按字面判定

**确定性计算用规则；模型只做抽取与解释**，不得补造规则、企业事实或扩大权限。"符合"仅表示在已提供资料与已核对条件范围内满足，不代表政府认定或最终获批。不输出虚构获批概率。

金额口径：上限 ≠ 企业可得金额；"认定" ≠ 现金补贴。支持形式分 `project_grant` / `designation` / `designation_reward` / `loan_interest_subsidy` / `tax_incentive` / `service_voucher` / `other` 分别标注。

---

## 7. 数据积累现状（可核验）

| 项 | 数量 | 来源 |
| --- | --- | --- |
| 政策来源登记 | 108（启用 90） | `config/policy_sources/` |
| 层级分布 | national 20 / provincial 53 / municipal 35 | 同上 |
| 来源核验 | document_verified 79、list_verified 6、unreachable 16、needs_site_adapter 3、registered 3、blocked_by_robots 1（2026-11-06 全量干跑后回写） | 同上 |
| 首批重点城市 | 30 | `priority_cities.yaml` |
| 园区目录 | 31（30 高新区 + 1 经开区） | `config/parks/` |
| 真实抓取产物 | 85 个 HTML / 3.1MB（全量干跑）+ 早期 30 文件含附件样本 | `crawler_output/dry_run/`、`crawler_output/policy_raw/` |
| 本地数据库 | **无** | 迁移未执行 |

**不做统计口径混淆**：政策条数、独立政策家族数、申报批次数、附件数、文本分块数分别统计，分块数不冒充政策数量。

---

## 8. 模型策略

优先做检索、原文、规则、版本、反馈、评测。**默认不启动微调或训练**。

- 客户资料与修改反馈不进跨客户训练集或共享知识库
- 跨客户复用需明确授权 + 数据治理 + 单独评估
- 只有评测证明剩余问题确实适合微调，且已有合法、足够、可靠数据时，才提出微调方案、预算与回归标准
- 模型调用设每日预算与熔断；缺真实供应商配置时明确停用相应阶段（当前即处于此状态）

---

## 9. 已知阻塞项

| 阻塞 | 影响 | 解除条件 |
| --- | --- | --- |
| 本地无数据库，迁移未执行 | 检索/入库无法端到端验证 | 提供隔离测试库或授权建库 |
| 无模型供应商配置与预算 | 评测 A/B 臂不可运行，抽取阶段停用 | 版本、资源预算、验收、回退方案确认 |
| 园区-企业授权关系未建模 | 园区工作台不可用 | P2 建模 + 权限审计 |
| 30 城中 4 直辖市无独立 municipal 源 | 京沪津渝的城市级覆盖依赖省级共享 | 补登记市级来源或明确标注共享 |
| 15 个来源 unreachable | 该地区覆盖不成立 | 站点适配器或改入口 |
