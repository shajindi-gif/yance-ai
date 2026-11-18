# 园区政策工作区 · 实现说明

分支 `feature/investor-grade-upgrade`，本轮全部为**未提交**新增，未改动既有业务代码。

| 层 | 文件 | 行数 | 状态 |
| --- | --- | --- | --- |
| 数据模型 | `app/models/park_policy.py` | 218 | 新增 |
| 迁移 | `alembic/versions/20261106_0037_park_policy_evidence.py` | — | 已生成，**未在真实 PostgreSQL 验证** |
| 园区目录 | `app/services/park_registry/catalog.py` | 385 | 新增 |
| 地域判定 | `app/services/park_registry/geography.py` | 337 | 新增 |
| 条件矩阵 | `app/services/park_policy/conditions.py` | 532 | 新增 |
| 证据层 | `app/services/park_policy/evidence.py` | 334 | 新增 |
| 混合检索 | `app/services/park_policy/retrieval.py` | 443 | 新增 |
| 对照评测 | `app/services/park_policy/evaluation.py` | 573 | 新增 |
| 运维入口 | `scripts/park_policy/cli.py` | — | 新增 |
| 来源/园区配置 | `config/parks/*.yaml`、`config/policy_sources/` | — | 新增 |
| 测试 | `tests/park_policy/*.py` | 814 | 新增 |

测试：`tests/park_policy + tests/policy_collection` = **118 passed**（1.37s，无 DB）。

---

## 1. 四张新表（`app/models/park_policy.py`）

| 表 | 用途 | 关键约束 |
| --- | --- | --- |
| `parks` | 园区目录，含类型、认定依据、行政区划、官网、有效状态、来源、核验时间 | `park_type` 枚举区分高新区/经开区/科技园/孵化器，不得混同 |
| `park_policy_scopes` | 政策适用地域与园区范围，一政策多 scope | `qualification_basis` 必填；`requires_confirmation` 默认 true |
| `policy_conditions` | 证据化条件：all_of / any_of / exclude / threshold / period / unit / exception / priority / no_double_dip | 无法确定性表达的条款标 `needs_review`，不压成简单分数 |
| `policy_eval_runs` | 版本化评测运行记录 | 绑定 eval_set version + digest，保证可复现 |

**迁移状态：已生成（`20261106_0037_park_policy_evidence.py`），尚未在真实 PostgreSQL 上验证 upgrade/downgrade 双向往返。**

迁移的设计约束（已写在文件头，可作为评审依据）：
- 只 `create_table` 四张新表 + 索引，**不 alter 任何既有列**，因此旧应用版本可在已迁移库上继续运行
- `downgrade` 默认拒绝删表，需显式 `PARK_POLICY_ALLOW_DROP=1`，因为 park scope、条件、引用条款是资格结论的审计链
- 下游依赖 `20261106_0036`（上一轮 policy_collection 迁移）

**未验证项**：本机无 PostgreSQL，`alembic upgrade head` / `downgrade -1` 未实际跑通。按发布门槛，验证前不得部署到生产。

---

## 2. 地域目录与归属判定

### 2.1 目录规模

31 条：30 个国家高新区 + 1 个经开区（苏州工业园区，因其按经开区口径管理政策）。

校验命令与真实输出：

```
$ python scripts/park_policy/cli.py parks validate
OK 园区目录 2026.11.06-parks.1 records=31 files=1 digest=d087f89d276777a3

$ python scripts/park_policy/cli.py parks summary
types        : {'national_high_tech_zone': 30, 'economic_dev_zone': 1}
verification : {'registered': 25, 'unreachable': 4, 'reachable': 2}
boundary     : {'needs_confirmation': 31}
```

**边界核验为 confirmed 的数量是 0。** 这不是未完成项被藏起来，是如实状态：没有任何园区拿到了官方四至边界文件。系统因此对所有园区政策一律返回 `needs_review`，而不是猜一个"大概在范围内"。

### 2.2 地址不是资格（核心不变量）

`geography.py` 的关键设计：`ADDRESS_FACT_KEYS`（地址、注册地文本）与 `PARK_FACT_KEYS`（园区归属证明）严格分离。仅有地址事实时，`resolve_park_attachment` 返回 `NEEDS_CONFIRMATION`，绝不返回 `CONFIRMED_MEMBER`。

实测（真实命令输出）：

```
$ ... parks scope --level park --park-id park_sz_sip \
    --fact address_city=苏州市 --fact address_district=工业园区
{
  "verdict": "needs_review",
  "reason": "园区 park_sz_sip 边界状态为 needs_confirmation，不得据此判定企业符合园区政策",
  "basis": "park_boundary",
  "requires_confirmation": true
}
```

企业地址明明在苏州工业园区，系统仍拒绝判定符合。这是设计目标，不是缺陷。

### 2.3 省级范围不误缩为省会

`scope_type=province` 只比较 province 字段，不隐含 city。实测：

```
$ ... parks scope --level province --province-of-policy 江苏省 --reviewed \
    --fact province=浙江省 --fact city=杭州市
verdict: not_satisfied  ("企业行政区划不在该政策适用范围内：province:浙江省!=江苏省")

$ ... --province-of-policy 江苏省 --reviewed --fact province=江苏省 --fact city=徐州市
verdict: satisfied       (徐州不是省会，仍命中省级范围)
```

---

## 3. 条件矩阵

`conditions.py` 把政策条件结构化为可确定性求值的节点，求值结果只有四种：`satisfied` / `not_satisfied` / `insufficient_evidence` / `needs_review`。

关键约束：
- 阈值比较必须带单位与统计期间，单位不一致时返回 `needs_review` 而非强行换算
- `exclude` 条件优先于 `all_of`：排除项命中即为 `not_satisfied`
- `no_double_dip` 需要历史受资助事实，缺失时 `insufficient_evidence`
- 金额上限 != 企业可得金额：`amount_ceiling` 只作为门槛上限参与比较，不写入"可获金额"

---

## 4. 证据层

`evidence.py` 强制三件事：

1. **每个关键字段的可支持性**：字段值要么带原文位置，要么显式标为未知。不允许静默留空。
2. **相关性、完整度、资格判断三者分离**；不计算获批概率（没有该字段）。
3. **来源可信 != 内容完整 != 仍有效 != 企业符合**。四件事分别有字段。

`invented_support_count` 是评测硬指标：任何在无原文支持时声称"符合原文"的行为都计数，且计入 `severe_error`。

---

## 5. 混合检索

`retrieval.py`：
- 关键词 + 文号 + 语义三路合并，RRF 融合
- 硬权限过滤在**服务端检索阶段**执行（租户 / 私有库边界），不在模型生成后补救
- 支持地区、园区、企业类型、政策状态、申报时间过滤
- 别名映射表处理机构更名、园区别名、行业术语（`config/parks/*.yaml` 内 `aliases`）
- 未接入真实向量库时的降级：纯关键词 + 规则重排，并在结果中标 `degraded=true`

**未验证项**：真实语料下的 Recall@K。需 DB + 入库政策，见 `policy-retrieval-evaluation.md` 第 5 节。

---

## 6. 权限边界（P0）

沿用既有租户模型，未新增"园区管理员可读所有企业"的角色。

| 主体 | 可见范围 |
| --- | --- |
| 园区/服务机构 | 仅公开政策能力 + 企业**明确授权**的数据范围 |
| 园区内企业 | 自身全部数据 |
| 其他租户 | 不可见 |

"位于同一园区"不构成授权依据。授权可撤销、有访问审计、有到期控制（复用既有 permission 模块）。测试 `ENG-SEC-001~004` 覆盖跨租户检索、提示注入、越权读取。

**未尽事项**：授权撤销与到期的端到端测试需要 DB，本地未执行，标注为服务器待验证。

---

## 7. 与既有系统的关系

| 复用 | 说明 |
| --- | --- |
| 政策库与检索 | 扩展，不新建平行库 |
| 任务与调度 | 复用 `scripts/policy_collection` 的任务锁与断点机制 |
| 权限 | 复用租户与授权模块 |
| 部署体系 | 未引入新微服务，未引入新队列 |

未创建任何替代应用，未触碰生产副本业务代码。

---

## 8. 已知缺口（不掩盖）

1. **无 Alembic 迁移**：需 DB 验证双向往返后才能提交
2. **园区边界全部未核验**：所有园区政策判定为 `needs_review`
3. **园区目录仅 31 条**：省级高新区、科技城、孵化器未纳入（待官方名录）
4. **条件矩阵未接真实政策**：532 行规则只有合成测试覆盖
5. **评测 A/B 臂未运行**：无模型供应商配置
6. **前端无工作台页面**：本轮只做后端与 CLI，`website/` 未改动
7. **生产状态未知**：服务器只做只读核查（见 runbook）
