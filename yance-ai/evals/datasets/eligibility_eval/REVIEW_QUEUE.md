# eligibility_eval 专家复核队列

> 由 ACC-06 修复生成（2026-11-24）。本文件只列待办，**不代表任何案例已被复核**。

## 背景

`cases.jsonl` 中有 50 条 `real-*` 案例，由 AI 根据 8 份生产政策的公开条款起草，数据集卡片标注为 `review_status: unreviewed`。它们目前只能证明规则比较器的计算是对的，不能证明产品能从政策原文中正确抽取规则，更不能作为准确率依据。

原先 `evals/datasets/eligibility_real/` 下有同一批案例的一份旧草稿，其中 21 条与本数据集不一致（本数据集为修正后的版本），并且错误地标注为"人工标注、已复核"。该副本已在 ACC-06 中删除，历史内容可通过 git 查看。

## 复核要求（每条案例）

1. 打开 `input.rules[].source_text`，对照政策官方原文链接，确认条款原文、条号与现行有效版本一致。
2. 确认每条规则的 `fact_key`、`operator`、`expected` 与条款含义一致，包括单位（万元、%、年）和边界（≥ 还是 >）。
3. 确认 `ground_truth` 中逐条结论和 `overall_status` 符合条款；有多条申报路径的政策，必须把每条路径都建模出来。
4. 有任何改动都要提升数据集版本号，同步每条案例的 `dataset_version`，并重新计算 `case_sha256`。
5. 全部复核完成后，由复核人本人在 `dataset.json` 中把 `review_status` 改为 `reviewed`，并填写真实的 `reviewed_by` 和 `reviewed_at`。

## 待复核案例

| 状态 | case_id | 题目 | 期望结论 |
|---|---|---|---|
| ☐ 待复核 | `real-gq-pass-001` | 上海某AI软件企业（成立3年/科技人员30%/研发8%/高新收入75%/营收3000万）能否认定高企？ | `POTENTIALLY_ELIGIBLE` |
| ☐ 待复核 | `real-gq-fail-age-002` | 成立仅8个月的企业能否认定高企？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-gq-fail-staff-003` | 科技人员占比8%的企业能否认定高企？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-gq-fail-rd-004` | 营收3000万但研发占比4.2%的企业能否认定高企？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-gq-boundary-rd-005` | 营收3000万、研发占比恰为5%的企业（边界值）能否认定高企？ | `POTENTIALLY_ELIGIBLE` |
| ☐ 待复核 | `real-gq-tier-5000w-006` | 营收6000万企业适用的研发比例门槛是多少？达标4.5%能否通过？ | `POTENTIALLY_ELIGIBLE` |
| ☐ 待复核 | `real-gq-tier-2y-007` | 营收3亿企业研发占比4.8%能否认定高企（适用3%档）？ | `POTENTIALLY_ELIGIBLE` |
| ☐ 待复核 | `real-gq-fail-rev60-008` | 高新收入占比55%的企业能否认定高企？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-gq-insufficient-009` | 未提供研发费用占比数据的企业资格判断？ | `NEED_MORE_INFORMATION` |
| ☐ 待复核 | `real-gq-insufficient-staff-010` | 科技人员数与职工总数均未知的企业？ | `NEED_MORE_INFORMATION` |
| ☐ 待复核 | `real-gq-fail-multi-011` | 成立10个月且高新收入50%的双重不合格企业？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-gq-boundary-rev-012` | 营收恰好5000万的企业研发比例适用哪档？3.9%是否不合格？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-kj-pass-013` | 45人/年营收3000万/资产1500万的上海AI初创能否入库科技型中小企业？ | `POTENTIALLY_ELIGIBLE` |
| ☐ 待复核 | `real-kj-fail-emp-014` | 520人的企业能否入库科技型中小企业？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-kj-fail-rev-015` | 年营收2.4亿的企业能否入库？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-kj-boundary-emp-016` | 恰好500人的企业（边界值）能否入库？ | `POTENTIALLY_ELIGIBLE` |
| ☐ 待复核 | `real-kj-fail-assets-017` | 资产总额2.5亿的企业能否入库？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-kj-insufficient-018` | 未提供资产总额的企业？ | `NEED_MORE_INFORMATION` |
| ☐ 待复核 | `real-kj-fail-hk-019` | 香港注册的企业能否入库科技型中小企业？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-kj-fail-multi-020` | 600人且营收3亿的双超限企业？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-zj-pass-021` | 营收1.2亿/研发4%/省级专精特新有效期能否申报小巨人？ | `POTENTIALLY_ELIGIBLE` |
| ☐ 待复核 | `real-zj-pass-growth-022` | 营收6000万但近两年增速45%的企业能否申报？ | `POTENTIALLY_ELIGIBLE` |
| ☐ 待复核 | `real-zj-fail-no-zjtx-023` | 非省级专精特新企业能否直接申报小巨人？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-zj-fail-rev-024` | 营收4000万的企业（不满足任一营收路径）？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-zj-fail-rev-mid-025` | 营收6000万（第二条增速路径）但近两年增速仅15%能否申报小巨人？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-zj-fail-rd-026` | 研发占比2.5%的企业？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-zj-insufficient-rd-027` | 未提供研发占比数据？ | `NEED_MORE_INFORMATION` |
| ☐ 待复核 | `real-zj-insufficient-status-028` | 专精特新状态未知（有效期不明）？ | `NEED_MORE_INFORMATION` |
| ☐ 待复核 | `real-zj-boundary-rev-1y-029` | 营收恰好1亿（边界）+研发3%（边界）？ | `POTENTIALLY_ELIGIBLE` |
| ☐ 待复核 | `real-zj-fail-expired-030` | 省级专精特新已过期的企业？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-lg-pass-031` | 注册临港的人工智能企业（实质性运营）能否享受15%所得税？ | `POTENTIALLY_ELIGIBLE` |
| ☐ 待复核 | `real-lg-fail-district-032` | 注册在徐汇区的AI企业能否直接享受临港15%所得税？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-lg-fail-industry-033` | 临港注册的传统商贸企业能否享受重点产业所得税优惠？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-lg-fail-ops-034` | 注册临港但研发与人员都在市区的空壳企业？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-lg-pass-ic-035` | 临港集成电路企业实质运营能否享受？ | `POTENTIALLY_ELIGIBLE` |
| ☐ 待复核 | `real-lg-insufficient-industry-036` | 临港注册但行业未分类的企业？ | `NEED_MORE_INFORMATION` |
| ☐ 待复核 | `real-lg-fail-new-energy-037` | 临港新能源企业（不在重点产业目录）？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-lg-insufficient-ops-038` | 运营实体情况未申报的临港AI企业？ | `NEED_MORE_INFORMATION` |
| ☐ 待复核 | `real-fj-pass-039` | 软件企业有系统研发活动能否适用100%加计扣除？ | `POTENTIALLY_ELIGIBLE` |
| ☐ 待复核 | `real-fj-fail-restaurant-040` | 餐饮连锁企业能否适用加计扣除？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-fj-fail-retail-041` | 批发零售企业能否适用？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-fj-fail-real-estate-042` | 房地产开发企业能否适用？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-fj-insufficient-rd-043` | 行业合规但研发活动性质不明？ | `NEED_MORE_INFORMATION` |
| ☐ 待复核 | `real-fj-pass-ic-120-044` | 集成电路企业适用120%更高比例的判断（含普通加计规则）？ | `POTENTIALLY_ELIGIBLE` |
| ☐ 待复核 | `real-fj-fail-no-rd-045` | 无任何研发活动的企业？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-xh-pass-046` | 注册徐汇区实地办公的AI企业申报西岸AI高地政策？ | `POTENTIALLY_ELIGIBLE` |
| ☐ 待复核 | `real-xh-fail-047` | 注册浦东的企业申报徐汇区级政策？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-zjpark-pass-048` | 张江注册的生物医药企业申请园区扶持？ | `POTENTIALLY_ELIGIBLE` |
| ☐ 待复核 | `real-zjpark-fail-ind-049` | 张江注册的金融科技企业（非三大主导产业）？ | `NOT_ELIGIBLE` |
| ☐ 待复核 | `real-sh-ai-pass-050` | 上海注册的AI企业适用上海AI产业条例专项支持？ | `POTENTIALLY_ELIGIBLE` |
