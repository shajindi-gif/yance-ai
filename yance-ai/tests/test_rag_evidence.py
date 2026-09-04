from app.services.policies.eligibility import _evaluate, exact_quote_span
from app.services.policies.ingestion import chunk_policy_text, clean_policy_text
from app.services.policies.retrieval import _lexical_score, _tokens


def test_policy_chunks_preserve_exact_source_spans():
    source = "第一条 申报企业应在上海市注册。\n第二条 研发费用占比应不低于4%。\n" + ("补充说明。" * 220)
    cleaned = clean_policy_text(source)
    chunks = chunk_policy_text(cleaned)

    assert len(chunks) >= 2
    assert "".join(text for _, _, text, _ in chunks) == cleaned
    for start, end, text, _article in chunks:
        assert cleaned[start:end] == text
        assert len(text) <= 900


def test_exact_quote_rejects_numeric_substring_collision():
    assert exact_quote_span("研发费用占比应不低于140%。", "40%") is None
    assert exact_quote_span("研发费用占比应不低于40%。", "40%") == (10, 13)


def test_typed_rule_operators_are_deterministic():
    assert _evaluate("上海市", "eq", "上海市") is True
    assert _evaluate("小型", "in", ["小型", "微型"]) is True
    assert _evaluate(["软件著作权 3 项"], "contains", "软件著作权") is True
    assert _evaluate(4.5, "gte", 4) is True
    assert _evaluate(None, "exists", None) is False


def test_lexical_retrieval_scores_relevant_policy_higher():
    query = _tokens("上海 人工智能 研发补贴")
    relevant = _lexical_score(query, "上海市人工智能企业研发补贴申报通知")
    unrelated = _lexical_score(query, "农业机械购置与粮食生产通知")
    assert relevant > unrelated
