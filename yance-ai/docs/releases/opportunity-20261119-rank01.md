# opportunity-20261119-rank01

有用性排序补丁：信度门禁不回退 + 效度 Top 可行动。

## 变更
- 新增 `app/services/report/ranking.py`：region/industry/actionability/window/evidence/enterprise/noise 可审计特征
- `matcher.py`：按 usefulness 重排；外省硬错配移出；宣传/规划强降权；同城多样性
- `pdf.py`：Top 表跳过强降权宣传填料（仍保留在主列表以维持正例池）
- Ask=false；不放宽 citation；不改价

## 三切片双门禁（合成无真扣款）
| 切片 | sellable∩useful | 缺规则 | 正例 | Top噪声 | Top 特征 |
|---|---|---:|---:|---:|---|
| 上海+AI | pass | 13.9% | 27 | 0% | 沪科委概念验证/伙伴计划/专精特新在前 |
| 广东+制造 | pass | 14.0% | 40 | 0% | 粤科技厅组织申报 / 脑机接口专项在前 |
| 全国软件 | pass | 10.0% | 8 | 0% | 专精特新小巨人/税收/创新积分在前 |

生产：`opportunity-20261119-rank01` · rev `a6d6db1…`（含后续 hotfix commits 至 website samples 刷新）  
回滚：`sudo bash /opt/yance/releases/opportunity-20261119-rank01/activate.sh rollback`（或切回 `opportunity-20261118-03e` 镜像）

## 网站
- `https://yance.ai/samples/index.html` 已刷新三份 PDF + 截图
- `release.json`：`api_application_version=opportunity-20261119-rank01`

## 仍劝退点
- 全国切片 Top 仍可能出现「再生资源」等弱相关意见（非宣传噪声，但行业贴合一般）
- 日期密度仍低；有用性下一刀可做窗口字段回填密度
