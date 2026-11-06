"""Deterministic classification of policy documents.

Rules are keyword + context based and every finding carries the exact source
sentence. The classifier never upgrades a document: an 认定 (designation) is not
reported as cash, a 贷款贴息 is reported as an interest subsidy, and an amount is
only attached to a grant when the sentence itself states the amount.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

SUPPORT_FORMS = {
    "project_grant": "项目资助/补助",
    "qualification": "资质认定",
    "qualification_award": "认定奖励",
    "loan_discount": "贷款贴息",
    "tax_incentive": "税收优惠",
    "service_voucher": "服务券/创新券",
    "equity_or_fund": "基金/股权投资",
    "talent_support": "人才支持",
    "other": "其他支持",
}

DOC_KINDS = {
    "policy": "政策正文",
    "implementation_rule": "实施细则",
    "application_notice": "申报通知",
    "correction": "更正/补充",
    "extension": "延期",
    "repeal": "废止/失效",
    "interpretation": "政策解读",
    "public_list": "公示名单",
}

INDUSTRY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "人工智能": ("人工智能", "大模型", "算力", "智能体", "AI"),
    "机器人": ("机器人", "具身智能", "人形机器人"),
    "低空经济": ("低空经济", "无人机", "eVTOL", "通航"),
    "生物医药": ("生物医药", "创新药", "医疗器械", "细胞治疗", "基因"),
    "新材料": ("新材料", "先进材料", "半导体材料"),
    "新能源": ("新能源", "光伏", "储能", "氢能", "风电", "动力电池"),
    "高端装备": ("高端装备", "数控机床", "工业母机", "智能装备"),
    "集成电路": ("集成电路", "芯片", "晶圆", "EDA"),
    "软件与信息服务": ("软件", "工业互联网", "信息技术服务", "开源"),
    "节能环保": ("节能", "环保", "双碳", "绿色低碳", "循环经济"),
}

SUPPORT_TOPICS: dict[str, tuple[str, ...]] = {
    "研发投入": ("研发费用", "研发投入", "研究开发", "R&D"),
    "技术改造": ("技术改造", "技改", "智能化改造", "数字化转型"),
    "设备更新": ("设备更新", "以旧换新", "首台套", "首版次", "首批次"),
    "创新券": ("创新券", "科技创新券", "服务券"),
    "贴息": ("贴息", "贷款利息补贴"),
    "成果转化": ("成果转化", "技术转移", "概念验证", "中试"),
    "人才": ("人才", "团队引进", "高层次人才"),
    "高新技术企业": ("高新技术企业", "高企"),
    "科技型中小企业": ("科技型中小企业", "科技中小企业"),
    "专精特新": ("专精特新", "小巨人", "单项冠军"),
    "创新平台": ("重点实验室", "技术创新中心", "工程研究中心", "企业技术中心", "孵化器"),
}

GRANT_WORDS = ("资助", "补助", "补贴", "支持资金", "扶持资金", "奖励资金", "无偿资助")
QUALIFICATION_AWARD_WORDS = ("认定奖励", "一次性奖励", "奖励", "给予奖励", "配套奖励")
LOAN_WORDS = ("贴息", "利息补贴", "贷款利息")
TAX_WORDS = ("税收优惠", "减按", "免征", "加计扣除", "税收减免", "税率优惠")
VOUCHER_WORDS = ("创新券", "服务券", "科技创新券")
EQUITY_WORDS = ("政府投资基金", "股权投资", "引导基金", "天使基金")
TALENT_WORDS = ("人才补贴", "安家费", "人才奖励", "生活补贴")

AMOUNT_RE = re.compile(
    r"(?:最高|不超过|最多|上限为|给予)?\s*"
    r"(\d+(?:\.\d+)?)\s*(亿元|万元|万|元)"
    r"(?:[/／]?(?:项|个|家|人|年))?"
)

REPEAL_RE = re.compile(r"(废止|失效|停止执行|不再执行|予以废止|自.{0,12}起废止)")
CORRECTION_RE = re.compile(r"(更正|更正通知|补充通知|修正|勘误)")
EXTENSION_RE = re.compile(r"(延期|延长|推迟|顺延)")
NOTICE_RE = re.compile(r"(申报通知|申报指南|组织申报|开展.{0,12}申报|申报工作|受理申报|征集)")
IMPLEMENTATION_RE = re.compile(r"(实施细则|管理办法|操作规程|实施细则)")
PUBLIC_LIST_RE = re.compile(r"(公示|名单|拟认定|拟支持)")

WINDOW_PATTERNS = (
    re.compile(
        r"(?:申报|受理|填报|申请)(?:时间|期限|日期)?\s*(?:为|：|:)?\s*"
        r"(20\d{2})\s*[年\-/.]\s*(\d{1,2})\s*[月\-/.]\s*(\d{1,2})\s*日?\s*"
        r"(?:至|到|—|-|~|～)\s*(20\d{2})\s*[年\-/.]\s*(\d{1,2})\s*[月\-/.]\s*(\d{1,2})\s*日?"
    ),
    re.compile(
        r"(?:截止|截至)(?:时间|日期)?\s*(?:为|：|:)?\s*"
        r"(20\d{2})\s*[年\-/.]\s*(\d{1,2})\s*[月\-/.]\s*(\d{1,2})\s*日?"
    ),
)

BATCH_RE = re.compile(r"(20\d{2}\s*年?(?:度)?)\s*(?:第\s*([一二三四五六七八九十0-9]+)\s*批|([一二三四五六七八九十0-9]+)\s*批)")


@dataclass(frozen=True)
class SupportFinding:
    form: str
    evidence: str
    amount_text: str | None = None

    @property
    def label(self) -> str:
        return SUPPORT_FORMS.get(self.form, self.form)


@dataclass
class ApplicationWindow:
    start: date | None
    end: date | None
    evidence: str
    batch: str | None = None
    year: int | None = None


@dataclass
class Classification:
    doc_kind: str
    support_forms: list[SupportFinding] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    application_windows: list[ApplicationWindow] = field(default_factory=list)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。；！？\n])", text)
    return [part.strip() for part in parts if part and part.strip()]


def _first_sentence(sentences: list[str], words: tuple[str, ...]) -> str | None:
    for sentence in sentences:
        if any(word in sentence for word in words):
            return sentence
    return None


def _amount_in_sentence(sentence: str) -> str | None:
    match = AMOUNT_RE.search(sentence)
    if not match:
        return None
    raw = match.group(0).strip()
    return f"{match.group(1)}{match.group(2)}" if raw else None


def detect_doc_kind(title: str, text: str) -> str:
    head = f"{title}\n{text[:1200]}"
    if REPEAL_RE.search(title) or re.search(r"^.{0,30}(废止|失效)的?(通知|公告|决定)", title):
        return "repeal"
    if CORRECTION_RE.search(title):
        return "correction"
    if EXTENSION_RE.search(title):
        return "extension"
    if NOTICE_RE.search(title):
        return "application_notice"
    if PUBLIC_LIST_RE.search(title) and "申报" not in title:
        return "public_list"
    if IMPLEMENTATION_RE.search(title):
        return "implementation_rule"
    if "解读" in title:
        return "interpretation"
    if REPEAL_RE.search(head) and "废止" in head[:400]:
        return "policy"
    return "policy"


def detect_support_forms(text: str) -> list[SupportFinding]:
    """Return at most one finding per form, each pinned to a real sentence."""
    sentences = _sentences(text)
    findings: dict[str, SupportFinding] = {}

    def add(form: str, sentence: str) -> None:
        if form in findings:
            return
        amount = _amount_in_sentence(sentence) if form in {"project_grant", "qualification_award"} else None
        findings[form] = SupportFinding(form=form, evidence=sentence[:300], amount_text=amount)

    voucher = _first_sentence(sentences, VOUCHER_WORDS)
    if voucher:
        add("service_voucher", voucher)
    loan = _first_sentence(sentences, LOAN_WORDS)
    if loan:
        add("loan_discount", loan)
    tax = _first_sentence(sentences, TAX_WORDS)
    if tax:
        add("tax_incentive", tax)
    equity = _first_sentence(sentences, EQUITY_WORDS)
    if equity:
        add("equity_or_fund", equity)
    talent = _first_sentence(sentences, TALENT_WORDS)
    if talent:
        add("talent_support", talent)

    # 认定奖励 requires an explicit reward word; a bare 认定 is not money.
    award = None
    for sentence in sentences:
        if any(word in sentence for word in QUALIFICATION_AWARD_WORDS) and "认定" in sentence:
            award = sentence
            break
    if award:
        add("qualification_award", award)

    grant = None
    for sentence in sentences:
        if any(word in sentence for word in GRANT_WORDS) and _amount_in_sentence(sentence):
            grant = sentence
            break
    if grant is None:
        grant = _first_sentence(sentences, GRANT_WORDS)
    if grant:
        add("project_grant", grant)

    designation = _first_sentence(
        sentences,
        ("认定为", "认定下列", "经认定", "评选为", "评定为", "授予", "纳入名单", "备案为", "颁发证书"),
    )
    if designation:
        add("qualification", designation)

    if not findings:
        findings["other"] = SupportFinding("other", sentences[0][:300] if sentences else "")
    return list(findings.values())


def detect_industries(text: str) -> list[str]:
    hits = [
        industry
        for industry, keywords in INDUSTRY_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]
    return hits


def detect_topics(text: str) -> list[str]:
    return [
        topic
        for topic, keywords in SUPPORT_TOPICS.items()
        if any(keyword in text for keyword in keywords)
    ]


def detect_application_windows(text: str) -> list[ApplicationWindow]:
    """Extract application windows; separate batches stay separate."""
    windows: list[ApplicationWindow] = []
    for pattern in WINDOW_PATTERNS:
        for match in pattern.finditer(text[:20000]):
            groups = match.groups()
            try:
                if len(groups) == 6:
                    start = date(int(groups[0]), int(groups[1]), int(groups[2]))
                    end = date(int(groups[3]), int(groups[4]), int(groups[5]))
                else:
                    start = None
                    end = date(int(groups[0]), int(groups[1]), int(groups[2]))
            except (TypeError, ValueError):
                continue
            if start and end and end < start:
                continue
            context = text[max(0, match.start() - 120) : match.end() + 40]
            batch_match = BATCH_RE.search(context)
            batch = None
            year = (start or end).year if (start or end) else None
            if batch_match:
                parts = [part for part in batch_match.groups() if part]
                batch = " ".join(parts)
            windows.append(
                ApplicationWindow(
                    start=start,
                    end=end,
                    evidence=context.strip()[:300],
                    batch=batch,
                    year=year,
                )
            )
    deduped: list[ApplicationWindow] = []
    for window in windows:
        if any(
            existing.start == window.start
            and existing.end == window.end
            and existing.batch == window.batch
            for existing in deduped
        ):
            continue
        deduped.append(window)
    return deduped


def classify(title: str, text: str) -> Classification:
    return Classification(
        doc_kind=detect_doc_kind(title, text),
        support_forms=detect_support_forms(text),
        industries=detect_industries(f"{title}\n{text}"),
        topics=detect_topics(f"{title}\n{text}"),
        application_windows=detect_application_windows(text),
    )
