"""M4 报表编排参考实现测试（契约仓库，领域无关）。

覆盖：报表计划三态解析 / 结构校验（节数上限、空节拦截）/ 汇总 prompt 组装
（纯语义注入，无物理列名）/ 汇总输出解析 / 声明式异常规则求值（list 行与
dict 行两种执行器产物、四种比较符、非数值与 None 跳过）。
"""
import json

import pytest

from semantic_contract import (
    REPORT_PLANNER_SYSTEM_TEMPLATE,
    PlanParseError,
    apply_anomaly_rules,
    parse_report_plan,
    parse_report_summary,
    report_planner_prompt,
    report_summary_prompt,
    section_digest,
    validate_report_plan,
)
from semantic_contract.reporting import ReportPlanParseError

REGISTRY = [
    {"id": "demo.view.total", "name_zh": "总量", "formula": "count(*)", "grain": ["day"],
     "time_window": {"type": "rolling", "days": 7}, "notes": "总量视图"},
    {"id": "demo.view.mix", "name_zh": "结构占比", "formula": "share by type", "grain": ["day", "type"],
     "time_window": None, "notes": "结构视图"},
]

PLAN_JSON = {
    "title": "盲盒经营日报",
    "sections": [
        {"question": "盲盒销售占比多少？", "rationale": "总量侧面"},
        {"question": "客单价什么水平？", "rationale": "结构侧面"},
    ],
}


# ---------------- 报表计划解析（三态兼容） ----------------

def test_parse_report_plan_bare_json():
    plan = parse_report_plan(json.dumps(PLAN_JSON, ensure_ascii=False))
    assert plan["title"] == "盲盒经营日报"
    assert [s["question"] for s in plan["sections"]] == ["盲盒销售占比多少？", "客单价什么水平？"]


def test_parse_report_plan_fenced_and_tagged():
    fenced = f"```json\n{json.dumps(PLAN_JSON, ensure_ascii=False)}\n```"
    assert len(parse_report_plan(fenced)["sections"]) == 2
    tagged = f"<json>{json.dumps(PLAN_JSON, ensure_ascii=False)}</json>"
    assert len(parse_report_plan(tagged)["sections"]) == 2


def test_parse_report_plan_rejects_empty_sections():
    with pytest.raises(ReportPlanParseError):
        parse_report_plan(json.dumps({"title": "t", "sections": []}, ensure_ascii=False))
    with pytest.raises(ReportPlanParseError):
        parse_report_plan(json.dumps({"sections": [{"rationale": "没有问题"}]}, ensure_ascii=False))
    with pytest.raises(ReportPlanParseError):
        parse_report_plan("这不是 JSON")


def test_report_plan_parse_error_is_plan_parse_error():
    # 子类关系：调用侧统一 catch PlanParseError 即可
    assert issubclass(ReportPlanParseError, PlanParseError)


# ---------------- 报表计划校验 ----------------

def test_validate_report_plan_passes():
    assert validate_report_plan(parse_report_plan(json.dumps(PLAN_JSON, ensure_ascii=False))) == []


def test_validate_report_plan_rejects_too_many_sections():
    plan = {"title": "t", "sections": [{"question": f"q{i}"} for i in range(5)]}
    v = validate_report_plan(plan)
    assert v and v[0]["rule_id"] == "SC-R001" and "超过上限" in v[0]["message"]


def test_validate_report_plan_allows_single_section():
    plan = {"title": "t", "sections": [{"question": "直接问"}]}
    assert validate_report_plan(plan) == []


# ---------------- 规划 prompt：注入语义注册表（铁律①） ----------------

def test_report_planner_prompt_injects_semantics_not_ddl():
    prompt = report_planner_prompt(REGISTRY)
    assert "demo.view.total" in prompt and "总量" in prompt
    assert "2-4" in prompt
    assert "CREATE TABLE" not in prompt and "column" not in prompt.lower()


# ---------------- 汇总 prompt 与解析 ----------------

def _ask_result(stage="answered", view="demo.view.total"):
    return {
        "stage": stage, "view": view,
        "reply": "盲盒占比 32.5%（口径：滚动 30 天）",
        "data": {"columns": ["day", "share"], "rows": [["2026-10-29", 0.325]], "row_count": 1},
    }


def test_report_summary_prompt_carries_digest_and_anomalies():
    anomalies = [{"rule_id": "R1", "label": "周转异常", "describe": "avg_tat_hours > 0.5",
                  "matched": [{"column": "avg_tat_hours", "value": 1.0, "row": [1.0, "心内科"]}]}]
    digests = [section_digest("各科室周转", _ask_result(view="demo.view.mix"), anomalies)]
    msgs = report_summary_prompt("本周检验周转异常的科室", "医疗周转周报", digests)
    assert msgs[0]["role"] == "system"
    assert "禁止编造" in msgs[0]["content"]
    body = msgs[1]["content"]
    assert "各科室周转" in body and "周转异常" in body and "demo.view.mix" in body
    assert "exam_reports" not in body  # 物理侧永不进 prompt


def test_parse_report_summary_shapes():
    out = parse_report_summary(json.dumps({"summary": "总量平稳。", "insights": ["口径为滚动 30 天", ""]}, ensure_ascii=False))
    assert out == {"summary": "总量平稳。", "insights": ["口径为滚动 30 天"]}
    out2 = parse_report_summary("<json>{\"summary\": \"\"}</json>")
    assert out2 == {"summary": "", "insights": []}
    with pytest.raises(ReportPlanParseError):
        parse_report_summary("no json here")


# ---------------- 声明式异常规则求值 ----------------

RULE_TAT = {"rule_id": "medflow.anomaly.tat", "label": "科室周转异常",
            "describe": "平均周转时间超过目标时限", "basis": "报告完成目标时限 30 分钟",
            "unit": "小时", "column": "avg_tat_hours", "op": ">", "threshold": 0.5}


def test_anomaly_rules_match_list_rows():
    columns = ["avg_tat_hours", "department"]
    rows = [[1.0, "心内科"], [0.3, "骨科"], [None, "空值科"], ["非数值", "脏数据科"]]
    out = apply_anomaly_rules([RULE_TAT], columns, rows)
    assert len(out) == 1
    a = out[0]
    assert a["matched_count"] == 1
    assert a["matched"][0]["row"] == [1.0, "心内科"]
    assert a["matched"][0]["value"] == 1.0
    assert a["basis"] == "报告完成目标时限 30 分钟"


def test_anomaly_rules_match_dict_rows_and_ops():
    rules = [
        {**RULE_TAT, "op": ">="},
        {"rule_id": "r2", "column": "share", "op": "<", "threshold": 0.1},
        {"rule_id": "r3", "column": "share", "op": ">", "threshold": 0.5},
    ]
    columns = ["share", "avg_tat_hours"]
    rows = [{"share": 0.55, "avg_tat_hours": 0.5}, {"share": 0.05, "avg_tat_hours": 2.0}]
    out = apply_anomaly_rules(rules, columns, rows)
    ids = {a["rule_id"] for a in out}
    assert ids == {"medflow.anomaly.tat", "r2", "r3"}  # >= 命中 0.5；< 命中 0.05；> 命中 0.55


def test_anomaly_rules_skip_malformed_and_empty():
    bad = [{"column": "ghost", "op": ">", "threshold": 1}, {"column": "share", "op": "~", "threshold": 1}]
    assert apply_anomaly_rules(bad, ["share"], [[0.9]]) == []
    assert apply_anomaly_rules(None, ["share"], [[0.9]]) == []
    assert apply_anomaly_rules([RULE_TAT], ["share"], [[0.9]]) == []  # 列不存在


RULE_SHARE = {"rule_id": "huanyu.anomaly.dist_concentration", "label": "分销集中度风险",
              "describe": "单一分销商 GMV 占比超过一半", "basis": "渠道健康度经验阈值 50%",
              "unit": "", "column": "sales_amount", "op": ">", "threshold": 0.5, "mode": "share"}


def test_anomaly_rules_share_mode_concentration():
    columns = ["dist_id", "sales_amount"]
    rows = [["d1", 600], ["d2", 300], ["d3", 100], ["d4", None]]
    out = apply_anomaly_rules([RULE_SHARE], columns, rows)
    assert len(out) == 1
    a = out[0]
    assert a["mode"] == "share"
    assert a["matched_count"] == 1
    assert a["matched"][0]["value"] == pytest.approx(0.6)
    assert a["matched"][0]["row"] == ["d1", 600]


def test_anomaly_rules_share_mode_zero_total_and_thresholds():
    assert apply_anomaly_rules([RULE_SHARE], ["sales_amount"], [[0], [None]]) == []  # 总和为 0 不除零
    half = [{**RULE_SHARE, "threshold": 0.4}]
    out = apply_anomaly_rules(half, ["sales_amount"], [[6], [4]])
    assert out[0]["matched_count"] == 1
