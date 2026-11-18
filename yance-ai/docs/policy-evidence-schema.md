# 政策证据与园区地域 Schema

对应代码：`app/models/park_policy.py`、`app/services/park_policy/{conditions,evidence,retrieval}.py`、`app/services/park_registry/{catalog,geography}.py`
迁移：`alembic/versions/20261106_0037_park_policy_evidence.py`（纯新增四表）

---

## 1. 四张新表

| 表 | 作用 | 关键约束 |
| --- | --- | --- |
| `parks` | 园区/载体目录 | `park_type`、`status`、`boundary_status`、`verification_status` 均由 CHECK 约束限定枚举 |
| `park_policy_scopes` | 政策 ↔ 园区适用范围 | 归属条件分列：注册/纳税/实际经营/统计关系；`boundary_status != confirmed` 时 `applicable` 强制为 `needs_review` |
| `policy_conditions` | 证据化条件 | 含运算符、阈值、单位、统计期间、`review_status`、`source_locator` |
| `policy_eval_runs` | 评测运行记录 | 记录 arm、版本、digest、指标 JSON，禁止总分字段 |

**降级保护**：`downgrade()` 需要显式 `PARK_POLICY_ALLOW_DROP=1`，防止误删生产数据。

---

## 2. 园区地域模型

```
Park
├─ park_id / name / aliases
├─ park_type          national_high_tech_zone | provincial_high_tech_zone
│                     | economic_dev_zone | science_city | tech_park | incubator
├─ province / city / district(可空)   ← district 从名称反推属不可靠，故意留空
├─ designation_level / designation_basis / designation_year / operator
├─ official_url
├─ status             active | merged | renamed | revoked | unknown
├─ boundary_status    confirmed | needs_confirmation | disputed
├─ source_url / source_kind
├─ verification_status  registered | reachable | unreachable | needs_confirmation | rejected
└─ verified_at / verification_note / confidence / catalog_version
```

**硬性规则（代码强制，非文档约定）**

1. `boundary_status=confirmed` 但 `source_url` 为空 → `ParkCatalogError`（`catalog.py`）。
2. 别名冲突 → 加载失败，不允许"同名不同园"静默共存。
3. 未知 `park_type` / `status` / `boundary_status` / `verification_status` → 加载失败。

### 归属判定（`geography.py`）

```python
resolve_park_attachment(enterprise_facts, park) -> ParkAttachment
    registration_ok   注册地
    tax_ok            纳税关系
    operation_ok      实际经营地
    statistics_ok     统计关系
    address_is_not_entitlement  → 永远不因地址文本返回 attached
```

四种关系**分别判定、互不替代**；政策要求哪一项就查哪一项。缺证据返回 `needs_confirmation`，不返回 `attached`。

### 适用范围（`evaluate_scope`）

```
省级政策 → 省内企业均适用（不得缩为省会）
市级政策 → 市内企业适用
园区政策 → 需该园区归属证据 + 边界已核验
```

`boundary_status != confirmed` → 一律 `NEEDS_REVIEW`，即使企业证据齐全。

---

## 3. 政策证据模型

### 3.1 三个维度必须分离

| 维度 | 取值 | 说明 |
| --- | --- | --- |
| `validity` | `effective` / `expired` / `superseded` / `abolished` / `unknown` | 政策本身是否有效 |
| `source_health` | `healthy` / `fetch_failed` / `parse_failed` / `attachment_missing` | 来源是否可读 |
| `window_state` | `open` / `closed` / `not_started` / `suspended` / `unknown` | 申报窗口 |

**禁止混淆**：404 或抓取失败**不得**推出 `abolished`；窗口关闭**不得**推出政策失效。

### 3.2 版本与批次

```
Policy（政策家族）
├─ PolicyVersion（内容版本：内容哈希变化即新版本，旧版本保留）
├─ PolicyAttachment（附件：原始文件 + 哈希 + 解析版本 + 解析状态）
├─ PolicyApplicationWindow（批次：年度/批次号 + 起止 + 状态 + 官方入口）
└─ PolicyOrigin（来源关系：不同官方来源转载建立关联，均保留）
```

同一 `source_url` 内容变化 → 生成新 `PolicyVersion`，旧版保留（`upsert` 以 `content_hash` 判定，不以 URL 判定）。
不同批次独立建模，**不合并为同一条截止日期**。

### 3.3 原文证据必备字段

`origin_url` / `final_url`（重定向后）/ `publisher` / `fetched_at` / `http_status` / `content_type` / `content_hash` / `parser_version` / `raw_file_path`

**保存原文失败时不得标记为完整证据** —— `attachment_missing` 与 `parse_failed` 为独立状态，检索结果中必须降级展示。

### 3.4 解析策略

| 类型 | 方式 | 备注 |
| --- | --- | --- |
| PDF | 确定性文本抽取 | 扫描件转 OCR |
| Word/Excel | 结构化解析 | **禁止执行宏**，`openpyxl` 只读模式 |
| 扫描件 | 按需 OCR | 标注 `ocr_confidence` 与失败状态 |
| OFD | 专用解析器 | `crawler_output` 已含 ofd 样本 |

---

## 4. 条件模型（`conditions.py`）

```python
PolicyCondition
├─ condition_type    all_of | any_of | exclusion | threshold | period
│                    | unit_basis | scale_basis | exception | priority | no_double_funding
├─ field             对应企业事实字段
├─ operator          gte | gt | lte | lt | eq | neq | in | between | exists
├─ threshold_value / threshold_unit
├─ statistic_period  统计期间
├─ review_status     confirmed | needs_review
└─ source_locator    原文定位（条款号/页码/字符偏移）
```

### 结论

| 结论 | 触发条件 |
| --- | --- |
| `not_satisfied` | 明确不满足 |
| `needs_review` | 条件未核对、单位/期间异常、园区边界未确认、条款无法可靠表达 |
| `insufficient_evidence` | 企业事实缺失 |
| `likely_satisfied` | 已核对且事实齐全 |

聚合采用**保守优先**：`not_satisfied > needs_review > insufficient_evidence > likely_satisfied`。合成单一分数被明确禁止。

### 拦截规则（实测覆盖）

- 单位不一致（政策 `%` vs 企业 `万元`）→ `needs_review`，不算占比
- 统计期间缺失 → 不可计算
- 金额上限 → 输出"上限"，不输出"可得金额"
- `designation` 类支持不得渲染为现金补贴
- 不得重复享受未被核对时 → `needs_review`

---

## 5. 检索层（`retrieval.py`）

### 过滤顺序（服务端强制）

```
1. tenant_id（必填，缺失抛错 fail-closed）
2. visibility（公开政策 / 本租户私有资料）
3. region（省/市/园区 scope）
4. park_id（未知 park_id 直接拒绝，不回退为城市）
5. 状态过滤（validity / window_state）
6. 关键词 + 向量混合
7. 重排
```

权限过滤在 **SQL `WHERE`** 内完成，不做生成后补救。`park_aware_search` 对 `park_id` 未知的情况**拒绝**而非降级为 `city`——避免"城市=园区"的错误合并。

### 空结果归因（`describe_empty_result`）

| 原因 | 表述 |
| --- | --- |
| 来源未登记 | 该地区无登记来源 |
| 来源暂停/未启用 | 来源已暂停采集 |
| 抓取失败 | 来源异常，非"确无更新" |
| 真无匹配 | 已采集范围内无匹配 |

"新增 0 条"必须能区分上述四种，禁止一律报告为"无更新"。

---

## 6. 企业事实模型

```
EnterpriseFact
├─ field / value / unit / statistic_period
├─ source_document / evidence_locator
├─ provided_by / updated_at
├─ confirmation_status   unconfirmed | customer_confirmed | disputed
└─ conflict_state        none | conflicting（保留双方来源，不静默覆盖）
```

用户纠正资料保留历史，不静默覆盖。事实变更 → 关联资格结论标记 `stale`，要求重新核对，**不自动覆盖旧报告**。

---

## 7. 未建模（已知缺口）

| 缺口 | 影响 |
| --- | --- |
| `enterprise_service_authorizations`（园区↔企业授权） | 园区工作台不可用，P2 |
| 官方解读/问答独立实体 | 混在政策正文 |
| 附件 ↔ 条件 的逐条溯源表 | `source_locator` 只能到页/段级 |
| 公示名单实体 | 未采集（且明确不作为客户案例） |
