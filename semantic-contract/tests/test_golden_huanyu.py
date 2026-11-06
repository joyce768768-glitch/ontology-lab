"""L1 黄金集回归 · pytest 接入口（真链路评测，非单元测试）。

与 evals/golden_eval.py 共用断言逻辑；目标链路为强制真 LLM（DeepSeek）+
真实 PG，单条用例两次 LLM 调用。默认跳过，避免 `pytest tests/` 全量跑单元
测试时意外触发 20 次真模型调用；显式开启：

    RUN_GOLDEN_EVAL=1 pytest tests/test_golden_huanyu.py -v

服务未启动时自动 SKIP（不会误报失败）。CI/回归接入见 evals/golden_eval.py。
"""
import json
import os
from pathlib import Path

import pytest

from evals.golden_eval import call_ask, evaluate_case

HERE = Path(__file__).resolve().parent
GOLDEN_PATH = HERE.parent / "evals" / "golden_huanyu.json"
BASE_URL = os.environ.get("HUANYU_BASE_URL", "http://127.0.0.1:4000")

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_GOLDEN_EVAL") != "1",
    reason="黄金集为真 LLM 回归评测，需 RUN_GOLDEN_EVAL=1 显式开启（避免混入单元测试全量跑）",
)

with open(GOLDEN_PATH, encoding="utf-8") as _f:
    _GOLDEN = json.load(_f)


def _service_up() -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen(BASE_URL + "/api/ontology/views", timeout=3):
            return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def _up() -> None:
    if not _service_up():
        pytest.skip(f"寰宇服务未启动（{BASE_URL}），黄金集回归跳过")


@pytest.mark.parametrize(
    "case",
    _GOLDEN["cases"],
    ids=[c["id"] for c in _GOLDEN["cases"]],
)
def test_golden_case(case: dict, _up: None):
    result = call_ask(BASE_URL, case["question"])
    outcome = evaluate_case(case, result)
    failed = [c for c in outcome["checks"] if not c["passed"]]
    assert not failed, (
        f"{case['id']} 失败断言: "
        + "; ".join(f"{c['name']}: {c['detail']}" for c in failed)
    )
