# 报告分享图 (Share Card) — 2026-11-24

## 范围

- 在 `/opportunities`（政策机会页）新增「生成分享图」入口。
- 纯前端实现：Canvas 2D 绘制 1080×1440 竖版图，无新增依赖，无后端/排名改动。
- 输出：下载 PNG、系统分享（Web Share，支持图片时）、复制分享文案。

## 隐私与措辞默认值

- 企业名称默认隐藏，仅在勾选「显示企业名称」后出现。
- 文案禁止：「符合」「可以申请」「可获得」「万元」「已通过」。
- 图片与文案均包含免责声明：仅供初步核对，资格以政府原文为准。
- 无可核对机会时，不生成假图，显示空状态文案。
- 被标记为 NOT_ELIGIBLE 或「弱匹配」的机会不进入亮点。

## 验证

- `node --experimental-strip-types --test tests/*.test.mjs`：18/18 通过（含 share-card 8 项）。
- `npx tsc --noEmit`：通过（清理 `.next` 生成类型缓存后）。
- `npx eslint` 变更文件：无报错。
- 视觉验证（CJK 换行、溢出、移动端宽度）**未完成**：本机 `next dev` 仅能加载 WASM 绑定，并出现 `EMFILE: too many open files` 导致路由无法响应。临时预览路由已删除。上线前需在可用环境中打开 `/opportunities` 人工核对一次分享图。

## 生产部署

- 网站 release：`website-20261124-share01`（基于线上 `website-20261119-ask01`，仅覆盖 4 个分享图文件，未同步其他有差异的文件）。
- 服务器构建：`npm run build` 成功，产物含 `生成分享图`。
- 激活：新增 systemd drop-in `zzzzzzzzzzzzz-website-20261124-share01.conf`，`/opt/yance/website` 指向新 release，`yance-website` 重启 active。
- 本机验证（服务器 127.0.0.1:3000）：`/`、`/dashboard`、`/opportunities`、`/reports` 均为 200；服务日志无报错。
- API 与采集器未改动。

## 回滚

```bash
sudo rm -f /etc/systemd/system/yance-website.service.d/zzzzzzzzzzzzz-website-20261124-share01.conf
sudo ln -sfn /opt/yance/releases/website-20261119-ask01/website /opt/yance/website
sudo systemctl daemon-reload && sudo systemctl restart yance-website
```

## 未验证 / 未包含

- 分享图视觉效果（CJK 换行、溢出、移动端）未在浏览器中核对；上线后需人工检查 `/opportunities` 页面的分享图。
- 公网入口未从外部网络验证。
- `/reports` 页的分享入口未做（后续项）。
- 采集器相关脏文件未纳入本次提交。

## 相关文件

- `website/lib/share-card.ts`
- `website/components/workspace/ReportShareCard.tsx`
- `website/components/workspace/ReportShareCard.module.css`
- `website/tests/share-card.test.mjs`
- `website/app/opportunities/page.tsx`
- `docs/prompts/report-share-card-20261124.md`
