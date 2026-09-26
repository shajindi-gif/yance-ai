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
