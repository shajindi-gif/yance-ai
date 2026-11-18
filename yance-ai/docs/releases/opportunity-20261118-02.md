# opportunity-20261118-02

## 目标
上海人工智能企业 POLICY_REPORT：缺结构化规则占比 <15%，正例≥8 且均有 verified 引用，PDF 可下载且与 frozen SHA 一致。

## 变更
- 检索：keyword/trigram 融合后强制 `applicable_region_clauses`，剔除外省噪声
- 匹配：外省非全国政策移出主列表；无硬规则降权；有规则优先，无规则占比封顶约 12%
- 日期：可核实回填；缺日期改为 advisory，不单独误杀正例
- 规则：上海/全国主题补种；模板扩展（中小企业等），仍要求 version+chunk exact-span

## 生产验收（合成租户，无真扣款）
- 版本：`opportunity-20261118-02` / `92256b570b2aa8369dcacdca8afc66dcc78a3902`
- scan_id：`3359e3e7-102c-4c99-b518-e0bebf0d0fc1`
- deliverable_id：`137c9613-ecd5-456b-bb21-97ad4ae25b64`
- 机会：34（POTENTIALLY_ELIGIBLE 26 / NEED_MORE 8）
- missing_structured_rule_ratio：8.8%
- positive_with_verified_evidence：26/26
- citation_coverage：91.2%；ungrounded/fabricated：0
- download_matches_frozen：true；pdf_bytes：532301
- release_gate_passed：true

## 回滚
`sudo bash /opt/yance/releases/opportunity-20261118-02/activate.sh rollback`

## 未混入
Ask / collector 实验改动仍留在脏工作区，未进入本 release。
