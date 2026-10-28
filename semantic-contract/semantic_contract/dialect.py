"""SQL 方言适配：日期函数 / 时间窗谓词 / 标识符引用。

设计约定：
- 编译产物统一使用 ``:name`` 具名参数占位；sqlite3 / SQLAlchemy text() 直接消费，
  PostgreSQL 消费方（如 node-pg）负责 ``:name`` → ``$n`` 的物化（见 codegen 产出的 materialize）。
- YAML 的 ``source`` / ``joins[].table`` 写裸标识符，由方言自动加引号（寰宇 camelCase 表名的保障）；
  ``expr`` / ``on`` / ``filters`` 是原样 SQL 片段，由作者负责引号（物理侧，永不进 prompt）。
"""
from __future__ import annotations

import re

_BARE_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class Dialect:
    name = "base"

    def quote(self, ident: str) -> str:
        """裸标识符加引号；已含引号/点号的片段原样返回。"""
        if _BARE_IDENT.match(ident):
            return f'"{ident}"'
        return ident

    def date_expr(self, expr: str) -> str:
        raise NotImplementedError

    def window_predicate(self, anchor: str, days: int) -> str:
        raise NotImplementedError


class SQLiteDialect(Dialect):
    name = "sqlite"

    def date_expr(self, expr: str) -> str:
        return f"date({expr})"

    def window_predicate(self, anchor: str, days: int) -> str:
        return f"date({anchor}) >= date('now', '-{days} days')"


class PostgresDialect(Dialect):
    name = "postgresql"

    def date_expr(self, expr: str) -> str:
        return f"({expr})::date"

    def window_predicate(self, anchor: str, days: int) -> str:
        return f"({anchor})::date >= current_date - {days}"


DIALECTS = {"sqlite": SQLiteDialect(), "postgresql": PostgresDialect()}


def get_dialect(name: str) -> Dialect:
    try:
        return DIALECTS[name]
    except KeyError:
        raise ValueError(f"未知方言: {name}（支持: {sorted(DIALECTS)}）") from None


def parse_translator(text: str) -> list[tuple[str, str]]:
    """解析 'done->completed; pending->testing' → [('done','completed'), ...]"""
    pairs = []
    for part in text.split(";"):
        if "->" in part:
            k, v = part.split("->", 1)
            pairs.append((k.strip(), v.strip()))
    return pairs


def translate_case(expr: str, pairs: list[tuple[str, str]]) -> str:
    """运行时枚举 → 契约枚举的 CASE 翻译。"""
    whens = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in pairs)
    return f"CASE {expr} {whens} ELSE {expr} END"
