# 整改复测

沿用验收环境的Python3.12、Node26、Next16.4.3和PostgreSQL18。新建yance_remediation_final_test，仅合成企业及测试夹具，供应商凭据为空、邮件短信关闭、模型mock。API127.0.0.1:8047，网页127.0.0.1:3047。没有生产写入或部署。

- 全套 `pytest tests -o addopts='' -q --junitxml=...`：459 passed，34.29秒。
- `pytest tests/test_runtime_version.py tests/policy_collection/test_evidence_search_api.py tests/policy_collection/test_keyword_search_db.py -o addopts='' -q`：12 passed。包含新增运行版本用例，其余与全套重叠。
- `npm run lint`、`npm run typecheck`、`npm run test:unit`、`API_PROXY_TARGET=http://127.0.0.1:8047 NEXT_PUBLIC_API_URL=/api/v1 npm run build`：通过。
- 新增 PolicyEvidenceSearch 的请求序列、显式错误及安全链接按React技能复核。API层新增跨租户计数、版本原文授权和未来生效排除回归。
- Playwright在后端测试结束后创建新夹具，提供YANCE_V2_FIXTURE、YANCE_ROLES_FIXTURE、YANCE_CHECKOUT_FIXTURE，使用新PLAYWRIGHT_OUTPUT_DIR。policy-evidence、evidence-workspace、login-payment-ux、frontend-redesign、workspace-roles、remediation六组共19 passed，21.8秒。
- 首次新增用例夹具漏填tenant.slug导致2失败，补齐必填字段后完整回归通过；业务断言保持。
- 两个浏览器批次同时使用默认输出目录导致ENOENT，以及后端政策测试清理删除网页夹具，首次浏览器结果保留在browser.log和browser-final.log。最终以browser-verified.log为准；后端与前端夹具必须按顺序运行。
- 先验收时手机Lighthouse性能50和95，LCP7.82秒和2.84秒。整改后首个样本97，LCP约2.5秒。模拟设备、网络及版本均存于lighthouse-mobile.json，不推算线上INP/RUM。基线样本波动大，不能将差值全归因于代码。
- Firefox现有安装仍报Could not find profile folder，换TMPDIR未解决。临时目录重新安装结果及复测单列在firefox-install.log和firefox-clean.log。

最后原文高亮与旧版本警示补充后，构建/类型/静态复测及单项浏览器结果另见build-verified.log、browser-source-final.log。没有把未运行的渠道/业务样本验证标通过。PG16生产恢复、原文备份恢复、园区撤销、实际税票和真实用户任务研究继续待验。

Firefox临时目录重新下载完成后，firefox-clean.log仍为配置目录不可用导致启动失败，1 failed。WebKit此前样本通过，此处不将其计作Firefox通过。最终原文高亮单项1 passed（1.2秒）。
