"""Flask + MySQL 后端,提供 CRUD API + DeepSeek 对话代理

API 设计(REST 风格):
    GET    /api/tables                列出所有表元信息
    GET    /api/<table>               查询某表所有行
    POST   /api/<table>               新增一行  body: {字段名: 值, ...}
    PUT    /api/<table>/<id>          修改一行  body: {字段名: 值, ...}
    DELETE /api/<table>/<id>          删除一行
    POST   /api/chat                  对话代理:把患者自然语言转成结构化 JSON

启动:
    cd backend
    python app.py
"""
import json
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
from config import Config

app = Flask(__name__)
CORS(app)  # 允许前端跨域访问

# ============================================================
# 表元信息配置 - 14 张表
# table: 实际表名 / pk: 主键字段 / fields: 可写字段(不含自增主键)
# ============================================================
TABLES_CONFIG = {
    "department": {
        "label": "科室表",
        "table": "department",
        "pk": "dept_id",
        "fields": ["dept_code", "name", "parent_dept_id"],
    },
    "patient": {
        "label": "患者表",
        "table": "patient",
        "pk": "patient_id",
        "fields": ["name", "gender", "birth_date", "id_card", "phone"],
    },
    "doctor": {
        "label": "医生表",
        "table": "doctor",
        "pk": "doctor_id",
        "fields": ["name", "title", "dept_id"],
    },
    "disease_dict": {
        "label": "疾病字典表",
        "table": "disease_dict",
        "pk": "disease_id",
        "fields": ["disease_code", "name", "category", "is_chronic"],
    },
    "symptom_dict": {
        "label": "症状字典表",
        "table": "symptom_dict",
        "pk": "symptom_id",
        "fields": ["symptom_code", "name", "body_part"],
    },
    "drug": {
        "label": "药品表",
        "table": "drug",
        "pk": "drug_id",
        "fields": ["drug_code", "name", "specification", "unit", "drug_type"],
    },
    "lab_test_dict": {
        "label": "检验项目字典表",
        "table": "lab_test_dict",
        "pk": "lab_test_id",
        "fields": ["lab_test_code", "name", "sample_type"],
    },
    "exam_dict": {
        "label": "检查项目字典表",
        "table": "exam_dict",
        "pk": "exam_id",
        "fields": ["exam_code", "name", "modality"],
    },
    "disease_symptom": {
        "label": "疾病-症状关联表",
        "table": "disease_symptom",
        "pk": "ds_id",
        "fields": ["disease_code", "symptom_code", "weight", "is_primary"],
        # JOIN 配置:list_rows 时把疾病名/症状名预 JOIN 出来
        # 字段 disease_name / symptom_name 是只读 JOIN 结果,不在 fields 里(不可写)
        "joins": [
            {
                "ref_table": "disease_dict",
                "alias": "dd",
                "on": "d.disease_code = dd.disease_code",
                "ref_field": "name",
                "as": "disease_name",
            },
            {
                "ref_table": "symptom_dict",
                "alias": "sd",
                "on": "d.symptom_code = sd.symptom_code",
                "ref_field": "name",
                "as": "symptom_name",
            },
        ],
    },
    "visit": {
        "label": "就诊表",
        "table": "visit",
        "pk": "visit_id",
        "fields": ["patient_id", "doctor_id", "dept_id", "visit_type", "visit_time", "chief_complaint"],
    },
    "diagnosis": {
        "label": "诊断记录表",
        "table": "diagnosis",
        "pk": "diagnosis_id",
        "fields": ["visit_id", "disease_code", "diagnosis_type", "diagnosis_time", "doctor_id"],
    },
    "symptom_record": {
        "label": "症状记录表",
        "table": "symptom_record",
        "pk": "record_id",
        "fields": ["visit_id", "symptom_code", "severity", "duration_days", "recorded_by"],
    },
    "prescription": {
        "label": "处方主表",
        "table": "prescription",
        "pk": "prescription_id",
        "fields": ["visit_id", "doctor_id", "prescription_time", "status"],
    },
    "prescription_item": {
        "label": "处方明细表",
        "table": "prescription_item",
        "pk": "item_id",
        "fields": ["prescription_id", "drug_code", "dosage", "frequency", "duration_days", "quantity"],
    },
    "allergy": {
        "label": "过敏记录表",
        "table": "allergy",
        "pk": "allergy_id",
        "fields": ["patient_id", "allergen_type", "allergen_code", "severity", "reaction"],
    },
}


def get_db():
    """获取 MySQL 连接"""
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE,
        charset=Config.MYSQL_CHARSET,
    )


def to_jsonable(value):
    """把 MySQL 返回值转换为 JSON 可序列化类型"""
    import datetime
    import decimal
    if isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


# ============================================================
# API 路由
# ============================================================

@app.route("/api/tables", methods=["GET"])
def list_tables():
    """列出所有表的元信息"""
    return jsonify({
        key: {
            "label": val["label"],
            "table": val["table"],
            "pk": val["pk"],
            "fields": val["fields"],
        }
        for key, val in TABLES_CONFIG.items()
    })


@app.route("/api/<table>", methods=["GET"])
def list_rows(table):
    """查询某表所有行(支持 JOIN 字段,如 disease_symptom 的 disease_name/symptom_name)"""
    if table not in TABLES_CONFIG:
        return jsonify({"error": f"Unknown table: {table}"}), 404
    cfg = TABLES_CONFIG[table]
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # 如果配置了 JOIN,执行 JOIN 查询(用于显示关联表的外键名称)
    joins = cfg.get("joins")
    if joins:
        select_cols = ["d.*"] + [
            f"{j['alias']}.{j['ref_field']} AS {j['as']}" for j in joins
        ]
        join_clauses = [
            f"LEFT JOIN {j['ref_table']} {j['alias']} ON {j['on']}" for j in joins
        ]
        sql = (
            f"SELECT {', '.join(select_cols)} "
            f"FROM `{cfg['table']}` d {' '.join(join_clauses)}"
        )
        cursor.execute(sql)
    else:
        cursor.execute(f"SELECT * FROM `{cfg['table']}`")
    rows = cursor.fetchall()
    # 转换不可序列化类型
    rows = [{k: to_jsonable(v) for k, v in row.items()} for row in rows]
    cursor.close()
    conn.close()
    return jsonify(rows)


@app.route("/api/<table>", methods=["POST"])
def create_row(table):
    """新增一行"""
    if table not in TABLES_CONFIG:
        return jsonify({"error": f"Unknown table: {table}"}), 404
    cfg = TABLES_CONFIG[table]
    data = request.get_json() or {}
    fields = cfg["fields"]
    values = [data.get(f) for f in fields]
    placeholders = ", ".join(["%s"] * len(fields))
    columns = ", ".join(f"`{f}`" for f in fields)
    sql = f"INSERT INTO `{cfg['table']}` ({columns}) VALUES ({placeholders})"
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(sql, values)
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return jsonify({"id": new_id, "message": "created"}), 201


@app.route("/api/<table>/<int:row_id>", methods=["PUT"])
def update_row(table, row_id):
    """修改一行"""
    if table not in TABLES_CONFIG:
        return jsonify({"error": f"Unknown table: {table}"}), 404
    cfg = TABLES_CONFIG[table]
    data = request.get_json() or {}
    fields = cfg["fields"]
    set_clause = ", ".join(f"`{f}` = %s" for f in fields)
    values = [data.get(f) for f in fields] + [row_id]
    sql = f"UPDATE `{cfg['table']}` SET {set_clause} WHERE `{cfg['pk']}` = %s"
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(sql, values)
    conn.commit()
    affected = cursor.rowcount
    cursor.close()
    conn.close()
    return jsonify({"affected": affected, "message": "updated"})


@app.route("/api/<table>/<int:row_id>", methods=["DELETE"])
def delete_row(table, row_id):
    """删除一行"""
    if table not in TABLES_CONFIG:
        return jsonify({"error": f"Unknown table: {table}"}), 404
    cfg = TABLES_CONFIG[table]
    sql = f"DELETE FROM `{cfg['table']}` WHERE `{cfg['pk']}` = %s"
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(sql, [row_id])
    conn.commit()
    affected = cursor.rowcount
    cursor.close()
    conn.close()
    return jsonify({"affected": affected, "message": "deleted"})


@app.route("/api/health", methods=["GET"])
def health_check():
    """健康检查"""
    return jsonify({
        "status": "ok",
        "database": Config.MYSQL_DATABASE,
        "tables": len(TABLES_CONFIG),
        "deepseek_configured": bool(Config.DEEPSEEK_API_KEY),
    })


# ============================================================
# DeepSeek 对话代理 - 把患者自然语言转成结构化 JSON
# 用途:术语归一化的前置环节,后续胶水代码把 JSON 转 ABox
# ============================================================

# 患者接诊结构化 JSON Schema
# DeepSeek response_format 用,严格约束输出结构
# 关键设计:每个症状既保留原文(raw_description),又给标准化术语名(symptom_name),
# 让后续胶水代码可以通过 symptom_name 反查 symptom_dict 拿到 symptom_code
PATIENT_INTAKE_SCHEMA = {
    "type": "object",
    "properties": {
        "patient": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "患者姓名,未提及填 null"},
                "gender": {"type": "string", "enum": ["M", "F", "unknown"]},
                "age": {"type": "number", "description": "年龄数值,未提及填 null"},
                "age_unit": {"type": "string", "enum": ["year", "month", "day"]},
            },
            "required": ["name", "gender", "age", "age_unit"],
        },
        "chief_complaint": {
            "type": "string",
            "description": "主诉,患者一句话概括的最困扰问题",
        },
        "symptoms": {
            "type": "array",
            "description": "症状列表,每条包含原文 + 标准化术语",
            "items": {
                "type": "object",
                "properties": {
                    "raw_description": {"type": "string", "description": "患者原话(如'头疼得厉害')"},
                    "symptom_name": {"type": "string", "description": "标准化症状名(如'头痛'),便于查 symptom_dict 表"},
                    "body_part": {"type": "string", "enum": ["头部", "胸部", "腹部", "全身", "盆腔", "未知"]},
                    "severity": {"type": "string", "enum": ["轻", "中", "重", "未知"]},
                    "duration_days": {"type": "number", "description": "持续天数,未提及填 null"},
                    "is_primary": {"type": "boolean", "description": "是否主诉症状"},
                },
                "required": ["raw_description", "symptom_name", "body_part", "severity", "duration_days", "is_primary"],
            },
        },
        "vital_signs": {
            "type": "object",
            "properties": {
                "temperature": {"type": "number", "description": "体温 °C,未提及填 null"},
                "heart_rate": {"type": "number", "description": "心率 bpm,未提及填 null"},
                "bp_systolic": {"type": "number", "description": "收缩压 mmHg,未提及填 null"},
                "bp_diastolic": {"type": "number", "description": "舒张压 mmHg,未提及填 null"},
            },
            "required": ["temperature", "heart_rate", "bp_systolic", "bp_diastolic"],
        },
        "visit_type": {"type": "string", "enum": ["初诊", "复诊", "急诊", "未知"]},
        "suspected_diseases": {
            "type": "array",
            "description": "AI 推测的疑似诊断(仅作辅助,不替代医生)",
            "items": {
                "type": "object",
                "properties": {
                    "disease_name": {"type": "string"},
                    "icd_code": {"type": "string", "description": "ICD-10 码,未确定填 null"},
                    "confidence": {"type": "number", "description": "0~1 置信度"},
                },
                "required": ["disease_name", "icd_code", "confidence"],
            },
        },
    },
    "required": ["patient", "chief_complaint", "symptoms", "vital_signs", "visit_type", "suspected_diseases"],
}

SYSTEM_PROMPT = """你是一个医院接诊助手,任务是把患者描述的自然语言转成结构化 JSON。

转换规则:
1. 患者语言可能口语化,需要做轻度术语归一化:
   - "头疼得厉害" → symptom_name="头痛", body_part="头部", severity="重"
   - "胸口闷痛" → symptom_name="胸痛", body_part="胸部"
   - "咳黄痰" → symptom_name="咳痰", body_part="胸部"
   - "拉肚子" → symptom_name="腹泻"(注意:如果不在标准症状集,就写最接近的)
2. 严格不要编造:患者没说的字段填 null (number 类型) 或 "未知" (string enum 类型)
3. is_primary=true 标记主诉症状(只标 1 个,最严重的那个)
4. suspected_diseases 数量限制 1~3 个,基于常识判断,confidence 给粗略值
5. 标准症状集参考(尽量往这个集合里归一):头晕、头痛、嗜睡、记忆障碍、幻觉、
   胸痛、呼吸困难、心悸、发热、疲乏无力、体重减轻、水肿、恶心呕吐、腹痛、腹胀、
   咳嗽、咳痰、排尿疼痛、血尿
6. 必须返回严格符合 JSON Schema 的 JSON,不要任何额外文本、解释、Markdown。
"""

# 历史会话(简化版:全局单会话,后续可扩展为多会话)
CHAT_HISTORY = [{"role": "system", "content": SYSTEM_PROMPT}]


@app.route("/api/chat", methods=["POST"])
def chat():
    """对话代理:接收用户消息,调 DeepSeek,返回结构化 JSON

    请求体: { "message": "患者描述文本" }
    响应: { "raw": "原始 JSON 字符串", "parsed": {...}, "history": [...] }
    """
    if not Config.DEEPSEEK_API_KEY:
        return jsonify({
            "error": "DeepSeek API Key 未配置",
            "hint": "请在 backend/config.py 填 DEEPSEEK_API_KEY,或设置环境变量",
        }), 500

    data = request.get_json() or {}
    user_message = (data.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "message 不能为空"}), 400

    # 追加到历史(限制长度,避免上下文爆炸)
    CHAT_HISTORY.append({"role": "user", "content": user_message})
    if len(CHAT_HISTORY) > 20:
        # 保留 system + 最近 18 条
        del CHAT_HISTORY[1:-18]

    payload = {
        "model": Config.DEEPSEEK_MODEL,
        "messages": CHAT_HISTORY,
        "temperature": Config.DEEPSEEK_TEMPERATURE,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "patient_intake",
                "schema": PATIENT_INTAKE_SCHEMA,
                "strict": True,
            },
        },
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {Config.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            f"{Config.DEEPSEEK_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=60,
        )
        if resp.status_code != 200:
            return jsonify({
                "error": f"DeepSeek API 错误: HTTP {resp.status_code}",
                "detail": resp.text,
            }), 502

        result = resp.json()
        content = result["choices"][0]["message"]["content"]

        # 解析 JSON(理论上一定成功,因为有 response_format 约束)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            return jsonify({
                "error": f"LLM 返回不是合法 JSON: {e}",
                "raw": content,
            }), 502

        # 记录 assistant 回复到历史
        CHAT_HISTORY.append({"role": "assistant", "content": content})

        return jsonify({
            "raw": content,
            "parsed": parsed,
            "history_length": len(CHAT_HISTORY),
        })

    except requests.exceptions.Timeout:
        return jsonify({"error": "DeepSeek API 超时(60s)"}), 504
    except Exception as e:
        return jsonify({"error": f"调用 DeepSeek 失败: {str(e)}"}), 500


@app.route("/api/chat/reset", methods=["POST"])
def chat_reset():
    """清空对话历史"""
    global CHAT_HISTORY
    CHAT_HISTORY = [{"role": "system", "content": SYSTEM_PROMPT}]
    return jsonify({"message": "对话已重置", "history_length": len(CHAT_HISTORY)})


# ============================================================
# 症状 → 疾病概率推理 API
# 基于 disease_symptom 知识表的加权打分
# ============================================================
@app.route("/api/infer", methods=["POST"])
def infer():
    """症状推理:给定症状列表,返回疑似疾病概率排序

    请求体:
        {
            "symptoms": ["R50", "R05", "R51"],   # 症状编码列表(必需)
            "top_n": 5,                          # 返回前 N 个(可选,默认 5)
            "method": "sql"                      # sql(加权) 或 ontology(纯逻辑),默认 sql
        }
    """
    from reasoner import infer_diseases_by_sql, infer_diseases_by_ontology, explain_reasoning

    data = request.get_json() or {}
    symptoms = data.get("symptoms") or []
    top_n = int(data.get("top_n", 5))
    method = data.get("method", "sql")

    if not symptoms:
        return jsonify({"error": "symptoms 不能为空"}), 400

    try:
        if method == "ontology":
            results = infer_diseases_by_ontology(symptoms, top_n)
        else:
            results = infer_diseases_by_sql(symptoms, top_n)

        explanation = explain_reasoning(symptoms, results) if results else ""

        return jsonify({
            "input_symptoms": symptoms,
            "method": method,
            "results": results,
            "explanation": explanation,
        })
    except Exception as e:
        return jsonify({"error": f"推理失败: {str(e)}"}), 500


if __name__ == "__main__":
    print(f"=== 医院本体教学系统 - Flask 后端 ===")
    print(f"数据库: {Config.MYSQL_DATABASE}@{Config.MYSQL_HOST}:{Config.MYSQL_PORT}")
    print(f"启动: http://localhost:{Config.FLASK_PORT}")
    print(f"测试: http://localhost:{Config.FLASK_PORT}/api/health")
    print(f"")
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.DEBUG,
    )
