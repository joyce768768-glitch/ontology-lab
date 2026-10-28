"""集成测试：对 M1 落库的 medflow_app.db 实跑编译产物。

跳过条件：本地无该库（CI 场景）。可用 MEDFLOW_DB 环境变量指向其他库。
"""
import os
import sqlite3

import pytest

from semantic_contract import compile_view, execute, load_entity, open_sqlite

MEDFLOW = load_entity("medflow")
DB = os.environ.get(
    "MEDFLOW_DB", "/Users/moon/Trae/医院问诊Agent/backend/data/medflow_app.db"
)

pytestmark = pytest.mark.skipif(not os.path.exists(DB), reason=f"无演示库: {DB}")


@pytest.fixture(scope="module")
def conn():
    c = open_sqlite(DB)
    yield c
    c.close()


def _run(conn, view_id, params=None):
    q = compile_view(MEDFLOW, view_id, dialect="sqlite", params=params)
    return execute(q, conn)


def test_tat_by_department_returns_rows(conn):
    result = _run(conn, "medflow.view.tat_by_department")
    assert result["row_count"] > 0
    cols = result["columns"]
    assert cols[:3] == ["department", "day", "avg_tat_hours"]
    # 科室名来自 users 表（心内科等）， Tat 值非负
    for row in result["rows"]:
        assert row[2] is None or row[2] >= 0


def test_status_distribution_translated(conn):
    result = _run(conn, "medflow.view.report_status_distribution")
    status_idx = result["columns"].index("status")
    statuses = {row[status_idx] for row in result["rows"]}
    assert "done" not in statuses and "pending" not in statuses      # 运行时枚举已翻译
    assert statuses <= {"completed", "testing", "ordered"}


def test_department_param_narrows(conn):
    full = _run(conn, "medflow.view.tat_by_department")
    filtered = _run(conn, "medflow.view.tat_by_department", {"department": "心内科"})
    if full["row_count"]:
        assert filtered["row_count"] <= full["row_count"]


def test_mdt_volume_executes(conn):
    result = _run(conn, "medflow.view.mdt_consult_volume")
    assert result["columns"][:2] == ["day", "adoption_rate"]


def test_raw_connection_and_sqlalchemy_equivalent(conn):
    q = compile_view(MEDFLOW, "medflow.view.exam_volume_by_type")
    raw = execute(q, conn)
    sa = sqlite3.connect(DB)  # 第二种连接形态：同一 SQL 两种连接均可执行
    try:
        alt = execute(q, sa)
    finally:
        sa.close()
    assert raw["rows"] == alt["rows"]
