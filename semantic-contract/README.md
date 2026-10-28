# Semantic Contract · 语义契约规范（v0.1）

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

## 生命周期（Git 即版本管理）

```
draft → reviewed → production
```

- `status` 演进必须发生在独立 commit，commit message 写变更理由（口径审核的落点）
- 修改 `semantic_views` 公式 = 口径变更，必须改 `metadata.version` 并在 `review_note` 记录旧口径 → 新口径
- `physical_mapping` 变更（底层表结构动）不影响 concept 消费者——这正是分层收益的验证点

## 文件组织

```
semantic-contract/
├── README.md            # 本规范
└── examples/
    ├── huanyu-offering.yaml      # 电商域示范：卖法/盲盒（寰宇思贤）
    └── medflow-exam-report.yaml  # 医疗域示范：检验报告（MedFlow）
```

## 消费方式（M3 编排层接口预览）

- **查询规划 Agent**：读 `concept`（意图解析）+ `semantic_views`（NL→视图命中）→ 输出「视图调用计划」
- **校验 Agent**：读 `policies`，对计划逐条校验 → 放行 / 拦截 + 拒答理由
- **编译器**（M2 交付）：`semantic_views` → 参数化 SQL（寰宇/PostgreSQL、MedFlow/SQLite 各一后端）
