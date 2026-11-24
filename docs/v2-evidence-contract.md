# 第一批证据工作台数据契约 v1

复用现有Application、ApplicationRequirement、EligibilityResult、Evidence、CompanyProfileVersion和ApplicationArtifact。本批无数据库迁移。

## 项目详情 GET /api/v1/applications/{id}

保持原响应字段，新增evidence_matrix：status（保留原资格枚举）、rows、context_issues、missing_information。每行包含原规则ID/name/fact_key/operator/expected/actual/is_hard_gate/status，并附profile_version_id、fact_source、policy_evidence。policy_evidence仅关联同rule_id的现有证据，包含id/quote/article/source_url/verified；无对应证据返回空数组，不拿相邻条款充数。企业事实显示已发布画像来源和企业自述限制，不冒充第三方证明。

criterion状态PASS/FAIL/MISSING/UNVERIFIED_SOURCE/UNSUPPORTED在页面分别显示条件满足/条件不满足/证据不足/原文待核验/需人工复核。资格整体状态、原文逐字校验、人工批准和获批结果含义不同。context_issues来自当前政策时效/地域/版本、当前企业画像版本及规则/事实/证据契约检查。

新生成的source_snapshot增加workspace_fingerprint（workspace-inputs-v1规范序列化SHA256）。覆盖项目标题/表单/截止日、画像快照、政策版本与内容/时效、规则、资格结果、要求状态、文件内容摘要/摄取状态和逐条引用；记录排序稳定，排除流程状态与易变时间戳。重新生成指纹不能洗白旧资格：检查规则集合、值/算子/硬条件、当前企业事实和硬条件原文与原判定是否一致。

详情generated各项新增source_state={current,reasons}。来源变化或内容校验失败返回current=false；不篡改历史批准记录。新批准、项目批准/提交和批准稿下载在服务端重验。旧稿无指纹需要重新生成/复核；有权限的未批准工作稿继续按原工作稿路径导出。历史批准稿不静默当成当前版本交付。

## POST /api/v1/applications/{id}/evidence-tasks

无请求体。仅owner/admin/member且项目处于draft/preparing/revision_requested可写；viewer403、跨租户404、错误阶段409。按矩阵中非PASS且有rule_id的条件创建现有ApplicationRequirement，category=evidence、status=missing，source_json存gap_rule_id和画像版本ID。父项目行锁串行化，已有同规则待办不重复创建；响应created_requirement_ids。空数组表示本次没有新增，不等于缺口已经解决。

这是内部补证清单，不是自动外发催办或后台自主任务。补资料后需重新确认画像/扫描资格；原机会已过时可从新机会建立新项目，保留原项目证据历史。

## 冲突及兼容

编辑、生成、材料关联、材料状态和审阅等修改在检查最新版本前锁定父项目。并发编辑同一工作稿只允许一个新版本，另一个409。来源改变后草稿可保留；批准稿导出409，批准/提交409。前端缺矩阵字段时显示版本未支持，不伪造结果。

本契约不引入新资格引擎，不为SSO、实时同文编辑、供应商连接或资源目录提供假接口。
