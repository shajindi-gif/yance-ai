# Release 流程

1. Issue 与 PRD 明确验收和版本。
2. 从 `main` 创建短分支，PR 必须链接 Issue。
3. CI 全绿，至少一人复核高风险变更；数据库迁移必须写回滚/恢复方案。
4. 合并后更新 `CHANGELOG.md` 和 `VERSION`，创建 `vX.Y.Z` 标签。
5. 先 Staging 验收；生产发布前创建 RDS 手动快照并记录当前 commit。
6. 生产 Environment 人工批准，以不可变 Git tag/SHA 发布。
7. 执行 `上线验收清单.md`，失败则按 `明日部署手册.md` 回滚。
8. GitHub Release 附：功能、已知风险、迁移、验证证据、回滚点。

