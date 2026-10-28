# Semantic Contract · 语义契约规范（v0.2）

> 跨项目通用的语义层契约：`concept → physical_mapping → semantic_view → policy` 四段式。
> 电商域（寰宇思贤）与医疗域（MedFlow）验证同一套模式——方法论成立的标志是两个异质域共用它。

## 设计原则（AI 消费数据三条铁律的契约化）

1. **注入语义，不注入 DDL**——Agent 的 prompt 只装 `concept` 和 `semantic_views`，物理表名/字段名永远不出现在 LLM 上下文里
2. **查询结果自带依据**——编译器执行 `semantic_views` 时必须返回 `provenance`（哪个视图、哪个概念、哪个映射），AI 引用时有据可依
3. **规则机器可判**——`policies` 里的每条规则用结构化条件表达（非自然语言），校验 Agent 逐条比对，违反即拦截

## 四段式结构

| 段 | 职责 | 消费者 |
|---|---|---|
| `concept` | 业务概念：语义字段、关系、人读得懂的定义 | 查询规划 Agent（进 prompt）、人类（评审） |
| `physical_mapping` | 语义字段 → 物理表/列的映射（**唯一允许接触物理层的地方**） | 编译器（YAML → SQL/查询） |
| `semantic_views` | 指标视图：公式、聚合粒度、时间窗口 | 查询规划 Agent（NL→视图命中）+ 编译器 |
| `policies` | 治理规则：披露、隐私、一致性，结构化条件 | 校验 Agent（独立于生成，逐条拦截） |

### semantic_views 的 compile 段（v0.2，机器可编译）

`formula` 是进 prompt 的人读口径；`compile` 段是编译器的输入（**物理侧**，与 `physical_mapping` 同权限边界，永不进 prompt）：

```yaml
semantic_views:
  - id: medflow.view.tat_by_department
    name_zh: 科室检验平均周转时间
    formula: "avg(tat_hours) by day, department"        # 人读口径 → LLM prompt
    grain: [day, department]
    time_window: { type: rolling, days: 7, anchor: ordered_at }
    compile:                                            # 机器口径 → 编译器
      source: exam_reports                              # 裸表名，方言自动加引号
      joins:
        - { table: users, "on": "exam_reports.created_by = users.user_id" }
      filters: ["exam_reports.completed_at >= exam_reports.ordered_at"]
      metrics:
        - { name: avg_tat_hours, agg: avg, expr: "(julianday(...) - julianday(...)) * 24.0" }
      dimensions:
        - { name: department, expr: "users.department" }
        - { name: day, expr: "date(exam_reports.ordered_at)" }
```

规则：
- `agg ∈ {sum, avg, count, min, max, none}`；`none` = expr 已是完整聚合表达式（比率类口径）；无 count 指标时自动追加样本量列 `n`
- `dimensions.translate: true` → 从 `physical_mapping.field_map` 的 `translator` 生成运行时枚举 → 契约枚举的 CASE
- 每个 dimension 自动成为可选过滤参数（`:name` 具名占位）
- `time_window` 由方言统一生成 WHERE（sqlite: `date('now','-N days')` / postgresql: `current_date - N`）；anchor 裸列名自动限定到主表
- DSL 表达不了的口径用 `compile.sql` 原生逃生舱（如 PG `FILTER` 子查询），`{time_window}` 占位符可用
- 视图 `status: blocked` → 编译器拒绝、注册表隐藏——**口径依赖不满足不进 production**（治理活案例：huanyu 盲盒毛利率缺 cost 依赖）
- YAML 注意：`on` 是 YAML 1.1 布尔键，flow 写法必须写 `"on":`

### policies 的 machine_check（v0.2）

自然语言 `condition` 之外，可附 `machine_check` 供编译器逐条机器判定（M2 支持视图级绑定）：

```yaml
machine_check:
  views: [medflow.view.tat_by_department, ...]   # 绑定视图（显式列出，Git 可审）
  requires_time_window: true                      # 无显式时间窗 → PolicyViolationError
```

## 编译器（M2 参考实现，两域共用）

```
semantic-contract/
├── README.md
├── pyproject.toml               # pip install -e . （仅依赖 PyYAML，Python ≥3.9）
├── semantic_contract/
│   ├── dialect.py               # sqlite / postgresql 方言适配
│   ├── loader.py                # YAML 加载 + 校验 + 纯语义注册表
│   ├── compiler.py              # compile 段 → 参数化 SQL + provenance + 策略判定
│   ├── executor.py              # SQLite 实跑（:name 具名参数）
│   ├── cli.py / __main__.py
│   └── examples/                # 契约示例（打包为 package data）
│       ├── medflow-exam-report.yaml   # 医疗域：检验报告 × 5 视图
│       ├── huanyu-offering.yaml       # 电商域：卖法/盲盒
│       └── huanyu-order.yaml          # 电商域：订单 × 4 视图
└── tests/
```

```bash
# 纯语义注册表（LLM prompt 注入用，无物理列名）
python -m semantic_contract list medflow
# 视图 → 参数化 SQL
python -m semantic_contract compile medflow --view medflow.view.tat_by_department --param department=心内科
# 生成 TS 视图模块（寰宇消费；:name → $n 物化函数内置）
python -m semantic_contract codegen huanyu-order --out ../huanyusixian/server/ontology/semantic-views.generated.ts
```

消费方式：MedFlow `pip install -e` 直连（REST `/semantic/views`）；寰宇 dev-time codegen（零运行时 Python 依赖）。SQL 产物统一 `:name` 具名参数——sqlite3/SQLAlchemy 直接执行，node-pg 由 codegen 内置的 `materialize()` 转 `$n`。

## 生命周期（Git 即版本管理）

```
draft → reviewed → production
```

- `status` 演进必须发生在独立 commit，commit message 写变更理由（口径审核的落点）
- 修改 `semantic_views` 公式 = 口径变更，必须改 `metadata.version` 并在 `review_note` 记录旧口径 → 新口径
- `physical_mapping` / `compile` 变更（底层表结构动）不影响 concept 消费者——这正是分层收益的验证点

## 文件组织

```
semantic-contract/          # 见上方「编译器」一节（examples 已迁入 semantic_contract/examples/）
```

## 消费方式（M3 编排层接口预览）

- **查询规划 Agent**：读 `concept`（意图解析）+ `semantic_views`（NL→视图命中）→ 输出「视图调用计划」
- **校验 Agent**：读 `policies`，对计划逐条校验 → 放行 / 拦截 + 拒答理由
- **编译器**（M2 交付）：`semantic_views` → 参数化 SQL（寰宇/PostgreSQL、MedFlow/SQLite 各一后端）
