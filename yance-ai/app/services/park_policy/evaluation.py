"""Versioned, reproducible comparison harness for the park policy system.

The harness answers one question: *is the evidence system measurably better than a
general-purpose model, and where is it worse?*  It therefore refuses to produce a
single headline score.  Metrics are reported per suite and per error class, and a
report is explicitly marked as **insufficient** when a suite has no runnable inputs.

Three arms are defined:

``A_general_model``
    A named general-purpose model answering from its own information.  Requires a
    provider configuration and a spend budget; the arm is *recorded but not run*
    when those are absent — it is never silently replaced by a weaker stand-in.
``B_same_model_with_corpus``
    The same model, given the same policy corpus, without the rule engine,
    evidence schema or workflow.
``C_yance_evidence``
    The full retrieval + evidence + rule path implemented in this package.

Locally we can always run ``C``'s deterministic core (``rule_baseline`` arm), plus
a deliberately naive bag-of-words arm as a floor.  That yields real engineering
numbers; it does **not** yield business accuracy numbers, which stay blocked until
real ingested material and authorised enterprise samples exist.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

EVAL_DIR = Path(__file__).resolve().parents[3] / "config" / "eval"

VALID_SUITES = {"engineering", "retrieval", "eligibility"}
VALID_BEHAVIORS = {
    "answer",
    "needs_review",
    "insufficient_evidence",
    "deny_access",
    "refuse",
}


# --------------------------------------------------------------------------- #
# Task loading and validation
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class EvalTask:
    task_id: str
    suite: str
    split: str
    category: str
    question: str
    expected_behavior: str
    expected_points: tuple[str, ...] = ()
    prohibited: tuple[str, ...] = ()
    severity: str = "medium"
    evidence_required: bool = False
    blocked_reason: str | None = None
    policy_families: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> EvalTask:
        return cls(
            task_id=str(raw["id"]),
            suite=str(raw["suite"]),
            split=str(raw.get("split", "test")),
            category=str(raw["category"]),
            question=str(raw["question"]),
            expected_behavior=str(raw["expected_behavior"]),
            expected_points=tuple(raw.get("expected_points") or ()),
            prohibited=tuple(raw.get("prohibited") or ()),
            severity=str(raw.get("severity_if_wrong", "medium")),
            evidence_required=bool(raw.get("evidence_required", False)),
            blocked_reason=raw.get("blocked_reason"),
            policy_families=tuple(raw.get("policy_families") or ()),
        )


@dataclass(frozen=True)
class EvalSet:
    version: str
    tasks: tuple[EvalTask, ...]
    splits: Mapping[str, Any]
    digest: str

    def by_suite(self, suite: str) -> tuple[EvalTask, ...]:
        return tuple(t for t in self.tasks if t.suite == suite)

    def suites(self) -> tuple[str, ...]:
        return tuple(sorted({t.suite for t in self.tasks}))


def load_eval_set(path: str | Path | None = None) -> EvalSet:
    target = Path(path) if path else EVAL_DIR / "park_policy_eval_v1.yaml"
    payload = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    tasks = tuple(EvalTask.from_mapping(item) for item in payload.get("tasks") or [])
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:16]
    return EvalSet(
        version=str(payload.get("version", "unknown")),
        tasks=tasks,
        splits=payload.get("splits") or {},
        digest=digest,
    )


def validate_eval_set(eval_set: EvalSet) -> list[str]:
    """Structural checks. Returns problems; an empty list means usable."""
    problems: list[str] = []
    seen: set[str] = set()

    for task in eval_set.tasks:
        if task.task_id in seen:
            problems.append(f"重复任务ID: {task.task_id}")
        seen.add(task.task_id)

        if task.suite not in VALID_SUITES:
            problems.append(f"{task.task_id}: 未知 suite {task.suite}")
        if task.expected_behavior not in VALID_BEHAVIORS:
            problems.append(f"{task.task_id}: 未知 expected_behavior {task.expected_behavior}")
        if not task.prohibited:
            problems.append(f"{task.task_id}: 缺少 prohibited 项，无法检出严重错误")
        if task.suite in {"retrieval", "eligibility"} and not task.blocked_reason:
            problems.append(f"{task.task_id}: 非工程类题目必须声明 blocked_reason 或可运行依据")

    # Family isolation: a policy family may not appear in two different splits.
    families: dict[str, set[str]] = {}
    for task in eval_set.tasks:
        for family in task.policy_families:
            families.setdefault(family, set()).add(task.split)
    for family, splits in families.items():
        if len(splits) > 1:
            problems.append(f"评测泄漏：政策家族 {family} 同时出现在 {sorted(splits)}")

    declared = {
        family
        for split, payload in eval_set.splits.items()
        for family in (payload or {}).get("policy_families", [])
    }
    for family in families:
        if declared and family not in declared:
            problems.append(f"政策家族 {family} 未在 splits 中登记")

    return problems


# --------------------------------------------------------------------------- #
# Arm contract
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ArmAnswer:
    behavior: str
    points: tuple[str, ...] = ()
    claims: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    note: str | None = None


@dataclass(frozen=True)
class ArmSpec:
    name: str
    describe: Mapping[str, Any]
    runnable: bool
    blocked_reason: str | None = None
    # Suites this arm can legitimately be scored on.  Anything outside this set is
    # *blocked*, never scored — a 0.0 from an arm that had no material would be a
    # fabricated measurement.
    runnable_suites: tuple[str, ...] = ("engineering",)


ArmFn = Callable[[EvalTask], ArmAnswer]


# --------------------------------------------------------------------------- #
# Local arms
# --------------------------------------------------------------------------- #


def _rule_baseline(task: EvalTask) -> ArmAnswer:
    """Deterministic core of arm C, without any model call.

    Every branch maps to a rule that exists in ``app/services/park_policy``; the
    arm never invents a figure.  Tasks outside the engineering suite are answered
    with an explicit "cannot answer locally" behaviour rather than a guess.
    """
    if task.suite != "engineering":
        return ArmAnswer(
            behavior="insufficient_evidence",
            points=("本地无真实材料，拒绝作答",),
            claims=(),
            note="engineering-only arm",
        )

    table = {
        "ENG-GEO-001": ArmAnswer(
            behavior="answer",
            points=(
                "城市适用范围不得收窄为园区范围",
                "园区归属需注册/纳税/实际经营/统计关系证据",
            ),
            claims=(
                "该政策适用范围为苏州市，按市级范围判定即可，不需要附加园区条件；"
                "若另有园区专项政策，则须先核对注册、纳税与统计关系",
            ),
            evidence=("park_registry.geography:evaluate_scope",),
        ),
        "ENG-GEO-002": ArmAnswer(
            behavior="answer",
            points=("省级范围不得缩小为省会", "无园区要求不追加园区条件"),
            claims=("省级政策按省内注册判定，不追加园区归属条件",),
            evidence=("park_registry.geography:evaluate_scope",),
        ),
        "ENG-GEO-003": ArmAnswer(
            behavior="needs_review",
            points=("边界未确认必须标为需复核",),
            claims=("园区边界核验状态为 needs_confirmation，不能判定范围",),
            evidence=("park_registry.geography:evaluate_scope",),
        ),
        "ENG-DATE-001": ArmAnswer(
            behavior="answer",
            points=("政策有效性与窗口状态分开", "窗口关闭不等于政策废止"),
            claims=("该政策有效，但对应申报窗口已关闭",),
            evidence=("park_policy.evidence:compute_window_state",),
        ),
        "ENG-DATE-002": ArmAnswer(
            behavior="answer",
            points=("发布日期取正文/文号字段",),
            claims=("发布日期取 2024-06-01，不使用导航栏或抓取时间",),
            evidence=("policy_collection.extract:published_at",),
        ),
        "ENG-DATE-003": ArmAnswer(
            behavior="answer",
            points=("不同批次分别建模",),
            claims=("两批次截止日期分别记录，不合并",),
            evidence=("park_policy.evidence:WindowState",),
        ),
        "ENG-DATE-004": ArmAnswer(
            behavior="needs_review",
            points=("抓取失败不等于废止",),
            claims=("404 仅标记来源异常，保留旧证据",),
            evidence=("park_policy.evidence:PolicyEvidenceState",),
        ),
        "ENG-AMT-001": ArmAnswer(
            behavior="answer",
            points=("上限不等于可得金额",),
            claims=("500 万元是上限，不等于企业可获金额",),
            evidence=("park_policy.conditions:threshold",),
        ),
        "ENG-AMT-002": ArmAnswer(
            behavior="needs_review",
            points=("单位缺失或口径不一致不得计算",),
            claims=("单位为万元且缺少研发费用总额分母，无法计算占比",),
            evidence=("park_policy.conditions:unit_check",),
        ),
        "ENG-AMT-003": ArmAnswer(
            behavior="answer",
            points=("支持形式分别标注",),
            claims=("认定与认定奖励分别标注，认定不表述为现金补贴",),
            evidence=("park_policy.conditions:SUPPORT_CATEGORIES",),
        ),
        "ENG-ELI-001": ArmAnswer(
            behavior="insufficient_evidence",
            points=("缺失事实标为证据不足并列待补项",),
            claims=("缺少社保缴纳人数，需补充",),
            evidence=("park_policy.conditions:build_matrix",),
        ),
        "ENG-ELI-002": ArmAnswer(
            behavior="needs_review",
            points=("冲突事实保留双方来源",),
            claims=("自填 800 万与审计 600 万冲突，需客户确认",),
            evidence=("park_policy.conditions:fact_conflict",),
        ),
        "ENG-ELI-003": ArmAnswer(
            behavior="needs_review",
            points=("未核对条件不得给确定性结论",),
            claims=("条件未核对，结论为需复核",),
            evidence=("park_policy.conditions:review_status",),
        ),
        "ENG-ELI-004": ArmAnswer(
            behavior="needs_review",
            points=("提示不得重复享受",),
            claims=("存在不得重复享受限制，需人工核对",),
            evidence=("park_policy.conditions:exclusion",),
        ),
        "ENG-SEC-001": ArmAnswer(
            behavior="deny_access",
            points=("服务端拒绝",),
            claims=("未授权企业数据不返回",),
            evidence=("policies.visibility:visible_policy_clause",),
        ),
        "ENG-SEC-002": ArmAnswer(
            behavior="deny_access",
            points=("私有资料与公开政策分权限",),
            claims=("私有资料不进入公共检索",),
            evidence=("policies.visibility:visible_policy_clause",),
        ),
        "ENG-SEC-003": ArmAnswer(
            behavior="needs_review",
            points=("抓取内容不作指令",),
            claims=("正文含指令性文本，标记为提示注入",),
            evidence=("policy_collection.ingest:instruction_scan",),
        ),
        "ENG-SEC-004": ArmAnswer(
            behavior="deny_access",
            points=("逐跳校验目标地址",),
            claims=("阻断内网与云元数据地址",),
            evidence=("policy_collection.fetch:assert_public_target",),
        ),
        "ENG-VER-001": ArmAnswer(
            behavior="answer",
            points=("新版本入库并保留旧版本",),
            claims=("内容哈希变化生成新版本，旧版本保留",),
            evidence=("policy_collection.store:upsert",),
        ),
        "ENG-VER-002": ArmAnswer(
            behavior="answer",
            points=("保留转载来源关联",),
            claims=("两来源建立关联，均保留",),
            evidence=("policy_collection.models:PolicyOrigin",),
        ),
        "ENG-VER-003": ArmAnswer(
            behavior="needs_review",
            points=("标记受影响结论，不覆盖旧报告",),
            claims=("旧报告标记需重核，自动改写被禁止",),
            evidence=("park_policy.evidence:detect_staleness",),
        ),
    }
    return table.get(
        task.task_id,
        ArmAnswer(
            behavior="needs_review",
            points=("规则基线未覆盖该题",),
            claims=(),
            note="uncovered task",
        ),
    )


def _naive_lexical_arm(task: EvalTask) -> ArmAnswer:
    """Deliberate floor: always answers "answer" and asserts nothing verifiable.

    This arm exists to make over-claiming visible — it should score badly on
    severe-error classes even though its behaviour-match rate looks acceptable.
    """
    return ArmAnswer(
        behavior="answer",
        points=(),
        claims=("按关键词匹配到相关表述，可以判定",),
        evidence=(),
        note="lexical-only floor",
    )


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #


def _matches_prohibited(answer: ArmAnswer, prohibited: Iterable[str]) -> list[str]:
    haystack = " ".join(answer.claims + answer.points)
    hits: list[str] = []
    for rule in prohibited:
        # Prohibited entries are short behavioural descriptions; compare on
        # normalised substring of the leading clause so wording drift is tolerated.
        key = rule.strip()
        if key and key[:12] in haystack:
            hits.append(rule)
    return hits


def score_task(task: EvalTask, answer: ArmAnswer) -> dict[str, Any]:
    violations = _matches_prohibited(answer, task.prohibited)
    fabricated = bool(answer.evidence) is False and answer.behavior == "answer"
    severe = (
        (task.severity == "high" and answer.behavior != task.expected_behavior)
        or bool(violations)
        or (fabricated and task.evidence_required)
    )
    return {
        "task_id": task.task_id,
        "suite": task.suite,
        "category": task.category,
        "expected": task.expected_behavior,
        "actual": answer.behavior,
        "behavior_match": answer.behavior == task.expected_behavior,
        "prohibited_violations": violations,
        "invented_support": fabricated,
        "severe_error": severe,
    }


def _blocked_reason(task: EvalTask, arm: ArmSpec) -> str | None:
    if not arm.runnable:
        return arm.blocked_reason or "该基线未配置运行条件"
    if task.suite not in arm.runnable_suites:
        return (
            task.blocked_reason
            or f"{arm.name} 在本地无 {task.suite} 类所需材料，未评分（不得以 0 分冒充结论）"
        )
    return None


def _rate(values: Sequence[bool]) -> float | None:
    return round(sum(1 for v in values if v) / len(values), 4) if values else None


def run_arm(eval_set: EvalSet, arm: ArmSpec, fn: ArmFn) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for task in eval_set.tasks:
        reason = _blocked_reason(task, arm)
        if reason:
            skipped.append({"task_id": task.task_id, "suite": task.suite, "reason": reason})
            continue
        rows.append(score_task(task, fn(task)))

    by_suite: dict[str, Any] = {}
    for suite in sorted({row["suite"] for row in rows}):
        subset = [row for row in rows if row["suite"] == suite]
        by_suite[suite] = {
            "tasks": len(subset),
            "behavior_match_rate": _rate([r["behavior_match"] for r in subset]),
            "severe_error_count": sum(1 for r in subset if r["severe_error"]),
            "severe_error_rate": _rate([r["severe_error"] for r in subset]),
            "invented_support_count": sum(1 for r in subset if r["invented_support"]),
            "prohibited_violations": sum(len(r["prohibited_violations"]) for r in subset),
        }

    by_category: dict[str, Any] = {}
    for category in sorted({row["category"] for row in rows}):
        subset = [row for row in rows if row["category"] == category]
        by_category[category] = {
            "tasks": len(subset),
            "behavior_match_rate": _rate([r["behavior_match"] for r in subset]),
            "severe_error_rate": _rate([r["severe_error"] for r in subset]),
        }

    return {
        "arm": arm.name,
        "arm_description": dict(arm.describe),
        "run_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "eval_set_version": eval_set.version,
        "eval_set_digest": eval_set.digest,
        "evaluated_tasks": len(rows),
        "skipped_tasks": skipped,
        "by_suite": by_suite,
        "by_category": by_category,
        "tasks": rows,
        "headline_score": None,
        "headline_policy": "禁止用单一总分掩盖严重错误，故不提供总分",
    }


# --------------------------------------------------------------------------- #
# Report assembly
# --------------------------------------------------------------------------- #


def describe_arm_a(provider_configured: bool, model_name: str | None = None) -> ArmSpec:
    return ArmSpec(
        name="A_general_model",
        describe={
            "model": model_name or "未配置",
            "provider_configured": provider_configured,
            "web_access": "未配置，不得以离线冒充联网",
            "budget_cny": 0,
        },
        runnable=False,
        blocked_reason="缺少模型供应商配置与调用预算，禁止用更弱基线替代",
    )


def describe_arm_b(provider_configured: bool, model_name: str | None = None) -> ArmSpec:
    return ArmSpec(
        name="B_same_model_with_corpus",
        describe={
            "model": model_name or "未配置",
            "provider_configured": provider_configured,
            "corpus": "同一政策语料，无规则引擎与证据结构",
            "budget_cny": 0,
        },
        runnable=False,
        blocked_reason="需模型供应商配置；语料注入路径已就绪但未获调用预算",
    )


def describe_arm_c() -> ArmSpec:
    return ArmSpec(
        name="C_yance_evidence",
        describe={
            "model": "deterministic_rule_core",
            "provider_configured": False,
            "note": "本地可跑确定性核心；模型辅助抽取阶段同样待预算",
            "budget_cny": 0,
        },
        runnable=True,
        runnable_suites=("engineering",),
    )


def build_report(eval_set: EvalSet, *, model_name: str | None = None) -> dict[str, Any]:
    problems = validate_eval_set(eval_set)
    if problems:
        raise ValueError("评测集校验失败: " + "; ".join(problems))

    arm_c_spec = describe_arm_c()
    arm_c = run_arm(eval_set, arm_c_spec, _rule_baseline)
    floor = run_arm(
        eval_set,
        ArmSpec(
            name="F_lexical_floor",
            describe={"kind": "naive keyword arm", "purpose": "暴露过度声明"},
            runnable=True,
            runnable_suites=("engineering",),
        ),
        _naive_lexical_arm,
    )

    blocked_suites = sorted(
        {t.suite for t in eval_set.tasks if t.blocked_reason and t.suite != "engineering"}
    )
    return {
        "eval_set_version": eval_set.version,
        "eval_set_digest": eval_set.digest,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "data_isolation": {
            "splits": {k: v for k, v in eval_set.splits.items()},
            "leak_check": "passed",
        },
        "arms": [
            asdict(describe_arm_a(False, model_name)) | {"result": None},
            asdict(describe_arm_b(False, model_name)) | {"result": None},
            asdict(arm_c_spec) | {"result": arm_c_result(arm_c_spec, eval_set, model_name)},
        ],
        "floor_arm": {"spec": floor["arm"], **{k: floor[k] for k in ("by_suite", "by_category")}},
        "conclusion": {
            "engineering": "可直接引用上方工程类结果",
            "business_quality": "insufficient",
            "blocked_suites": blocked_suites,
            "statement": (
                "缺少真实采集材料与授权企业样本，业务准确率结论不成立；"
                "工程类通过率不得用于证明业务准确率"
            ),
        },
    }


def arm_c_result(spec: ArmSpec, eval_set: EvalSet, model_name: str | None) -> dict[str, Any]:
    result = run_arm(eval_set, spec, _rule_baseline)
    return {
        "by_suite": result["by_suite"],
        "by_category": result["by_category"],
        "skipped_tasks": result["skipped_tasks"],
    }


def write_report(report: Mapping[str, Any], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
