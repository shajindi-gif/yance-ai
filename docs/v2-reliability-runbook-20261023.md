# V2第二批隔离复验与待审发布操作

本手册描述待审操作，不是生产执行授权。源码以本文件所在的第二批Git提交为候选，基线adb2aea；批准时必须补完整SHA、镜像摘要、PG16证据及目标环境，不使用“最新代码”代替版本。

## 隔离复验

全套测试须新建专用库；已有测试全局计数/队列用例依赖空起点。不能连接生产、复用客户备份或删除已有数据来通过测试。示例库只属于本机合成环境，数据库必须先创建。

```sh
cd /Users/shajindi/yance-backup/yance/yance-ai
export APP_ENV=test
export DATABASE_URL=postgresql+psycopg://yance@127.0.0.1:55440/yance_v2_reliability_final_test
export YANCE_TEST_DATABASE_ACK=yance_v2_reliability_final_test
export EMAIL_ENABLED=false LLM_DEFAULT_PROVIDER=mock
.venv/bin/alembic upgrade head
.venv/bin/alembic check
.venv/bin/python -m pytest --cov=app --cov-report=term --cov-fail-under=50 --tb=short
.venv/bin/python scripts/export_openapi.py --check
.venv/bin/python evals/run_evals.py run --no-persist
.venv/bin/ruff check app tests scripts/verify_worker_shutdown.py
```

上述实际最终验收库已有记录，重跑全套应使用另一新库及相同ACK，不清理它。停机脚本另外使用空的迁移测试库 DATABASE_URL，并执行 `.venv/bin/python scripts/verify_worker_shutdown.py`；脚本拒绝非localhost、非test、非_test数据库和已有AgentRun的数据库，强制关闭邮件。迁移往返只对空的可丢弃库执行，不能用于生产回退。备份恢复核验沿用 scripts/verify_database_snapshot.py，两端仅接受本机 *_test 库，输出哈希和统计，不输出行内容。

## 发布前必须形成的具体验收包

负责人动作：工程固定候选SHA/镜像与PG16证据；运维只读核实生产当前版本、0027前置、容量/锁窗口/队列与进程管理方式，验证新鲜备份可恢复；业务负责人复核真实证据与历史稿重新审批影响；邮件负责人在隔离收件箱验证供应商状态语义与发送量。将这些结果和目标43.128.1.64、维护窗口、迁移影响、回退条件交用户确认后才能操作。

不能混跑旧/新任务进程。旧进程不校验token，旧邮件处理还会修改dedup key；新增schema的ORM兼容不能证明旧worker安全。先停接新任务、排空或停止旧worker，记录在途run和发送状态；不删除任务。关闭EMAIL_ENABLED并保持notifications profile关闭。仅停止旧worker后迁移0028，部署固定新API/worker，隔离检查新认领与token、取消/租户授权、生成/批准/导出和支付回归，再灰度恢复入队。迁移锁等待超限应中止并前向处理，避免无限等待。

邮件另行批准启用：先按租户/状态统计历史未读高优先级提醒和pending意图，明确积压量、过时提醒处理与收件范围；不能直接把全部历史积压当新邮件发送。默认不启用notifications容器，但只要开启EMAIL_ENABLED，原agent-worker小时扫描也会投递outbox，因此必须同时评估两个入口，不能仅依赖profile控制。未验收供应商时保持邮件关闭。

## 待核实通知处理

监控pending最老年龄、sending超时、uncertain/failed数量、attempt_count、任务lease回收数、终态错误和请求/租户/任务关联；日志不记录邮箱、正文、供应商响应体或密钥。仅供授权运维在受控管理环境按通知ID/收件人内部ID核对，禁止在聊天导出内容。

uncertain 可能已送达，必须先核对供应商投递记录/邮件回执。明确已送达：经审计前向补记结果；明确未接收：记录证据与负责人批准后，才可单条前向恢复到pending并遵守次数上限。无法确认则继续uncertain，不批量重置，不删除旧意图，不改变通知dedup_key。本批没有提供自动核实或人工重发API；未来管理入口须补角色授权和审计，不能绕过授权直接向外发送。failed/suppressed也不自动复活。

## 灰度失败与回退

跨租户访问、旧尝试成功写入、重复权益、关键无依据资格结论、重复邮件或队列异常增长立即阻断发布/暂停新任务与外发，保留账本与故障证据。新旧API兼容只验证有限ORM读写，不替代目标环境回归。

应用回退前停止新版和旧版worker、关闭外发与入队；保留0028列和投递历史。不得在生产执行downgrade：它会删除投递审计表。优先前向修复；若回旧API，仍须维持第一批批准/提交/下载安全限制，不能由回退重新开放旧安全缺口。任何恢复备份都需单独确认数据窗口和对账计划，不覆盖迁移后真实订单。任务在修复后由新worker按租约/重试状态恢复；uncertain邮件不能随任务重跑而重发。恢复后对订单/权益逐笔对账，未通过不恢复付费入口。

本机合成恢复不证明生产RTO/RPO；必须实测目标备份、存储与服务恢复耗时，再制定承诺。本轮未生产操作。
