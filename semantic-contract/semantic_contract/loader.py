"""契约 YAML 加载与最小校验。"""
from __future__ import annotations

import os
from pathlib import Path

import yaml

_EXAMPLES_DIR = Path(__file__).parent / "examples"

# 短名 → 打包示例文件（metadata.id 的域名前缀即短名来源）
REGISTRY = {
    "medflow": "medflow-exam-report.yaml",
    "huanyu-offering": "huanyu-offering.yaml",
    "huanyu-order": "huanyu-order.yaml",
}

REQUIRED_SECTIONS = ("metadata", "concept", "physical_mapping", "semantic_views", "policies")


def load(path: str | os.PathLike) -> dict:
    """加载契约 YAML 并做结构校验（四段式 + 视图 id 唯一）。"""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    for section in REQUIRED_SECTIONS:
        if section not in data:
            raise ValueError(f"{path}: 缺少必需段 {section}")
    view_ids = [v["id"] for v in data["semantic_views"]]
    if len(view_ids) != len(set(view_ids)):
        dupes = {i for i in view_ids if view_ids.count(i) > 1}
        raise ValueError(f"{path}: 视图 id 重复: {dupes}")
    return data


def load_entity(ref: str) -> dict:
    """按路径或注册短名加载。短名：medflow / huanyu-offering / huanyu-order。"""
    if ref.endswith(".yaml"):
        return load(ref)
    try:
        return load(_EXAMPLES_DIR / REGISTRY[ref])
    except KeyError:
        raise KeyError(f"未知契约短名: {ref}（可用: {sorted(REGISTRY)} 或传 YAML 路径）") from None


def find_view(entity: dict, view_id: str) -> dict:
    for v in entity["semantic_views"]:
        if v["id"] == view_id:
            return v
    known = [v["id"] for v in entity["semantic_views"]]
    raise KeyError(f"视图 {view_id} 不在 {entity['metadata']['id']} 中（可用: {known}）")


def semantic_registry(entity: dict) -> list[dict]:
    """纯语义注册表：注入 LLM prompt 的部分（无任何物理列名）。"""
    return [
        {
            "id": v["id"],
            "name_zh": v["name_zh"],
            "formula": v.get("formula"),
            "grain": v.get("grain", []),
            "time_window": v.get("time_window"),
            "notes": v.get("notes"),
        }
        for v in entity["semantic_views"]
        if v.get("status") != "blocked"
    ]
