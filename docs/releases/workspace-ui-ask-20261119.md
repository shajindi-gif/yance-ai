# workspace-ui-ask-20261119 交付对照

## 能力对照

| 能力 | 优化前 | 优化后 | 仍劝退点 |
|---|---|---|---|
| 问衍策 | 生产 `WORKSPACE_ASK_ENABLED=false`，首屏「尚未开放」 | 破冰文案+4 预设；开关可热启/回滚；reading 证据分级 | 未开开关时仍不可真实问答；日限额 100 |
| 工作台首屏 | 标题偏空、路径分散 | 「选企业·问一句·看机会」三路径 + Ask 主任务 | 无企业时仍需先建档（有意） |
| AppShell | 「证据工作台」重复噪声 | 品牌「衍策」+ 顶栏显示工作区名 | 次要导航仍多，后续可再收 |
| 机会列表 | 仅匹配% | 实效分 + 同城/窗口/规则/弱匹配降权标签 | 旧扫描无 `rank_features` 时标签较少 |
| 企业画像 | 单页长表 | 4 步分组、每步保存、省市联动、完成度缺口提示、一键发布 | 未接工商 API（合同外禁止） |
| 模型 | 文档分散 | `docs/workspace-ask-v1/llm-ops-checklist.md` | OpenAI/Claude 密钥可能存在但生产路由拒绝 |

## 截图路径（部署后补齐）

- 桌面：`docs/releases/shots/workspace-ask-desktop-20261119.png`
- 手机：`docs/releases/shots/workspace-ask-mobile-20261119.png`

## 激活 / 回滚

见 `docs/releases/workspace-ask-activate-20261119.md`。
