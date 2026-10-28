"""执行器：CompiledQuery → 结果集 + provenance（铁律 2 的出口）。

连接适配：sqlite3 原生连接与 SQLAlchemy 2.0 Connection 的 ``:name`` 具名参数
均可直接执行；PostgreSQL 侧由消费方（寰宇 codegen 产出的 materialize）做
``:name`` → ``$n`` 物化，本执行器只覆盖 M2 的 SQLite 实跑场景。
"""
from __future__ import annotations

import sqlite3

from .compiler import CompiledQuery


def _execute(conn, sql: str, params: dict):
    cls = type(conn).__mro__[0].__module__
    if cls.startswith("sqlalchemy"):
        from sqlalchemy import text

        return conn.execute(text(sql), params)
    return conn.execute(sql, params)  # sqlite3 / DBAPI


def execute(compiled: CompiledQuery, conn) -> dict:
    """执行编译产物，返回 {columns, rows, sql, params, provenance}。"""
    cursor = _execute(conn, compiled.sql, compiled.params)
    cols = [c[0] for c in cursor.description] if cursor.description else compiled.columns
    rows = [list(r) for r in cursor.fetchall()]
    return {
        "columns": cols,
        "rows": rows,
        "row_count": len(rows),
        "sql": compiled.sql,
        "params": compiled.params,
        "provenance": compiled.provenance,
    }


def open_sqlite(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
