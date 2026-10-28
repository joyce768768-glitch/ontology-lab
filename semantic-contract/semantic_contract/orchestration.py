"""M3 编排参考实现：查询规划 + 校验 + 带依据回答（两域共用）。

M3 双 Agent 编排中与领域无关的部分收拢在此，领域落地各取所需：

- 规划 Agent：planner_prompt 注入纯语义注册表（铁律①：注入语义不注入 DDL），
  LLM 输出 JSON 查询计划；parse_plan 负责解析与结构校验；rule_plan 关键词
  兜底仅在「LLM 输出无法解析为合法计划」时使用（供型策略为强制真 LLM 时，
  规则兜底是解析鲁棒性手段，不是 Mock 演示替代品）。
- 校验 Agent：validate_plan 做视图合法性机判，独立于生成（铁律③）；领域
  特有规则（医疗诊断边界 / 盲盒披露）由各域在调用侧补充。编译期策略机判
  （machine_check）由 compile_view 执行，构成第三道防线。
- 回答组装：answer_prompt 把口径元数据 + 带依据的结果（铁律② provenance）
  交给 LLM 组织回答；数字只允许从结果引用，不从模型记忆生成。

LLM 供型（强制真模型、无 key 即报配置错误）由调用侧执行，本模块不触碰
任何 LLM 传输——只产出 prompt、解析输出、做纯函数校验，全部可单测。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

__all__ = [
    "PlanParseError",
    "PLAN_INTENTS",
    "PLANNER_SYSTEM_TEMPLATE",
    "ANSWER_SYSTEM_TEMPLATE",
    "planner_prompt",
    "parse_plan",
    "rule_plan",
    "validate_plan",
    "answer_prompt",
]


class PlanParseError(ValueError):
    """LLM 输出无法解析为合法查询计划。"""


# 计划中的意图枚举：意图边界校验的数据基础（规则仍以关键词机判为准）
PLAN_INTENTS = (
    "metric_query",          # 指标/统计查询
    "diagnosis_request",     # 诊断请求（医疗域越界意图，校验 Agent 拦截）
    "prescription_request",  # 处方/用药请求（同上）
    "out_of_scope",          # 与数据无关
)

# ============================================================
# 1. 规划 Agent prompt（canonical 模板；TS 侧文本与此对齐）
# ============================================================

PLANNER_SYSTEM_TEMPLATE = """你是「查询规划 Agent」。把用户的自然语言问题映射到语义视图注册表中的唯一视图，输出查询计划 JSON。

【语义视图注册表】（口径唯一真相源；每条含 名称/公式/粒度/时间窗/备注，不含任何物理表结构）
{registry}

【规则】
1. view_id 只能取自注册表中的 id；没有视图能回答时输出 null，禁止臆造。
2. filters 仅当问题明确提到注册表中可作为过滤维度的取值时才填，否则输出 {{}}。
3. intent 必须从以下枚举中选择：{intents}。
4. reasoning 用一句话说明命中依据，必须引用该视图的口径或粒度。
5. 只输出一个 JSON 对象，不要输出任何其他文字：
{{"view_id": "…或null", "intent": "…", "filters": {{}}, "reasoning": "…"}}"""

ANSWER_SYSTEM_TEMPLATE = """你是数据分析助手，基于给定的查询结果回答用户问题。

【回答规则】
1. 数字只能来自【查询结果】，禁止编造、外推或凭记忆补充。
2. 回答必须点明口径：引用视图的指标公式与时间窗，让听者知道数字怎么算出来的。
3. 结果为空时如实说明「没有符合口径的数据」，不得臆测原因。
4. 不回答查询结果与口径之外的问题（如诊断、预测、建议）。
5. 用中文简洁作答，先给结论再给依据。"""

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def planner_prompt(registry: List[dict]) -> str:
    """组装规划 Agent 的 system prompt：只注入纯语义注册表（无物理列名）。"""
    return PLANNER_SYSTEM_TEMPLATE.format(
        registry=json.dumps(registry, ensure_ascii=False, indent=2),
        intents="、".join(PLAN_INTENTS),
    )


# ============================================================
# 2. 计划解析（<json> 标签 / ```json 围栏 / 裸 JSON 三态兼容）
# ============================================================

def parse_plan(raw: str, registry: List[dict]) -> dict:
    """解析 LLM 输出为查询计划；结构不合法抛 PlanParseError。

    只管解析（JSON 形状 / 字段类型），不管语义——view_id 是否在注册表内、
    是否命中 blocked 视图，由 validate_plan（校验 Agent）独立判定并给出
    可解释违规。返回结构：{view_id, intent, filters, reasoning}。
    """
    text = (raw or "").strip()
    m = re.search(r"<json>\s*(\{.*?\})\s*</json>", text, re.DOTALL | re.IGNORECASE)
    json_str = m.group(1) if m else None
    if json_str is None:
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
        json_str = m.group(1) if m else None
    if json_str is None:
        m = _JSON_RE.search(text)
        json_str = m.group(0) if m else None
    if not json_str:
        raise PlanParseError("输出中未找到 JSON 对象")

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise PlanParseError(f"JSON 解析失败: {exc}") from exc
    if not isinstance(data, dict):
        raise PlanParseError("计划不是 JSON 对象")

    view_id = data.get("view_id")
    if view_id is not None:
        view_id = str(view_id).strip() or None

    filters = data.get("filters")
    if not isinstance(filters, dict):
        filters = {}

    return {
        "view_id": view_id,
        "intent": str(data.get("intent") or "metric_query"),
        "filters": filters,
        "reasoning": str(data.get("reasoning") or ""),
    }


# ============================================================
# 3. 规则兜底（仅解析失败时使用；中文 bigram 重叠打分，零依赖）
# ============================================================

def _bigrams(text: str) -> List[str]:
    return [text[i:i + 2] for i in range(len(text) - 1)] if len(text) >= 2 else ([text] if text else [])


def rule_plan(question: str, registry: List[dict]) -> Optional[dict]:
    """关键词规则兜底：按名称/备注与问题的 bigram 重叠度选视图。

    打分口径：name_zh 命中权重 3、notes 权重 1、formula 拉丁词权重 1。
    无任何命中返回 None（调用方按「无对应视图」处理）。
    """
    q = (question or "").strip()
    if not q:
        return None
    best: Optional[tuple] = None  # (score, view, hits)
    for v in registry:
        score, hits = 0, []
        for bg in set(_bigrams(v.get("name_zh", ""))):
            if bg in q:
                score += 3
                hits.append(bg)
        for bg in set(_bigrams(v.get("notes", "") or "")):
            if bg in q:
                score += 1
        for token in re.findall(r"[a-z_]{3,}", v.get("formula") or ""):
            if token in q.lower():
                score += 1
                hits.append(token)
        if score > 0 and (best is None or score > best[0]):
            best = (score, v, hits)
    if best is None:
        return None
    score, v, hits = best
    return {
        "view_id": v["id"],
        "intent": "metric_query",
        "filters": {},
        "reasoning": f"规则兜底命中「{v['name_zh']}」（关键词：{'、'.join(sorted(set(hits))[:4])}）",
        "planner": "rule_fallback",
        "rule_score": score,
    }


# ============================================================
# 4. 校验 Agent：视图合法性机判（领域规则由调用侧补充）
# ============================================================

def validate_plan(plan: dict, entity: dict) -> List[dict]:
    """校验查询计划的视图合法性，返回违规列表（空列表 = 通过）。

    - view_id 为 None：不算违规，调用方按「无对应视图」作答。
    - view_id 命中 blocked 视图：给出治理解释（口径为什么被拦，
      例：盲盒毛利率物理层缺 cost 依赖）——治理活案例的机器可解释出口。
    - view_id 纯臆造（注册表与 blocked 里都没有）：直接违规。
    """
    violations: List[dict] = []
    view_id = plan.get("view_id")
    if not view_id:
        return violations

    registry_ids = {v["id"] for v in entity["semantic_views"] if v.get("status") != "blocked"}
    if view_id in registry_ids:
        return violations

    for v in entity["semantic_views"]:
        if v["id"] == view_id and v.get("status") == "blocked":
            violations.append({
                "rule_id": "SC-V002",
                "severity": "block",
                "message": (
                    f"视图 {view_id}（{v.get('name_zh', '')}）处于 blocked 状态，"
                    f"不可查询：{v.get('notes', '口径未通过治理评审')}"
                ),
            })
            return violations

    violations.append({
        "rule_id": "SC-V002",
        "severity": "block",
        "message": f"view_id 不在语义注册表中（疑似臆造）: {view_id}",
    })
    return violations


# ============================================================
# 5. 回答组装 prompt（口径 + 带依据结果 → LLM 作答）
# ============================================================

def answer_prompt(
    question: str,
    view_meta: dict,
    result: dict,
    max_rows: int = 20,
) -> List[dict]:
    """组装回答 Agent 的 messages。view_meta 取注册表条目（纯语义），
    result 取 execute() 产物（含 sql/provenance，作为引用依据）。
    """
    meta = {
        "id": view_meta.get("id"),
        "name_zh": view_meta.get("name_zh"),
        "formula": view_meta.get("formula"),
        "grain": view_meta.get("grain", []),
        "time_window": view_meta.get("time_window"),
        "notes": view_meta.get("notes"),
    }
    user_content = (
        f"【用户问题】\n{question}\n\n"
        f"【视图口径】\n{json.dumps(meta, ensure_ascii=False, indent=2)}\n\n"
        f"【查询结果】（columns/rows；共 {result.get('row_count', len(result.get('rows', [])))} 行，"
        f"超出 {max_rows} 行截断展示）\n"
        f"columns: {json.dumps(result.get('columns', []), ensure_ascii=False)}\n"
        f"rows: {json.dumps(result.get('rows', [])[:max_rows], ensure_ascii=False, default=str)}\n\n"
        f"【实际执行的 SQL】（仅作为口径依据引用，不向用户展示原文）\n"
        f"{result.get('sql', '')}"
    )
    return [
        {"role": "system", "content": ANSWER_SYSTEM_TEMPLATE},
        {"role": "user", "content": user_content},
    ]
