# 执行提示词：政策机会报告分享图（2026-11-24）

## 目标

用户完成政策扫描、看到报告结果后，可以一键生成一张适合社交网络分享的竖版图片（1080×1440 PNG），并复制一段分享文案。

## 约束（不可违反）

1. 分享图不得出现「符合 / 可以申请 / 可获得 X 万元」等资格或金额结论；只能用「可优先核对」「匹配记录」等中性措辞。
2. 默认隐藏企业名称（用户可手动勾选显示）；不展示统一信用代码、画像明细、手机号等。
3. 每张图必须带免责声明：匹配记录仅作初筛，资格与金额以原文和主管部门为准。
4. 无数据时禁止生成「假图」；按钮在无机会时禁用。
5. 不新增第三方渲染依赖；在浏览器用 Canvas 绘制，数据不经第三方。
6. 不改后端接口、不改排序与资格引擎。

## 交付物

- `website/lib/share-card.ts`：纯函数模型（排序取 TOP3、统计、文案）+ Canvas 绘制。
- `website/components/workspace/ReportShareCard.tsx` 与样式：预览、下载 PNG、系统分享、复制文案。
- `website/app/opportunities/page.tsx`：在报告结果工具条接入入口。
- `website/tests/share-card.test.mjs`：模型单测（排序、隐私、禁用词、空态）。
- 本文件 + 验证结果写入 `docs/releases/share-card-20261124.md`。

## 验收

1. `node --experimental-strip-types --test tests/*.test.mjs` 全绿。
2. `npm run typecheck`、`npx eslint` 针对改动文件无错误。
3. 浏览器内绘制的图片截图存在，中文不乱码、文字不溢出。
4. 默认不显示企业名；勾选后显示。
