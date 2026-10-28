"""编译器单测：双域视图 → SQL 快照断言（子串锚定，不冻结全文）。"""
import pytest

from semantic_contract import compile_view, load_entity, semantic_registry
from semantic_contract.compiler import PolicyViolationError

MEDFLOW = load_entity("medflow")
HUANYU_ORDER = load_entity("huanyu-order")
HUANYU_OFFERING = load_entity("huanyu-offering")


# ── MedFlow / sqlite ─────────────────────────────────────────
def test_tat_by_department_sql():
    q = compile_view(MEDFLOW, "medflow.view.tat_by_department")
    assert "JOIN \"users\" ON exam_reports.created_by = users.user_id" in q.sql
    assert "julianday(exam_reports.completed_at)" in q.sql
    assert "date(exam_reports.ordered_at) >= date('now', '-7 days')" in q.sql
    assert "GROUP BY 1, 2" in q.sql
    assert '"n"' in q.sql                       # 样本量自动追加
    assert q.params == {}
    assert q.provenance["matched_by"] == "semantic_view:medflow.view.tat_by_department"
    assert q.provenance["concept_fields"]["tat_hours"]


def test_status_translation_case():
    q = compile_view(MEDFLOW, "medflow.view.report_status_distribution")
    assert "CASE exam_reports.status WHEN 'done' THEN 'completed' WHEN 'pending' THEN 'testing'" in q.sql
    assert "count(*) AS \"report_count\"" in q.sql
    # 有 count 指标时不再自动追加 n
    assert '"n"' not in q.sql


def test_critical_filter_and_window():
    q = compile_view(MEDFLOW, "medflow.view.critical_report_latency")
    assert "exam_reports.flag = 'critical'" in q.sql
    assert "'-1 days'" in q.sql                 # rolling_24h → days: 1


def test_dimension_param_filter():
    q = compile_view(MEDFLOW, "medflow.view.tat_by_department", params={"department": "心内科"})
    assert q.params == {"department": "心内科"}
    assert "users.department = :department" in q.sql


def test_mdt_and_volume_views():
    q1 = compile_view(MEDFLOW, "medflow.view.mdt_consult_volume")
    assert 'avg(mdt_comments.is_adopted) AS "adoption_rate"' in q1.sql
    assert "FROM \"mdt_comments\"" in q1.sql
    q2 = compile_view(MEDFLOW, "medflow.view.exam_volume_by_type")
    assert 'exam_reports.task_type AS "task_type"' in q2.sql


# ── MedFlow / 策略机器判定 ───────────────────────────────────
def test_tat_policy_requires_time_window():
    import copy

    broken = copy.deepcopy(MEDFLOW)
    for v in broken["semantic_views"]:
        if v["id"] == "medflow.view.tat_by_department":
            del v["time_window"]
    with pytest.raises(PolicyViolationError) as exc:
        compile_view(broken, "medflow.view.tat_by_department")
    assert "tat_temporal_window" in str(exc.value)


# ── 寰宇 / postgresql ────────────────────────────────────────
def test_avg_order_value_pg_quoting():
    q = compile_view(HUANYU_ORDER, "huanyu.view.avg_order_value", dialect="postgresql")
    assert 'FROM "orders"' in q.sql
    assert 'avg("orders"."totalAmount") AS "avg_order_value"' in q.sql
    assert '("orders"."time")::date >= current_date - 30' in q.sql
    assert "GROUP BY 1" in q.sql


def test_repeat_rate_raw_sql_window_substitution():
    q = compile_view(HUANYU_ORDER, "huanyu.view.repeat_purchase_rate", dialect="postgresql")
    assert "{time_window}" not in q.sql
    assert 'FROM "orders"' in q.sql
    assert "current_date - 30" in q.sql
    assert "AS repeat_rate" in q.sql


def test_mystery_sales_share_ratio():
    q = compile_view(HUANYU_OFFERING, "huanyu.view.mystery_sales_share", dialect="postgresql")
    assert 'FROM "orderItems"' in q.sql
    assert 'JOIN "offerings"' in q.sql
    assert "CASE WHEN \"offerings\".\"saleType\" = 'mystery'" in q.sql
    assert "nullif(sum(" in q.sql


def test_blocked_view_not_compilable_and_hidden():
    with pytest.raises(ValueError, match="blocked"):
        compile_view(HUANYU_OFFERING, "huanyu.view.mystery_gross_margin")
    ids = [v["id"] for v in semantic_registry(HUANYU_OFFERING)]
    assert ids == ["huanyu.view.mystery_sales_share"]      # blocked 不进 LLM 注册表


def test_registry_semantic_only():
    reg = semantic_registry(MEDFLOW)
    text = str(reg)
    assert "julianday" not in text and "users.user_id" not in text   # 物理细节不进 prompt
    assert len(reg) == 5
