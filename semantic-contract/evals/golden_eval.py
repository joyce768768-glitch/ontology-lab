"""L1 黄金集评测执行器 · 寰宇 huanyusixian 语义问答回归（断言式，非 LLM-judge）。

L1 评测三维度（mission-control 线4 v2）：
  ① SQL 正确性断言  —— stage/view/sql 特征机判（sql_contains / sql_not_contains）
  ② 口径披露检查    —— reply 必须点明时间窗与指标口径（reply_groups any-of 组）
  ③ 护栏拦截率      —— 负例必须被三道防线拦截（SC-V001 域边界 / SC-V002 视图合法性 /
                       no_view 如实拒答），且不得编造数字（numbers_from_data，铁律②）

设计原则（对齐契约仓库铁律）：
  - 断言全部规则机判，不用 LLM 评 LLM（judge 校准是 L3 的课题，L1 保持零歧义基线）
  - 目标链路为强制真 LLM（DeepSeek），本脚本只发 HTTP，不做任何 Mock
  - 每次运行产出 Markdown 诊断报告 + 机器可读 JSON（reports/ 下，带时间戳）

用法：
    python -m evals.golden_eval                      # 打 HUANYU_BASE_URL 或默认 localhost:4000
    python -m evals.golden_eval --tag m5-fix         # 报告文件名加标签
    python -m evals.golden_eval --only guardrail     # 只跑某一维度
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
GOLDEN_PATH = HERE / "golden_huanyu.json"
REPORTS_DIR = HERE / "reports"

DIMS = ("sql_correctness", "disclosure", "guardrail")

_NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


# ============================================================
# 1. 链路调用（真 HTTP，真 LLM）
# ============================================================

def call_ask(base_url: str, question: str, timeout: float = 120.0) -> Dict[str, Any]:
    """POST /api/ontology/ask，返回 AskResult dict；HTTP/网络错误统一抛 RuntimeError。"""
    url = base_url.rstrip("/") + "/api/ontology/ask"
    req = urllib.request.Request(
        url,
        data=json.dumps({"question": question}, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"服务不可达 {base_url}: {exc.reason}") from exc
    if not payload.get("success"):
        raise RuntimeError(f"链路报错: {payload.get('message')}")
    return payload["data"]


# ============================================================
# 2. 断言求值（全部规则机判）
# ============================================================

def _norm(text: str) -> str:
    """SQL 比较前小写归一（pg 关键字大小写不稳定）。"""
    return (text or "").lower()


def _reply_has_group(reply: str, group: List[str]) -> bool:
    """any-of 组：组内任一关键词命中即通过。"""
    return any(kw in reply for kw in group)


def _numbers_from_data(reply: str, data: Optional[dict]) -> Dict[str, Any]:
    """铁律②机判：reply 中 >=1000 的数值必须能在查询结果 rows 中找到。

    宽松匹配以容忍格式差异：被逗号分隔/小数舍入的数字，匹配其整数前缀
    （如 reply 写 19,137 或 1.9万 中的 19137 前缀 → 在 rows 文本中找 19137 或 19,137）。
    rows 为空数据时，reply 不应出现 >=1000 的数字。
    """
    blob = json.dumps(data.get("rows", []), ensure_ascii=False, default=str) if data else ""
    blob += " " + json.dumps((data or {}).get("columns", []), ensure_ascii=False)
    offenders: List[str] = []
    for raw in _NUM_RE.findall(reply):
        value = raw.replace(",", "")
        try:
            num = float(value)
        except ValueError:
            continue
        if num < 1000:
            continue
        int_part = str(int(num)) if num == int(num) else value.split(".")[0]
        if int_part not in blob.replace(",", "") and int_part not in blob:
            offenders.append(raw)
    return {"passed": not offenders, "detail": (f"reply 出现结果之外的数字: {offenders}" if offenders else "")}


def evaluate_case(case: dict, result: Dict[str, Any]) -> Dict[str, Any]:
    """对单用例逐断言机判。返回 {id, dim, passed, checks:[{name, passed, detail}]}。"""
    checks: List[dict] = []
    stage = result.get("stage")
    reply = result.get("reply") or ""
    sql = result.get("sql")
    data = result.get("data")
    norm_sql = _norm(sql) if sql else ""

    def check(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    # —— stage 断言（单值或 any-of）——
    expect_stage = case.get("expect_stage")
    expect_stage_any = case.get("expect_stage_any_of")
    if expect_stage:
        check("stage", stage == expect_stage, f"期望 {expect_stage}，实际 {stage}")
    elif expect_stage_any:
        check("stage", stage in expect_stage_any, f"期望 ∈ {expect_stage_any}，实际 {stage}")
    else:
        check("stage", stage == "answered", f"默认期望 answered，实际 {stage}")

    # —— view 断言（仅 answered 时有意义）——
    expect_view = case.get("expect_view")
    expect_view_any = case.get("expect_view_any_of")
    if stage == "answered":
        if expect_view:
            check("view", result.get("view") == expect_view,
                  f"期望 {expect_view}，实际 {result.get('view')}")
        elif expect_view_any:
            check("view", result.get("view") in expect_view_any,
                  f"期望 ∈ {expect_view_any}，实际 {result.get('view')}")

    # —— SQL 正确性断言（维度①）——
    if expect_stage == "answered" or expect_stage_any == ["answered"] or stage == "answered":
        if not sql:
            check("sql_exists", False, "answered 但无 sql")
        else:
            check("sql_exists", True)
            for frag in case.get("sql_contains", []):
                check(f"sql_has:{frag}", frag.lower() in norm_sql, f"SQL 中未找到 {frag!r}")
            for frag in case.get("sql_not_contains", []):
                check(f"sql_not_has:{frag}", frag.lower() not in norm_sql,
                      f"SQL 中出现了禁用片段 {frag!r}（口径事故候选）")

    # —— 口径披露断言（维度②）——
    for i, group in enumerate(case.get("reply_groups", [])):
        ok = _reply_has_group(reply, group)
        check(f"reply_group{i+1}", ok, f"reply 未命中任一关键词 {group}；reply 前 80 字: {reply[:80]!r}")
    for frag in case.get("reply_forbidden", []):
        check(f"reply_forbid:{frag}", frag not in reply, f"reply 出现禁用内容 {frag!r}")

    # —— 护栏断言（维度③）——
    expect_rule = case.get("expect_rule")
    if expect_rule:
        rule_ids = [v.get("rule_id") for v in (result.get("validation") or {}).get("violations", [])]
        check("rule", expect_rule in rule_ids, f"期望违规含 {expect_rule}，实际 {rule_ids}")

    if case.get("numbers_from_data"):
        num_check = _numbers_from_data(reply, data)
        check("numbers_from_data", num_check["passed"], num_check["detail"])

    return {
        "id": case["id"],
        "dim": case["dim"],
        "question": case["question"],
        "passed": all(c["passed"] for c in checks),
        "stage": stage,
        "view": result.get("view"),
        "planner": result.get("planner"),
        "reply": reply,
        "sql": sql,
        "checks": checks,
    }


# ============================================================
# 3. 汇总与报告
# ============================================================

def run_eval(golden_path: Path = GOLDEN_PATH, base_url: Optional[str] = None,
             only_dim: Optional[str] = None, tag: str = "") -> dict:
    """跑全量黄金集，写报告，返回汇总。"""
    with open(golden_path, encoding="utf-8") as f:
        golden = json.load(f)
    base_url = base_url or os.environ.get(
        golden["meta"]["target"]["base_url_env"], golden["meta"]["target"]["default_base_url"]
    )
    cases = [c for c in golden["cases"] if not only_dim or c["dim"] == only_dim]

    results: List[dict] = []
    for case in cases:
        t0 = time.time()
        result: Optional[dict] = None
        error: Optional[str] = None
        # 供型限流鲁棒性：DeepSeek 对连续调用有限流，失败退避重试（真重试，非 Mock 降级）
        for attempt in range(3):
            try:
                result = call_ask(base_url, case["question"])
                error = None
                break
            except RuntimeError as exc:
                error = str(exc)
                if attempt < 2:
                    time.sleep(5.0 * (attempt + 1))
        outcome = evaluate_case(case, result) if result is not None else {
            "id": case["id"], "dim": case["dim"], "question": case["question"],
            "passed": False, "stage": None, "view": None, "planner": None,
            "reply": "", "sql": None, "error": error,
            "checks": [{"name": "call", "passed": False, "detail": error}],
        }
        outcome["latency_s"] = round(time.time() - t0, 1)
        results.append(outcome)
        status = "PASS" if outcome["passed"] else ("ERROR" if outcome.get("error") else "FAIL")
        print(f"[{status}] {case['id']} ({case['dim']}) {case['question']}  [{outcome['latency_s']}s]", flush=True)
        time.sleep(1.0)  # 案例间隔，避免触发供型限流

    summary = _aggregate(results)
    report_md = _render_report(golden, base_url, results, summary, tag)
    REPORTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = f"-{tag}" if tag else ""
    (REPORTS_DIR / f"golden_huanyu_{stamp}{suffix}.md").write_text(report_md, encoding="utf-8")
    (REPORTS_DIR / f"golden_huanyu_{stamp}{suffix}.json").write_text(
        json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def _aggregate(results: List[dict]) -> dict:
    """三层汇总：用例级通过率 / 维度断言通过率 / 护栏拦截率。"""
    dims: Dict[str, dict] = {d: {"assert_total": 0, "assert_passed": 0, "cases": 0, "cases_passed": 0}
                             for d in DIMS}
    for r in results:
        d = dims[r["dim"]]
        d["cases"] += 1
        d["cases_passed"] += 1 if r["passed"] else 0
        for c in r["checks"]:
            d["assert_total"] += 1
            d["assert_passed"] += 1 if c["passed"] else 0
    guardrail = dims["guardrail"]
    stage_ok = sum(
        1 for r in results if r["dim"] == "guardrail"
        for c in r["checks"] if c["name"] == "stage" and c["passed"]
    )
    guardrail_cases = guardrail["cases"]
    return {
        "cases_total": len(results),
        "cases_passed": sum(1 for r in results if r["passed"]),
        "case_pass_rate": round(sum(1 for r in results if r["passed"]) / max(len(results), 1), 3),
        "dims": {
            d: {
                **v,
                "assert_pass_rate": round(v["assert_passed"] / max(v["assert_total"], 1), 3),
                "case_pass_rate": round(v["cases_passed"] / max(v["cases"], 1), 3),
            } for d, v in dims.items()
        },
        "guardrail_block_rate": round(stage_ok / max(guardrail_cases, 1), 3),
        "failed_ids": [r["id"] for r in results if not r["passed"]],
    }


def _render_report(golden: dict, base_url: str, results: List[dict], summary: dict, tag: str) -> str:
    """渲染 Markdown 诊断报告（人读：通过率 + 失败归因 + 缺陷候选清单）。"""
    lines: List[str] = []
    m = golden["meta"]
    lines.append(f"# 寰宇语义问答 · 黄金集诊断报告{('（' + tag + '）') if tag else ''}")
    lines.append("")
    lines.append(f"- 运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 目标链路：`{base_url}{m['target']['endpoint']}`（{m['name']}）")
    lines.append(f"- 供型：强制真 LLM（DeepSeek），无 Mock；断言全部规则机判（L1 不引入 LLM-judge）")
    lines.append(f"- 黄金集版本：{m['version']} · 用例数 {summary['cases_total']}")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append(f"**用例级通过率 {summary['cases_passed']}/{summary['cases_total']}"
                 f"（{summary['case_pass_rate']:.0%}） · 护栏拦截率 {summary['guardrail_block_rate']:.0%}**")
    lines.append("")
    lines.append("| 维度 | 断言通过率 | 用例通过 | 说明 |")
    lines.append("|---|---|---|---|")
    dim_notes = {
        "sql_correctness": "① SQL 正确性断言：视图命中 + SQL 特征 + 口径事故禁用片段",
        "disclosure": "② 口径披露检查：reply 点明时间窗/口径 + 数字可溯源（铁律②）",
        "guardrail": "③ 护栏拦截率：负例被三道防线拦截（SC-V001 / SC-V002 / no_view 如实拒答）",
    }
    for d, v in summary["dims"].items():
        lines.append(f"| {d} | {v['assert_pass_rate']:.0%}（{v['assert_passed']}/{v['assert_total']}） "
                     f"| {v['cases_passed']}/{v['cases']} | {dim_notes[d]} |")
    lines.append("")

    failures = [r for r in results if not r["passed"]]
    if failures:
        lines.append("## 失败用例与归因")
        lines.append("")
        for r in failures:
            lines.append(f"### {r['id']}（{r['dim']}）— 「{r['question']}」")
            if r.get("error"):
                lines.append(f"- **链路错误**：{r['error']}")
            else:
                lines.append(f"- stage={r['stage']} · view={r['view']} · planner={r['planner']}")
            for c in r["checks"]:
                if not c["passed"]:
                    lines.append(f"- ❌ `{c['name']}`：{c['detail']}")
            if r.get("reply"):
                lines.append(f"- reply 摘录：{r['reply'][:160]!r}")
            lines.append("")
    else:
        lines.append("## 无失败用例 ✅")
        lines.append("")

    lines.append("## 全量明细")
    lines.append("")
    lines.append("| 用例 | 维度 | 问题 | stage | view | 结果 | 失败断言 |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in results:
        failed = "、".join(c["name"] for c in r["checks"] if not c["passed"]) or "—"
        lines.append(f"| {r['id']} | {r['dim']} | {r['question']} | {r['stage']} "
                     f"| {r['view'] or '—'} | {'✅' if r['passed'] else '❌'} | {failed} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="寰宇语义问答黄金集回归")
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--tag", default="", help="报告文件名标签，如 m5-fix")
    ap.add_argument("--only", choices=DIMS, default=None, help="只跑某维度")
    args = ap.parse_args()
    summary = run_eval(base_url=args.base_url, only_dim=args.only, tag=args.tag)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
