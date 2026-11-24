# 租户数据删除操作手册（ACC-14）

状态：**人工流程**。系统中的删除申请（`deletion_requests`）只做登记，不会自动执行（`app/api/routes/enterprise.py`）。隐私政策承诺"核实后 30 天内删除或匿名化"，本手册就是兑现这个承诺的执行步骤。

脚本 `yance-ai/ops/tenant_data_deletion.sql` 按数据库**实际的外键依赖**（Alembic `20261124_0028`）生成，已在一次性测试库上验证（见文末）。

> ⚠️ **最重要的一条：永远不要执行 `DELETE FROM tenants`。**
> 订单、支付、支付事件、发票、权益、订阅、用量记录到 `tenants` 的外键全部是 `ON DELETE CASCADE`。删除租户行会把这些需要依法保存的财务凭证一并删掉，并且无法恢复。脚本只会匿名化并停用租户行。

## 0. 角色与前提

| 角色 | 职责 |
|---|---|
| 客服 / 数据保护负责人 | 核实身份、与用户确认处理方式、回复用户 |
| 数据库负责人 | 执行脚本，保存输出 |
| 运维负责人 | 删除对象存储（OSS）中的文件，确认备份保留期 |
| 法务 | 确认保留数据的范围和期限（见第 6 节） |

执行前，先在最近一次备份的恢复库（`ops/restore_drill.sh` 生成的 `yance_restore_*`）上完整演练一遍。

## 1. 核实申请

1. 申请必须来自该租户 owner 的注册邮箱，或者经过书面授权的企业联系人。
2. 用以下 SQL 找到租户，并确认企业全称与申请一致：

   ```sql
   select t.id, t.name, t.slug, u.email
   from tenants t
   join memberships m on m.tenant_id = t.id and m.role = 'owner'
   join users u on u.id = m.user_id
   where u.email = lower('<申请邮箱>');
   ```

3. 在 `deletion_requests` 中登记，或找到已有的登记记录，记下 `tenant_id`。
4. 确认没有处理中的订单或退款：

   ```sql
   select id, status, amount from orders
   where tenant_id = '<tenant_id>' and status in ('created', 'pending');
   ```

   代码中订单只有 `created`、`pending`、`paid` 三种状态（`app/services/payments/settlement.py:140`）。查到 `created` 或 `pending` 的订单，先与用户和支付渠道确认处理完毕，再继续删除。

## 2. 导出（用户需要时）

用户要求"先导出后删除"时，用租户 owner 账号调用产品内的导出功能（`/api/v1/enterprise/exports`），把结果交付给用户，并保留交付记录。

## 3. 记录对象存储中的文件清单

**必须在删除数据库之前做**，删完数据库就查不到文件路径了。

```sql
\copy (select 'documents' src, object_key from documents where tenant_id = '<tenant_id>' and object_key is not null
       union all select 'artifacts', object_key from artifacts where tenant_id = '<tenant_id>' and object_key is not null
       union all select 'deliverables', file_url from deliverables where tenant_id = '<tenant_id>' and file_url is not null)
to 'oss_objects_<tenant_id>.csv' csv header
```

## 4. 删除数据库中的数据

```bash
# 第一步：试运行。在事务里执行全部删除并做事后校验，最后回滚，不改任何数据
psql "$PROD_DSN" -v tenant_id=<tenant_id> -f yance-ai/ops/tenant_data_deletion.sql

# 第二步：正式执行。只有 confirm 精确等于 DELETE 才会提交，其他值一律回滚
psql "$PROD_DSN" -v tenant_id=<tenant_id> -v confirm=DELETE -f yance-ai/ops/tenant_data_deletion.sql
```

脚本做了这些事：

- 在**一个事务**中按外键依赖顺序（子表在前），删除 53 张业务表中该租户的数据。
- **保留** 10 张表：`orders`、`payments`、`payment_events`、`invoices`、`entitlements`、`subscriptions`、`subscription_items`、`usage_records`、`audit_logs`、`deletion_requests`。
- 把租户行改为 `name='已注销租户'`、`slug='deleted-<id>'`、`is_active=false`。
- 提交之前逐表检查：除保留表以外，该租户在任何一张表中都不能还有数据，否则整个事务报错回滚。

保存两次执行的完整输出。

> 数据库结构变化后（新增表或新增外键），脚本中的删除顺序可能过时。由于事后检查会覆盖所有带 `tenant_id` 的表，新表漏删时脚本会失败并回滚，不会静默漏删。此时需要按新的外键关系重新生成脚本。

## 5. 删除对象存储中的文件

按第 3 步导出的清单逐个删除（例如 `ossutil rm oss://<bucket>/<object_key>`），然后抽查 5 个对象，确认已返回 404。

## 6. 保留数据与备份

| 数据 | 处理方式 | 待确认事项 |
|---|---|---|
| 订单、支付、发票等财务记录 | 保留，租户已匿名化 | **法务确认**会计凭证和发票的保存期限，以及到期后如何清理。发票中的抬头、税号、地址电话、银行账户属于发票法定内容 |
| `audit_logs` | 保留 | **法务确认**安全日志的保存期限，以及其中个人信息的处理方式 |
| `deletion_requests` | 保留 | 作为已依法处理的凭证 |
| 数据库备份 | 不单独改写备份；按备份保留期自然过期 | 在回复用户时写明最晚的过期日期（当前保留期见 `ops/backup.sh` 的 `YANCE_BACKUP_RETENTION_DAYS`，默认 14 天，**清理默认关闭**，必须开启清理后这个期限才成立） |
| 异地备份副本 | 同上，按对象存储的生命周期规则过期 | 运维确认生命周期规则已配置 |

## 7. 回复用户并留档

回复内容包括：已删除的数据范围、依法保留的数据类别和原因、备份最晚的过期日期。把申请、核实记录、脚本输出、OSS 清单和回复一起归档。

## 附：本地验证记录（2026-11-24）

在一次性测试库（PostgreSQL 16 + pgvector，跑完 194 个后端测试后的数据）上执行：

| 场景 | 删除前 | 试运行后 | `confirm=yes` | `confirm=DELETE` 后 | 其他租户 |
|---|---|---|---|---|---|
| 覆盖 26 张表的租户 | 34 行 | 不变 | 回滚 | 0 行 | 2563 行，不变 |
| 有财务记录的租户 | 10 行（9 行属于保留表） | 不变 | 回滚 | 9 行，全部是保留表 | 不变 |
