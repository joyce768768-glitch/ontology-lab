"""M4 报表编排参考实现：NL 问题 → 多节复合报表（两域共用）。

M3 编排是「单问题 → 单视图」；M4 Data Agent 在其上叠一层「报表编排」：

    NL 问题（如「上月盲盒卖得怎么样」）
      → [报表规划 Agent] report_planner_prompt：注入语义注册表（铁律①），
        LLM 拆解 2-4 个统计子问题（总量 → 结构 → 异常/趋势，角度互补）
      → [逐节执行] 每个子问题由调用侧走 M3 ask_question 全链路——
        三道校验（意图边界 / 视图合法性 / 编译期 machine_check）逐节不旁路
      → [异常标注] apply_anomaly_rules：声明式业务规则机判（M4 设计决策：
        语义层管「数从哪来」，应用层管「数怎么判」——异常判定不进语义视图）
      → [汇总 Agent] report_summary_prompt：各节叙述 + 机器异常标注 →
        LLM 汇总 summary + insights（数字只从各节引用，口径差异必须提示）

本模块与 orchestration.py 同边界：只产出 prompt、解析输出、做纯函数校验
（含异常规则求值），不触碰任何 LLM 传输，全部可单测。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from .orchestration import PlanParseError, _JSON_RE

__all__ = [
    "ReportPlanParseError",
    "REPORT_PLANNER_SYSTEM_TEMPLATE",
    "REPORT_SUMMARY_SYSTEM_TEMPLATE",
    "report_planner_prompt",
    "parse_report_plan",
    "validate_report_plan",
    "report_summary_prompt",
    "parse_report_summary",
    "section_digest",
    "apply_anomaly_rules",
]


class ReportPlanParseError(PlanParseError):
    """LLM 输出无法解析为合法报表计划（PlanParseError 子类，便于统一捕获）。"""


# ============================================================
# 1. 报表规划 Agent prompt（canonical 模板；TS 侧文本与此对齐）
# ============================================================

REPORT_PLANNER_SYSTEM_TEMPLATE = """你是「报表规划 Agent」。把用户的经营/统计问题拆解为一份多节报表计划：每节回答该问题的一个子角度，合并后能完整回答用户问题。

【语义视图注册表】（口径唯一真相源；每个子问题都必须能被其中某个视图回答，不含任何物理表结构）
{registry}

【规则】
1. 拆解 2-{max_sections} 节；每节 question 是一个独立的统计子问题（不是原问题的复述）。
2. 注册表覆盖不了的侧面不要拆节——每节都必须能命中注册表中的某个视图。
3. 各节角度互补（如：总量 → 结构 → 异常/趋势），禁止两节问同一件事。
4. rationale 用一句话说明该节对回答主问题的作用。
5. 只输出一个 JSON 对象，不要输出任何其他文字：
{{"title": "报表标题", "sections": [{{"question": "子问题1", "rationale": "…"}}, {{"question": "子问题2", "rationale": "…"}}]}}"""


def report_planner_prompt(registry: List[dict], max_sections: int = 4) -> str:
    """组装报表规划 Agent 的 system prompt：只注入纯语义注册表（无物理列名）。"""
    return REPORT_PLANNER_SYSTEM_TEMPLATE.format(
        registry=json.dumps(registry, ensure_ascii=False, indent=2),
        max_sections=max_sections,
    )


# ============================================================
# 2. 报表计划解析与校验（三态兼容同 parse_plan；结构是 {title, sections[]})
# ============================================================

def parse_report_plan(raw: str) -> dict:
    """解析 LLM 输出为报表计划；结构不合法抛 ReportPlanParseError。

    只管解析（JSON 形状 / 字段类型），不管语义——节是否可被注册表回答
    由逐节复用的 M3 链路校验（生成后每节仍过三道防线，不旁路）。
    返回结构：{title, sections: [{question, rationale}]}。
    """
    text = (raw or "").strip()
    m = re.search(r"<json>\s*(\{.*?\})\s*</json>", text, re.DOTALL | re.IGNORECASE)
    json_str = m.group(1) if m else None
    if json_str is None:
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
        json_str = m.group(1) if m else None
    if json_str is None:
        m = _JSON_RE.search(text)
        json_str = m.group(0) if m else None
    if not json_str:
        raise ReportPlanParseError("输出中未找到 JSON 对象")

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ReportPlanParseError(f"JSON 解析失败: {exc}") from exc
    if not isinstance(data, dict):
        raise ReportPlanParseError("报表计划不是 JSON 对象")

    raw_sections = data.get("sections")
    if not isinstance(raw_sections, list) or not raw_sections:
        raise ReportPlanParseError("sections 必须是非空数组")

    sections: List[dict] = []
    for item in raw_sections:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or "").strip()
        if not question:
            continue
        sections.append({"question": question, "rationale": str(item.get("rationale") or "")})
    if not sections:
        raise ReportPlanParseError("sections 中没有任何带 question 的节")

    return {"title": str(data.get("title") or "").strip(), "sections": sections}


def validate_report_plan(plan: dict, max_sections: int = 4) -> List[dict]:
    """校验报表计划结构（节的数量上限 / 每节 question 非空），返回违规列表。

    节数下限不设硬门槛：LLM 拆不出多节时允许单节退化为「原问题直查」，
    调用方按 plan 当作普通问题处理（鲁棒性优先于形式完整）。
    """
    violations: List[dict] = []
    sections = plan.get("sections") or []
    if len(sections) > max_sections:
        violations.append({
            "rule_id": "SC-R001",
            "severity": "block",
            "message": f"报表节数 {len(sections)} 超过上限 {max_sections}",
        })
    for i, s in enumerate(sections):
        if not str(s.get("question") or "").strip():
            violations.append({
                "rule_id": "SC-R001",
                "severity": "block",
                "message": f"第 {i + 1} 节缺少子问题 question",
            })
    return violations


# ============================================================
# 3. 汇总 Agent prompt：各节叙述 + 机器异常标注 → summary + insights
# ============================================================

REPORT_SUMMARY_SYSTEM_TEMPLATE = """你是数据分析助手，基于一份报表各节的回答，写整体汇总与洞察。

【规则】
1. summary：3-5 句话直接回答用户的主问题；数字只能来自【各节回答】或【机器异常标注】，禁止编造、外推或凭记忆补充。
2. 必须点明关键口径：时间窗、指标公式；各节口径有差异时（如滚动窗口≠自然月）必须提示。
3. insights：0-3 条，每条一句话；优先级：机器异常标注 > 口径提示 > 节间对比；没有可说时输出空数组。
4. 被拦截/无数据的节如实说明，不臆测原因。
5. 用中文，只输出一个 JSON 对象，不要输出任何其他文字：
{"summary": "…", "insights": ["…", "…"]}"""


def section_digest(
    section_question: str,
    ask_result: dict,
    anomalies: Optional[List[dict]] = None,
    max_rows: int = 12,
) -> dict:
    """把一节的 ask 结果压成汇总 prompt 可用的摘要（叙述 + 数据 + 异常标注）。"""
    data = ask_result.get("data") or {}
    return {
        "section_question": section_question,
        "stage": ask_result.get("stage"),
        "view": ask_result.get("view"),
        "reply": ask_result.get("reply"),
        "columns": data.get("columns", []),
        "rows": (data.get("rows") or [])[:max_rows],
        "row_count": data.get("row_count", 0),
        "anomalies": anomalies or [],
    }


def report_summary_prompt(question: str, title: str, digests: List[dict]) -> List[dict]:
    """组装汇总 Agent 的 messages：主问题 + 各节摘要（含机器异常标注）。"""
    user_content = (
        f"【用户主问题】\n{question}\n\n"
        f"【报表标题】\n{title}\n\n"
        f"【各节回答摘要】\n{json.dumps(digests, ensure_ascii=False, indent=2, default=str)}"
    )
    return [
        {"role": "system", "content": REPORT_SUMMARY_SYSTEM_TEMPLATE},
        {"role": "user", "content": user_content},
    ]


def parse_report_summary(raw: str) -> dict:
    """解析汇总 Agent 输出为 {summary, insights}；结构不合法抛 ReportPlanParseError。"""
    text = (raw or "").strip()
    m = re.search(r"<json>\s*(\{.*?\})\s*</json>", text, re.DOTALL | re.IGNORECASE)
    json_str = m.group(1) if m else None
    if json_str is None:
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
        json_str = m.group(1) if m else None
    if json_str is None:
        m = _JSON_RE.search(text)
        json_str = m.group(0) if m else None
    if not json_str:
        raise ReportPlanParseError("汇总输出中未找到 JSON 对象")

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ReportPlanParseError(f"汇总 JSON 解析失败: {exc}") from exc
    if not isinstance(data, dict):
        raise ReportPlanParseError("汇总输出不是 JSON 对象")

    insights = [str(x) for x in data.get("insights") or [] if str(x or "").strip()]
    return {"summary": str(data.get("summary") or "").strip(), "insights": insights}


# ============================================================
# 4. 异常标注（声明式业务规则的纯函数求值；规则由各域声明）
# ============================================================

def _num(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


_OPS = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
}


def apply_anomaly_rules(
    rules: Optional[List[dict]],
    columns: List[str],
    rows: List[Any],
) -> List[dict]:
    """对一节数据执行声明式异常规则，返回命中的异常列表（空列表 = 无异常）。

    规则结构（由各域声明，本函数只求值）：
      {rule_id, label, describe, basis, unit, column, op, threshold, mode?}
    mode 两种：
      - "cell"（默认）：行内值直接与 threshold 比较；
      - "share"：行值占该列总和的比例与 threshold 比较（集中度类规则），
        threshold 以小数语义解释（0.5 = 50%）。
    行格式兼容两种执行器产物：SQLite 侧 rows 为 list（按 columns 下标取值），
    PostgreSQL 侧 rows 为 dict（按列名取值）。
    """
    anomalies: List[dict] = []
    if not rules:
        return anomalies
    col_index = {c: i for i, c in enumerate(columns)}
    for rule in rules:
        col = rule.get("column")
        op = _OPS.get(rule.get("op"))
        threshold = _num(rule.get("threshold"))
        if col not in col_index or op is None or threshold is None:
            continue

        def _raw(row: Any) -> Any:
            return row[col_index[col]] if isinstance(row, (list, tuple)) else (
                row.get(col) if isinstance(row, dict) else None
            )

        mode = rule.get("mode", "cell")
        total: Optional[float] = None
        if mode == "share":
            total = sum(v for v in (_num(_raw(row)) for row in rows) if v is not None)
        matched: List[dict] = []
        for row in rows:
            num = _num(_raw(row))
            if num is None:
                continue
            value = (num / total) if (mode == "share" and total) else num
            if op(value, threshold):
                matched.append({
                    "column": col,
                    "value": value,
                    "row": row,
                    **({"share": value} if mode == "share" else {}),
                })
        if matched:
            anomalies.append({
                "rule_id": rule.get("rule_id", "anomaly"),
                "label": rule.get("label", str(col)),
                "describe": rule.get("describe") or f"{col} {rule.get('op')} {threshold}",
                "basis": rule.get("basis", ""),
                "unit": rule.get("unit", ""),
                "threshold": threshold,
                "mode": mode,
                "matched_count": len(matched),
                "matched": matched,
            })
    return anomalies
