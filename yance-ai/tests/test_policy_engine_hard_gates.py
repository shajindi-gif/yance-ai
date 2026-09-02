from app.services.policy_engine.deterministic import _is_blocking, final_gate


def test_safety_environment_and_credit_requirements_are_blocking():
    assert _is_blocking("近三年未发生重大安全事故") is True
    assert _is_blocking("企业不得存在环境违法记录") is True
    assert _is_blocking("企业社会信用记录良好") is True


def test_advisory_awards_remain_non_blocking():
    assert _is_blocking("获得创新创业大赛奖励可加分") is False


def test_failed_blocking_criterion_cannot_be_eligible():
    assert final_gate(["PASS", "FAIL"], [True, True]) == "NOT_ELIGIBLE"
    assert final_gate(["PASS", "INSUFFICIENT"], [True, True]) == "INSUFFICIENT_INFO"
