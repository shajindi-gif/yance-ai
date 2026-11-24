# opportunity-20261118-03（含 03e 热修镜像）

## 目标
任意客户填完画像 → 好看可引用可下载 POLICY_REPORT；至少 3 个画像切片合成验收达标。

## 变更摘要
- 广东 geo / 制造主题补种；全国画像仅保留 national/未标省政策
- 剔除名册/招聘/决算等无行动噪声；无规则占比封顶 <15%
- 停用「行业关键词硬门槛」误种（避免 AND 误杀正例）；保留高企/专精特新/科技型中小/规模等可核实规则
- Ask 关闭；citation 门禁未放宽

## 三切片合成验收（无真扣款，fullchain 复跑）
| 切片 | 结果 | 缺规则 | 正例(verified) | PDF |
|---|---|---:|---:|---:|
| 上海+人工智能 | pass | 13.6% | 28 | `docs/releases/sample_pdfs/sample_shanghai_ai.pdf` |
| 广东+智能制造 | pass | 13.6% | 35 | `docs/releases/sample_pdfs/sample_guangdong_mfg.pdf` |
| 全国软件(province空) | pass | 10.0% | 8 | `docs/releases/sample_pdfs/sample_national_soft.pdf` |

生产版本标签：`opportunity-20261118-03e`（基于 `24486c9…` + matcher/rule_seeding 补丁）  
Ask=`false` · download SHA=frozen · 硬错配 0

## 网页切换（已执行候选 1）
- 保持网页 release `website-20261118-02`，**未**重建前端、**未**打开 Ask
- `release.json`：`api_application_version=opportunity-20261118-03e`
- 合成样例静态入口：https://yance.ai/samples/index.html （三份 PDF + 截图）
- 截图归档：`docs/releases/pdf_shots/`

## 仍劝退点
- 日期字段密度仍低（ruled 回填本轮 updated=0；dated_versions 105）
- Top 排序仍可能抬全国泛政策；有用性升权下一刀
- 行业硬规则需改回「适用对象句式」精确抽取后再启用
