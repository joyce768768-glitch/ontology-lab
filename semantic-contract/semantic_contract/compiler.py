"""编译器：semantic_views 的 compile 段 → 参数化 SQL + provenance。

分层铁律的落点：
- concept 进 prompt，compile 段永不进 prompt（与 physical_mapping 同属物理侧）；
- 产物自带 provenance（视图/实体/概念定义），AI 引用有据可依；
- policies.machine_check 在编译期机器判定，违反即 PolicyViolationError。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .dialect import Dialect, get_dialect, parse_translator, translate_case
from .loader import find_view


class PolicyViolationError(Exception):
    """编译期策略拦截（policies.machine_check 机器判定）。"""

    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__("策略拦截: " + "; ".join(violations))


@dataclass
class CompiledQuery:
    sql: str
    params: dict = field(default_factory=dict)
    columns: list[str] = field(default_factory=list)
    provenance: dict = field(default_factory=dict)


def _anchor_expr(dialect: Dialect, source_sql: str, anchor: str) -> str:
    """time_window.anchor：裸列名 → 限定到主表；含引号/点号 → 视为已限定片段。"""
    if "." in anchor or '"' in anchor:
        return anchor
    return f"{source_sql}.{anchor}"


def _machine_check(entity: dict, view: dict, dialect_name: str) -> None:
    violations: list[str] = []
    for policy in entity.get("policies", []):
        mc = policy.get("machine_check")
        if not mc or view["id"] not in mc.get("views", []):
            continue
        if mc.get("requires_time_window") and not (view.get("time_window") or {}).get("days"):
            violations.append(
                f"{policy['id']}: 视图 {view['id']} 引用时态指标必须携带显式时间窗口"
                f"（{policy.get('rationale', '')}）"
            )
    if violations:
        raise PolicyViolationError(violations)


def _build_select(view: dict, compile_sec: dict, dialect: Dialect,
                  source_sql: str, field_map: dict) -> tuple[list[str], list[str], int]:
    """返回 (select 片段, 列名序列, group by 维度数)。"""
    columns: list[str] = []
    selects: list[str] = []
    dim_count = 0
    has_count = any(m.get("agg") == "count" for m in compile_sec.get("metrics", []))

    for dim in compile_sec.get("dimensions", []):
        expr = dim["expr"]
        if dim.get("translate"):
            translator = field_map[dim["name"]].get("translator", "")
            expr = translate_case(expr, parse_translator(translator))
        selects.append(f"{expr} AS {dialect.quote(dim['name'])}")
        columns.append(dim["name"])
        dim_count += 1

    for metric in compile_sec.get("metrics", []):
        name = metric["name"]
        agg, expr = metric.get("agg"), metric.get("expr")
        if agg == "count":
            fragment = "count(*)"
        elif agg in (None, "none"):
            fragment = expr
        else:
            fragment = f"{agg}({expr})"
        selects.append(f"{fragment} AS {dialect.quote(name)}")
        columns.append(name)

    if not has_count:  # 样本量随行输出（医疗口径：无样本量的均值不可信）
        selects.append('count(*) AS "n"')
        columns.append("n")
    return selects, columns, dim_count


def compile_view(entity: dict, view_id: str, dialect: str = "sqlite",
                 params: dict | None = None) -> CompiledQuery:
    """语义视图 → 参数化 SQL。params：维度名 → 过滤值（可选）。"""
    params = params or {}
    dx: Dialect = get_dialect(dialect)
    view = find_view(entity, view_id)
    compile_sec = view.get("compile")
    if not compile_sec:
        raise ValueError(f"视图 {view_id} 无 compile 段（status={view.get('status', 'draft')}，不可编译）")

    _machine_check(entity, view, dialect)
    field_map = entity["physical_mapping"].get("field_map", {})

    if "sql" in compile_sec:  # 原生 SQL 逃生舱：DSL 无法表达的口径（如 FILTER 子查询）
        sql = compile_sec["sql"]
        tw = view.get("time_window") or {}
        if "{time_window}" in sql:
            if not tw.get("days") or not tw.get("anchor"):
                raise ValueError(f"视图 {view_id} 使用 {{time_window}} 占位但未定义完整 time_window")
            anchor = _anchor_expr(dx, compile_sec.get("source", ""), tw["anchor"])
            sql = sql.replace("{time_window}", dx.window_predicate(anchor, int(tw["days"])))
        columns = compile_sec.get("columns", [])
        return CompiledQuery(sql=sql, params=dict(params), columns=columns, provenance=_provenance(entity, view, dialect))

    source_sql = dx.quote(compile_sec["source"])
    selects, columns, dim_count = _build_select(view, compile_sec, dx, source_sql, field_map)

    lines = [f"SELECT {', '.join(selects)}" if selects else "SELECT 1", f"FROM {source_sql}"]
    for join in compile_sec.get("joins", []):
        kind = join.get("type", "inner").upper()
        lines.append(f"{kind} JOIN {dx.quote(join['table'])} ON {join['on']}")

    where: list[str] = list(compile_sec.get("filters", []))
    tw = view.get("time_window") or {}
    if tw.get("days") and tw.get("anchor"):
        anchor = _anchor_expr(dx, compile_sec["source"], tw["anchor"])
        where.append(dx.window_predicate(anchor, int(tw["days"])))
    used_params: dict = {}
    for dim in compile_sec.get("dimensions", []):
        if dim["name"] in params:
            where.append(f"{dim['expr']} = :{dim['name']}")
            used_params[dim["name"]] = params[dim["name"]]
    if where:
        lines.append("WHERE " + " AND ".join(where))

    if dim_count:
        lines.append(f"GROUP BY {', '.join(str(i) for i in range(1, dim_count + 1))}")
        lines.append(f"ORDER BY {', '.join(str(i) for i in range(1, dim_count + 1))}")

    return CompiledQuery(
        sql="\n".join(lines),
        params=used_params,
        columns=columns,
        provenance=_provenance(entity, view, dialect),
    )


def _provenance(entity: dict, view: dict, dialect_name: str) -> dict:
    meta = entity["metadata"]
    concept = entity["concept"]
    return {
        "entity": meta["id"],
        "entity_version": meta.get("version"),
        "view": view["id"],
        "name_zh": view["name_zh"],
        "formula": view.get("formula"),
        "grain": view.get("grain", []),
        "time_window": view.get("time_window"),
        "dialect": dialect_name,
        "matched_by": f"semantic_view:{view['id']}",   # 铁律 2：结果带依据
        "concept_fields": {
            f["name"]: f.get("desc", "") for f in concept.get("fields", [])
        },
    }
