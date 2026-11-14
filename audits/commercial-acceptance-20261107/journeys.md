# 客户旅程实测

以下均为当前构建、Chromium、本机API8047、隔离库的合成资料，外部请求在相关网页用例中拦截。邮件短信关闭、模型mock、支付凭据为空。既有真实政策生产数据仅聚合读取。

|旅程|实际覆盖|结果与失败恢复|证据|
|---|---|---|---|
|首次到访与入口|首页、价格、双登录入口、手机视口、标签、焦点与未保存提醒|通过；真实邮件短信送达未执行|browser.log、workspace.log、local-*.png|
|企业资料到项目|后端core_workflow对资料、画像发布、机会、材料做持久化流程|后端通过；浏览器空账户到全部节点的连续单一旅程未完整录制|backend.xml、workspace.log|
|资格与补证|真实API资格矩阵、条款标识、持久化补证任务，桌面和手机|通过，矩阵用例3.7秒为机器操作墙钟|journey.log|
|材料与协作|生成工作稿、版本对比、编辑、旧建议拒绝、评论、viewer只读|通过；真实多客户授权园区范围与撤销未执行|workspace.log|
|客户复核与导出|客户复核source-bound版本，下载DOCX|通过，合成证据；逐页中文字体/PDF打印版人工验收未完成|workspace.log|
|购买及恢复|服务端价格变化要求二次确认、刷新恢复原订单、供应商不可用仍保留订单|通过，真实API续付用例1.1秒；付款确认UI使用合同响应|journey.log|
|结算与开票|后端结算验签字段校验、重放不重复权益，发票申请、运营上传、下载及拒绝|后端通过，文件为测试夹具；渠道真实到账、正式税票效力未验证|backend.xml、tests/test_invoice_flow.py|
|反馈|真实API提交销售请求、私有入库与状态读取|通过，0.5秒机器操作墙钟|remediation-complete.log|

截图workspace-1440.png、workspace-390.png保存合成项目详情。local-*与production-*分别为本地和生产公开页截图。

Firefox失败发生于浏览器进程启动，错误为Could not find profile folder，页面未打开，因此无可用失败页面截图。失败栈见browser.log。WebKit公开页1440/768/390样本通过。原生Safari/Edge及真实触屏未测试。
