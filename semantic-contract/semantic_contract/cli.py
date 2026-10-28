"""CLI：list / compile / codegen。

    python -m semantic_contract list medflow
    python -m semantic_contract compile medflow --view medflow.view.tat_by_department
    python -m semantic_contract codegen huanyu-order --out ../huanyusixian/server/ontology/semantic-views.generated.ts
"""
from __future__ import annotations

import argparse
import json
import sys

from .compiler import compile_view
from .loader import load_entity, semantic_registry


def _cmd_list(args) -> int:
    entity = load_entity(args.entity)
    meta = entity["metadata"]
    print(json.dumps({
        "entity": meta["id"],
        "version": meta.get("version"),
        "status": meta.get("status"),
        "views": semantic_registry(entity),
    }, ensure_ascii=False, indent=2))
    return 0


def _cmd_compile(args) -> int:
    entity = load_entity(args.entity)
    params = dict(kv.split("=", 1) for kv in args.param) if args.param else {}
    q = compile_view(entity, args.view, dialect=args.dialect, params=params)
    print(json.dumps({
        "sql": q.sql,
        "params": q.params,
        "columns": q.columns,
        "provenance": q.provenance,
    }, ensure_ascii=False, indent=2))
    return 0


def _ts_str(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _cmd_codegen(args) -> int:
    entity = load_entity(args.entity)
    meta = entity["metadata"]
    views = entity["semantic_views"]
    if args.views:
        wanted = {v.strip() for v in args.views.split(",")}
        views = [v for v in views if v["id"] in wanted]
    defs = []
    for view in views:
        if view.get("status") == "blocked":
            continue
        q = compile_view(entity, view["id"], dialect=args.dialect)
        tw = view.get("time_window") or {}
        defs.append({
            "id": view["id"], "nameZh": view["name_zh"],
            "formula": view.get("formula", ""), "grain": view.get("grain", []),
            "timeWindow": {"type": tw.get("type", ""), "days": tw.get("days", 0),
                           "anchor": tw.get("anchor", "")},
            "notes": view.get("notes", ""),
            "dialect": args.dialect, "sql": q.sql,
        })
    ts = _render_ts(meta, defs)
    if args.out:
        from pathlib import Path

        Path(args.out).write_text(ts, encoding="utf-8")
        print(f"✓ {len(defs)} views → {args.out}", file=sys.stderr)
    else:
        print(ts)
    return 0


def _render_ts(meta: dict, defs: list[dict]) -> str:
    body = json.dumps(defs, ensure_ascii=False, indent=2)
    lines = [
        "// ================================================================",
        "// 自动生成：semantic-contract compiler codegen（勿手改，Git 即版本）",
        f"// 实体：{meta['id']} v{meta.get('version')} · 方言：{defs[0]['dialect'] if defs else '-'}",
        "// 重新生成：python -m semantic_contract codegen <entity> --out <本文件>",
        "// ================================================================",
        "",
        "export interface SemanticTimeWindow { type: string; days: number; anchor: string; }",
        "",
        "export interface SemanticViewDef {",
        "  id: string;",
        "  nameZh: string;",
        "  formula: string;",
        "  grain: string[];",
        "  timeWindow: SemanticTimeWindow;",
        "  notes: string;",
        "  dialect: string;",
        "  sql: string;",
        "}",
        "",
        f"export const semanticViews: SemanticViewDef[] = {body};",
        "",
        "export function findView(id: string): SemanticViewDef | undefined {",
        "  return semanticViews.find((v) => v.id === id);",
        "}",
        "",
        "export function viewRegistry() {",
        "  return semanticViews.map(({ sql: _sql, ...meta }) => meta); // 纯语义，供 LLM prompt 注入",
        "}",
        "",
        "/** :name 具名参数 → node-pg 的 $n 物化 */",
        "export function materialize(",
        "  sql: string,",
        "  params: Record<string, unknown> = {},",
        "): { text: string; values: unknown[] } {",
        "  const values: unknown[] = [];",
        "  const text = sql.replace(/:(\\w+)/g, (_m, name: string) => {",
        "    if (!(name in params)) return `:${name}`;",
        "    values.push(params[name]);",
        "    return `$${values.length}`;",
        "  });",
        "  return { text, values };",
        "}",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="semantic_contract", description="语义契约编译器")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="纯语义视图注册表（LLM prompt 用）")
    p_list.add_argument("entity")
    p_list.set_defaults(func=_cmd_list)

    p_compile = sub.add_parser("compile", help="视图 → 参数化 SQL")
    p_compile.add_argument("entity")
    p_compile.add_argument("--view", required=True)
    p_compile.add_argument("--dialect", default="sqlite", choices=["sqlite", "postgresql"])
    p_compile.add_argument("--param", action="append", help="维度过滤 k=v，可多次")
    p_compile.set_defaults(func=_cmd_compile)

    p_gen = sub.add_parser("codegen", help="生成 TS 视图模块（寰宇消费）")
    p_gen.add_argument("entity")
    p_gen.add_argument("--dialect", default="postgresql", choices=["sqlite", "postgresql"])
    p_gen.add_argument("--out", help="输出 .ts 路径（缺省打印 stdout）")
    p_gen.add_argument("--views", help="逗号分隔视图 id 过滤")
    p_gen.set_defaults(func=_cmd_codegen)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
