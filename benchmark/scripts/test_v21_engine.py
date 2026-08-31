#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V2.1 引擎冒烟测试（确定性 + Mock-E2E，无需联网/API Key）
验证：
  U1 _detect_field 对高企 32 号文「科技人员占企业职工总数比例不低于10%」→ tech_staff_ratio（修复前误判 employee_count）
  U2 evaluate_deterministic 对 tech_staff_ratio / employee_count / rd_ratio 分档 / 收入区间 判定正确
  U3 final_gate 程序聚合正确
  U4 _loads_json 能剥离 ```json 代码块
  U5 evaluate_policy 端到端（Mock LLM）跑通，且 deterministic 覆盖错误 LLM 判定
"""
import asyncio
import os
import sys
import json
from types import SimpleNamespace

# —— 仅注入 env（不打印任何 Key 值）——
ENV_PROD = "/Users/shajindi/Desktop/yance-backup/env.prod"
for line in open(ENV_PROD, encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

YANCE_AI = "/Users/shajindi/Desktop/yance-backup/yance/yance-ai"
sys.path.insert(0, YANCE_AI)
os.chdir(YANCE_AI)

from app.services.policy_engine.evaluator import evaluate_policy, _loads_json  # noqa: E402
from app.services.policy_engine.deterministic import (  # noqa: E402
    normalize_facts, normalize_criteria, evaluate_deterministic, final_gate, _detect_field,
)

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")


# ── U1: 字段识别优先级 ──
print("== U1 field detection ==")
cond_ratio = "科技人员占企业职工总数比例不低于10%"
check("tech_staff_ratio 优先于 employee_count",
      _detect_field(cond_ratio) == "tech_staff_ratio",
      f"got={_detect_field(cond_ratio)}")
check("职工总数条件仍识别为 employee_count",
      _detect_field("职工总数不超过500人") == "employee_count",
      f"got={_detect_field('职工总数不超过500人')}")
check("研发占比条件识别为 rd_ratio_3y",
      _detect_field("近三个会计年度研究开发费用总额占销售收入总额的比例不低于5%") == "rd_ratio_3y")

# ── U2: deterministic 数值判定 ──
print("== U2 deterministic evaluation ==")
prof = {
    "tech_staff": 80, "employee_count": 500,
    "revenue_last_year_wan": 8000, "rd_expense_last_year_wan": 400,
    "hitech_product_revenue_ratio": 0.65,
}
facts = normalize_facts(prof)
check("tech_staff_ratio 派生 = 0.16", abs((facts["tech_staff_ratio"] or 0) - 0.16) < 1e-6,
      f"got={facts['tech_staff_ratio']}")

cn_ratio = {"criterion": cond_ratio, "policy_quote": cond_ratio, "field": "tech_staff_ratio",
            "operator": ">=", "value": 0.10, "unit": "ratio", "kind": "numeric"}
r = evaluate_deterministic(cn_ratio, facts)
check("tech_staff_ratio 0.16>=0.10 → PASS", r is not None and r["result"] == "PASS", f"got={r}")

cn_emp = {"criterion": "职工总数不超过500人", "policy_quote": "", "field": "employee_count",
          "operator": "<=", "value": 500, "unit": "人", "kind": "numeric"}
r2 = evaluate_deterministic(cn_emp, facts)
check("employee_count 500<=500 → PASS", r2 is not None and r2["result"] == "PASS", f"got={r2}")

# rd_ratio 分档：收入 8000万 → 4% 档；last year 400/8000=5% PASS
cn_rd = {"criterion": "上年度研发费用总额占销售收入不低于4%", "policy_quote": "",
         "field": "rd_ratio_last_year", "operator": ">=", "value": 0.04, "unit": "ratio", "kind": "numeric"}
r3 = evaluate_deterministic(cn_rd, facts)
check("rd_ratio_last_year 0.05>=0.04 → PASS", r3 is not None and r3["result"] == "PASS", f"got={r3}")

# 反例：tech_staff_ratio 不足
prof_bad = dict(prof); prof_bad["tech_staff"] = 30  # 30/500 = 0.06 < 0.10
facts_bad = normalize_facts(prof_bad)
r_bad = evaluate_deterministic(cn_ratio, facts_bad)
check("tech_staff_ratio 0.06>=0.10 → FAIL", r_bad is not None and r_bad["result"] == "FAIL", f"got={r_bad}")

# ── U3: final_gate 聚合 ──
print("== U3 final gate ==")
check("全PASS→ELIGIBLE", final_gate(["PASS", "PASS"]) == "ELIGIBLE")
check("任一FAIL→NOT_ELIGIBLE", final_gate(["PASS", "FAIL", "PASS"]) == "NOT_ELIGIBLE")
check("无FAIL有INSUFF→INSUFFICIENT_INFO", final_gate(["PASS", "INSUFFICIENT"]) == "INSUFFICIENT_INFO")
check("空→INSUFFICIENT_INFO", final_gate([]) == "INSUFFICIENT_INFO")

# ── U4: _loads_json 鲁棒解析 ──
print("== U4 _loads_json ==")
block = "```json\n{\"criteria\": [{\"criterion\": \"x\", \"result\": \"PASS\"}]}\n```"
try:
    p = _loads_json(block)
    check("_loads_json 剥离 ```json 代码块", isinstance(p, dict) and "criteria" in p, f"got={p}")
except Exception as e:
    check("_loads_json 剥离 ```json 代码块", False, str(e))

noise = "好的，结果如下：\n{\"criteria\": []}\n以上为判定。"
try:
    p2 = _loads_json(noise)
    check("_loads_json 截取首个 {...}", isinstance(p2, dict), f"got={p2}")
except Exception as e:
    check("_loads_json 截取首个 {...}", False, str(e))


# ── U5: evaluate_policy 端到端（Mock LLM）──
print("== U5 end-to-end (mock LLM) ==")


class FakeLLM:
    """extract 返回固定条件；evaluate 故意全 INSUFFICIENT，验证 deterministic 覆盖。"""
    async def complete(self, request, provider=None):
        content = request.messages[-1]["content"]
        if "提取所有硬性申报条件" in content:
            payload = {"criteria": [
                {"criterion": "科技人员占企业职工总数比例不低于10%", "policy_quote": "科技人员占企业职工总数比例不低于10%"},
                {"criterion": "职工总数不超过500人", "policy_quote": "职工总数不超过500人"},
                {"criterion": "上年度高新技术产品收入占比不低于60%", "policy_quote": "上年度高新技术产品收入占比不低于60%"},
            ]}
        else:
            # 故意全部 INSUFFICIENT —— 模拟 LLM 保守/误判，验证引擎以 deterministic 为准
            payload = {"criteria": [], "summary": "fake conservative"}
        return SimpleNamespace(content=json.dumps(payload),
                               usage={"prompt_tokens": 10, "completion_tokens": 10, "prompt_cache_hit_tokens": 0})


import app.services.policy_engine.evaluator as EV
EV._llm = FakeLLM()

POLICY = ("《高新技术企业认定管理办法》（国科发火〔2016〕32号，科技部）\n"
          "【第十一条】科技人员占企业职工总数比例不低于10%；职工总数不超过500人；"
          "上年度高新技术产品收入占比不低于60%。")

prof_ok = {
    "company_name": "测试科技A", "tech_staff": 80, "employee_count": 500,
    "hitech_product_revenue_ratio": 0.65,
}
prof_bad = {
    "company_name": "测试科技B", "tech_staff": 30, "employee_count": 600,
    "hitech_product_revenue_ratio": 0.65,
}


async def run_e2e(prof):
    res = await evaluate_policy(
        policy_id="HITECH32", policy_title="高新技术企业认定", policy_content=POLICY,
        policy_level="国家级", company_name=prof.get("company_name"),
        company_profile=prof, provider="deepseek",
    )
    return res


res_ok = asyncio.run(run_e2e(prof_ok))
check("E2E-PASS: 满足全部→ELIGIBLE", res_ok.overall_result.value == "ELIGIBLE",
      f"got={res_ok.overall_result.value} crit={[c.criterion+':'+c.result.value for c in res_ok.criteria]}")
det_count = res_ok.model_metadata.get("deterministic_evaluated", 0)
check("E2E-PASS: 至少有 1 条 deterministic 判定", det_count >= 1, f"got={det_count}")

res_bad = asyncio.run(run_e2e(prof_bad))
check("E2E-FAIL: 科技人员占比不足→NOT_ELIGIBLE（deterministic 覆盖 LLM INSUFFICIENT）",
      res_bad.overall_result.value == "NOT_ELIGIBLE",
      f"got={res_bad.overall_result.value} crit={[c.criterion+':'+c.result.value for c in res_bad.criteria]}")

print(f"\n==== RESULT: {PASS} passed, {FAIL} failed ====")
sys.exit(1 if FAIL else 0)
