"""M3 编排参考实现单测：规划 prompt / 计划解析 / 规则兜底 / 校验 / 回答 prompt。

全程纯函数，不触碰 LLM 传输（供型在调用侧，强制真模型）。
"""
import json

import pytest

from semantic_contract import (
    PlanParseError,
    load_entity,
    parse_plan,
    planner_prompt,
    rule_plan,
    semantic_registry,
    validate_plan,
)

MEDFLOW = load_entity("medflow")
HUANYU_OFFERING = load_entity("huanyu-offering")
MEDFLOW_REGISTRY = semantic_registry(MEDFLOW)


# ---------------- 规划 prompt：铁律①注入语义不注入 DDL ----------------

def test_planner_prompt_contains_registry_without_physical_leak():
    prompt = planner_prompt(MEDFLOW_REGISTRY)
    assert "medflow.view.tat_by_department" in prompt
    assert "科室检验平均周转时间" in prompt
    # 物理侧永不进 prompt：无列名 / SQL 关键字 / compile 段
    for leak in ("exam_reports", "julianday", "physical_mapping", "compile", "SELECT"):
        assert leak not in prompt


def test_planner_prompt_states_intent_enum():
    prompt = planner_prompt(MEDFLOW_REGISTRY)
    for intent in ("metric_query", "diagnosis_request", "prescription_request", "out_of_scope"):
        assert intent in prompt


# ---------------- 计划解析 ----------------

PLAN_OK = {
    "view_id": "medflow.view.tat_by_department",
    "intent": "metric_query",
    "filters": {},
    "reasoning": "问题问科室周转，命中 avg(tat_hours) by day, department",
}


def _raw_with(plan: dict, wrapper: str) -> str:
    body = json.dumps(plan, ensure_ascii=False)
    return wrapper.format(body=body)


def test_parse_plan_accepts_three_json_shapes():
    bare = _raw_with(PLAN_OK, "{body}")
    fenced = _raw_with(PLAN_OK, "```json\n{body}\n```")
    tagged = _raw_with(PLAN_OK, "前置说明\n<json>{body}</json>\n后置说明")
    for raw in (bare, fenced, tagged):
        plan = parse_plan(raw, MEDFLOW_REGISTRY)
        assert plan["view_id"] == "medflow.view.tat_by_department"
        assert plan["intent"] == "metric_query"


def test_parse_plan_allows_null_view_id():
    plan = parse_plan(json.dumps({"view_id": None, "intent": "out_of_scope"}), MEDFLOW_REGISTRY)
    assert plan["view_id"] is None


def test_parse_plan_rejects_garbage_but_leaves_semantics_to_validator():
    # 结构不合法（无 JSON）→ PlanParseError，调用方重试后走规则兜底
    with pytest.raises(PlanParseError):
        parse_plan("我觉得这个问题没法回答", MEDFLOW_REGISTRY)
    # 臆造 view_id 是语义问题：解析放行，由 validate_plan（校验 Agent）拦截
    bad = dict(PLAN_OK, view_id="medflow.view.i_made_this_up")
    plan = parse_plan(json.dumps(bad), MEDFLOW_REGISTRY)
    violations = validate_plan(plan, MEDFLOW)
    assert violations and violations[0]["severity"] == "block"


# ---------------- 规则兜底（仅解析失败时用） ----------------

def test_rule_plan_hits_tat_question():
    plan = rule_plan("上周哪个科室检验周转最慢？", MEDFLOW_REGISTRY)
    assert plan is not None
    assert plan["view_id"] == "medflow.view.tat_by_department"
    assert plan["planner"] == "rule_fallback"


def test_rule_plan_returns_none_for_unmatched_question():
    assert rule_plan("今天天气怎么样", MEDFLOW_REGISTRY) is None


# ---------------- 校验 Agent：视图合法性 ----------------

def test_validate_plan_passes_registry_view():
    plan = {"view_id": "medflow.view.tat_by_department"}
    assert validate_plan(plan, MEDFLOW) == []


def test_validate_plan_no_view_is_not_violation():
    assert validate_plan({"view_id": None}, MEDFLOW) == []


def test_validate_plan_flags_hallucinated_view():
    violations = validate_plan({"view_id": "medflow.view.ghost"}, MEDFLOW)
    assert len(violations) == 1
    assert violations[0]["severity"] == "block"
    assert "臆造" in violations[0]["message"]


def test_validate_plan_blocked_view_gets_governance_note():
    # 治理活案例：盲盒毛利率物理层缺 cost → blocked，校验 Agent 给出可解释出口
    violations = validate_plan({"view_id": "huanyu.view.mystery_gross_margin"}, HUANYU_OFFERING)
    assert len(violations) == 1
    assert violations[0]["severity"] == "block"
    assert "blocked" in violations[0]["message"]
    assert "cost" in violations[0]["message"]  # 治理原因可解释


# ---------------- 回答 prompt：铁律②结果带依据 ----------------

def test_answer_prompt_carries_caliber_and_result():
    from semantic_contract import answer_prompt

    view_meta = next(v for v in MEDFLOW_REGISTRY if v["id"] == "medflow.view.tat_by_department")
    result = {
        "columns": ["department", "day", "avg_tat_hours"],
        "rows": [["心内科", "2026-10-27", 3.2]],
        "row_count": 1,
        "sql": "SELECT ...",
    }
    messages = answer_prompt("上周哪个科室周转最慢？", view_meta, result)
    assert messages[0]["role"] == "system"
    user_text = messages[1]["content"]
    assert "avg(tat_hours)" in user_text          # 口径公式
    assert "心内科" in user_text                    # 结果数据
    assert "禁止编造" in messages[0]["content"]     # 反幻觉规则
