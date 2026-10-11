# 支付宝接入说明（yance.ai）

更新：2026-09-27。当前实现：`yance-ai/app/api/routes/payments.py`（电脑网站支付 page.pay）。

## 生产配置（.env.prod，值从 fengyuxueye 同商户应用复用）

- `ALIPAY_APP_ID` / `ALIPAY_PRIVATE_KEY` / `ALIPAY_PUBLIC_KEY`：真实值（私钥为 PKCS#8 单行 base64）
- `ALIPAY_NOTIFY_URL=https://yance.ai/api/v1/payments/alipay/notify`（主域 /api 经 next.config rewrite 代理到 API）
- `ALIPAY_RETURN_URL=https://yance.ai/success`
- `ALIPAY_SANDBOX=false`

## 实测踩坑（每一项都经过生产网关二分实验验证，勿回退）

1. **签名原文必须包含 sign_type**：过滤条件只能排除 `sign`。排除 sign_type 会报 invalid-signature。
2. **biz_content 必须紧凑序列化**：`json.dumps(..., separators=(",", ":"))`。默认 `", "`/`": "` 分隔符会导致网关重序列化后与签名原文不一致。
3. **URL 必须严格百分号编码**：`urlencode(params, quote_via=quote, safe='')`。未编码的 `/`（notify_url/return_url 中）会导致网关验签失败；空格编码为 `+` 也不可靠，用 %20。
4. **私钥格式**：支付宝密钥工具产出 PKCS#8 单行 base64，`_load_rsa_private_key` 会自动识别 PKCS#8/PKCS#1/PEM。
5. **占位符检测**：`REPLACE_WITH_*` 之类占位值会返回 503「未配置」而非 500。
6. **回调路由**：支付宝回调必须能到达 FastAPI。主域 `/api/*` 由 `website/next.config.js` 的 rewrite 代理到 `API_PROXY_TARGET`（默认 https://api.yance.ai）。

## 与 fengyuxueye 共用商户应用的说明

当前与《风雨学业求职路》共用同一支付宝商户应用（收款主体：上海衍策引擎人工智能科技有限公司，收银台显示"衍策引擎AI"）。技术上按请求级 notify_url 回调，互不影响。注意：为 yance.ai 单独申请支付宝应用需要 ICP 备案，届时应迁移独立应用与密钥。

## 未验证/待办

- 真实付款→回调→结算→权益发放全链路（待授权后执行沙箱或小额真实订单验收）
- 退款：无程序化退款接口，人工在支付宝商户平台操作后需手动同步订单状态（见 terms 退款条款）
- 商户收银台风控：无浏览器特征的服务端探测（curl）会报 FISHING_RISK，属预期；真实浏览器打开为正常收银台（已实测）

---

## 微信支付 APIv3（Native 扫码）— 2026-10-11 接通

实现：`app/services/payments/wechat.py`（纯 pycryptodome，无新依赖），移植自 fengyuxueye 生产验证的 wechat-pay.ts。

### 配置（.env.prod）
- `WXPAY_MODE=direct`（直连商户）
- `WXPAY_MCH_ID=1117431351`、`WXPAY_APP_ID`、`WXPAY_SERIAL_NO`
- `WXPAY_PRIVATE_KEY`：商户 API 私钥，**裸单行 base64（PKCS#8）**，与支付宝私钥同存法（无引号无 PEM 头）
- `WXPAY_APIV3_KEY`：32 位
- `WXPAY_PUBKEY_ID` + `WXPAY_PUBKEY`：微信支付公钥模式（新商户无平台证书，回调验签用固定公钥；serial 必须等于 PUB_KEY_ID）
- `WXPAY_NOTIFY_URL=https://api.yance.ai/api/v1/payments/wechat/notify`（直连后端，不经前端 rewrite）

### 端点
- `POST /payments/wechat/native?order_id=` → 返回 `code_url`（前端用 api.qrserver.com 渲染二维码）
- `POST /payments/wechat/notify` → 验签(公钥模式)+AES-256-GCM 解密+幂等结算（复用 settle_payment）
- `POST /payments/wechat/query?order_id=` → 主动查单补偿（回调丢失时前端轮询触发）

### 已验证（生产）
- Native 下单返回真实 `weixin://wxpay/bizpayurl?pr=...`（微信网关接受签名）✓
- 主动查单返回 `NOTPAY`（未支付正确状态）✓
- notify 无签名 → `{"code":"FAIL"}` 不崩溃 ✓
- checkout 页微信 tab → 二维码 → 轮询 UI 全链路（Playwright 实测）✓
- out_trade_no 复用 order_no（稳定，支持重扫与查单）；金额服务端按分计算

### 待办
- 真实扫码付款 → 回调到达 → 订单 paid → Entitlement 发放（待用户授权一笔小额实测）
- 退款：无程序化退款 API，人工在微信商户平台操作

### 关键坑（勿回退）
1. 请求头必须带 `Accept-Language: zh-CN,zh;q=0.9`，否则网关 406
2. 验签走微信支付公钥模式（serial==PUB_KEY_ID），平台证书下载对新商户 404 是预期
3. PKCS#8 私钥检测用 `ADANBgkqhkiG9w0BAQEF` 标记（长度无关），不能用写死的 `MIIEvQ` 前缀（真实密钥有 `MIIEvg`）
4. AES-GCM 解密：tag 拼在密文尾部（末 16 字节），AAD 通过 `cipher.update(associated_data)` 传入
