"""semantic_contract：语义契约编译器（M2 参考实现，两域共用）。

    from semantic_contract import load_entity, compile_view, execute

    entity = load_entity("medflow")
    q = compile_view(entity, "medflow.view.tat_by_department", dialect="sqlite")
    result = execute(q, sqlite3.connect("backend/data/medflow_app.db"))
"""
from .compiler import CompiledQuery, PolicyViolationError, compile_view
from .dialect import get_dialect, translate_case
from .executor import execute, open_sqlite
from .loader import REGISTRY, find_view, load, load_entity, semantic_registry
from .orchestration import (
    ANSWER_SYSTEM_TEMPLATE,
    PLAN_INTENTS,
    PLANNER_SYSTEM_TEMPLATE,
    PlanParseError,
    answer_prompt,
    parse_plan,
    planner_prompt,
    rule_plan,
    validate_plan,
)
from .reporting import (
    REPORT_PLANNER_SYSTEM_TEMPLATE,
    REPORT_SUMMARY_SYSTEM_TEMPLATE,
    ReportPlanParseError,
    apply_anomaly_rules,
    parse_report_plan,
    parse_report_summary,
    report_planner_prompt,
    report_summary_prompt,
    section_digest,
    validate_report_plan,
)

__version__ = "0.4.0"

__all__ = [
    "CompiledQuery", "PolicyViolationError", "compile_view",
    "execute", "open_sqlite", "get_dialect", "translate_case",
    "load", "load_entity", "find_view", "semantic_registry", "REGISTRY",
    # M3 编排参考实现
    "PLANNER_SYSTEM_TEMPLATE", "ANSWER_SYSTEM_TEMPLATE", "PLAN_INTENTS",
    "PlanParseError", "planner_prompt", "parse_plan", "rule_plan",
    "validate_plan", "answer_prompt",
    # M4 报表编排参考实现
    "REPORT_PLANNER_SYSTEM_TEMPLATE", "REPORT_SUMMARY_SYSTEM_TEMPLATE",
    "ReportPlanParseError", "report_planner_prompt", "parse_report_plan",
    "validate_report_plan", "report_summary_prompt", "parse_report_summary",
    "section_digest", "apply_anomaly_rules",
]
