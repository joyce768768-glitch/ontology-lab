# Ontology Lab · 本体层实验

AI 产品五层架构（模型→数据→**本体**→编排→语义）中本体层的实验项目：以医疗领域为对象，构建结构化本体，验证「Agent 借助本体层提升检索与推理精度」。

## 结构

- `ontology/` — 本体定义（实体、关系、层级）
- `backend/` — Flask 服务：自然语言 → 结构化查询（DeepSeek 做术语归一化前置）
- `web/` — 查询与可视化界面
- `sql/` — 本体存储（MySQL）

## 运行

```bash
export DEEPSEEK_API_KEY=your_key
export MYSQL_PASSWORD=your_password
cd backend && python app.py
```

## 定位

探索型项目：本体层是 RAG 精度的关键杠杆，本实验验证「结构化语义层对 Agent 查询准确率」的提升路径。
