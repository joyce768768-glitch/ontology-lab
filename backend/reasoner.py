"""症状 → 疾病概率推理模块

两种推理方式:
1. SQL 加权打分(基于 disease_symptom 表的 weight)—— 快,适合生产
2. OWL 本体推理(基于 has_symptom 关系)—— 纯逻辑,适合教学演示

推理公式(简化贝叶斯):
    score(disease) = Σ weight(disease, symptom)  for symptom in input_symptoms
    probability(disease) = score(disease) / Σ score(all_diseases)

也可以用"命中率"作为辅助指标:
    hit_ratio(disease) = matched_symptoms / total_symptoms_of_disease
"""
import mysql.connector
from config import Config


def get_db():
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE,
        charset=Config.MYSQL_CHARSET,
    )


def infer_diseases_by_sql(symptom_codes, top_n=5):
    """SQL 加权推理:给定症状码列表,返回最可能的疾病排序

    Args:
        symptom_codes: list[str], 症状编码列表,如 ['R50', 'R05']
        top_n: 返回前 N 个疾病

    Returns:
        list[dict], 每个元素含 disease_code, name, matched_symptoms,
                    total_symptoms, hit_ratio, score, probability
    """
    if not symptom_codes:
        return []

    db = get_db()
    cur = db.cursor(dictionary=True)

    # 1. 查每个疾病命中了哪些输入症状,并求和权重
    placeholders = ",".join(["%s"] * len(symptom_codes))
    sql = f"""
        SELECT
            d.disease_code,
            d.name,
            d.category,
            d.is_chronic,
            COUNT(*) AS matched_symptoms,
            SUM(ds.weight) AS score,
            GROUP_CONCAT(s.name ORDER BY ds.is_primary DESC SEPARATOR '、') AS matched_names
        FROM disease_symptom ds
        JOIN disease_dict d ON d.disease_code = ds.disease_code
        JOIN symptom_dict s ON s.symptom_code = ds.symptom_code
        WHERE ds.symptom_code IN ({placeholders})
        GROUP BY d.disease_code, d.name, d.category, d.is_chronic
        ORDER BY score DESC
    """
    cur.execute(sql, symptom_codes)
    matched = cur.fetchall()

    if not matched:
        cur.close()
        db.close()
        return []

    # 2. 查每个疾病的总症状数(用于算命中率)
    cur.execute("""
        SELECT disease_code, COUNT(*) AS total_symptoms
        FROM disease_symptom
        GROUP BY disease_code
    """)
    total_map = {r["disease_code"]: r["total_symptoms"] for r in cur.fetchall()}

    # 3. 归一化成概率
    total_score = sum(float(r["score"]) for r in matched)
    results = []
    for r in matched:
        total = total_map.get(r["disease_code"], 1)
        results.append({
            "disease_code": r["disease_code"],
            "name": r["name"],
            "category": r["category"],
            "is_chronic": bool(r["is_chronic"]),
            "matched_symptoms": int(r["matched_symptoms"]),
            "total_symptoms": total,
            "hit_ratio": round(int(r["matched_symptoms"]) / total, 3),
            "score": round(float(r["score"]), 3),
            "probability": round(float(r["score"]) / total_score, 3) if total_score else 0,
            "matched_names": r["matched_names"],
        })

    cur.close()
    db.close()
    return results[:top_n]


def infer_diseases_by_ontology(symptom_codes, top_n=5):
    """OWL 本体推理:加载 hospital_with_abox.owl,通过 has_symptom 关系反查疾病

    纯逻辑推理,不使用 weight(OWL 二元关系不存权重)。
    评分方式:命中症状数越多,排名越靠前。

    Args:
        symptom_codes: list[str]
        top_n: int

    Returns:
        list[dict]
    """
    from owlready2 import get_ontology
    import os

    owl_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "ontology", "hospital_with_abox.owl"
    )
    onto = get_ontology(f"file://{owl_path}").load()

    # 找输入症状对应的实例
    input_symptoms = []
    for code in symptom_codes:
        iri_code = code.replace(".", "_")
        sym = onto.search_one(iri=f"http://www.semanticweb.org/hospital-ontology#{iri_code}")
        if sym:
            input_symptoms.append(sym)

    if not input_symptoms:
        return []

    # 遍历所有 Disease 实例,统计命中数
    disease_scores = {}
    for disease in onto.Disease.instances():
        disease_symptoms = set(disease.has_symptom)
        matched = disease_symptoms & set(input_symptoms)
        if matched:
            disease_scores[disease] = len(matched)

    # 排序
    sorted_diseases = sorted(disease_scores.items(), key=lambda x: x[1], reverse=True)
    total_hits = sum(v for v in disease_scores.values())

    results = []
    for disease, hits in sorted_diseases[:top_n]:
        name = disease.has_name[0] if disease.has_name else disease.name
        results.append({
            "disease_code": disease.has_disease_code[0] if disease.has_disease_code else disease.name,
            "name": name,
            "matched_symptoms": hits,
            "total_symptoms": len(disease.has_symptom),
            "hit_ratio": round(hits / len(disease.has_symptom), 3) if disease.has_symptom else 0,
            "probability": round(hits / total_hits, 3) if total_hits else 0,
        })

    return results


def explain_reasoning(symptom_codes, results):
    """生成推理过程的自然语言解释

    Args:
        symptom_codes: list[str] 输入症状
        results: infer_diseases_by_sql 的返回值

    Returns:
        str 人类可读的推理解释
    """
    if not results:
        return f"输入症状 {symptom_codes} 在知识库中未匹配到任何疾病。"

    lines = [f"输入症状 {symptom_codes},推理过程如下:\n"]
    for i, r in enumerate(results, 1):
        lines.append(
            f"{i}. {r['name']}({r['disease_code']})\n"
            f"   命中 {r['matched_symptoms']}/{r['total_symptoms']} 个症状 "
            f"(命中率 {r['hit_ratio']*100:.0f}%)\n"
            f"   加权得分 {r['score']},概率 {r['probability']*100:.1f}%\n"
            f"   命中症状: {r['matched_names']}\n"
        )
    return "\n".join(lines)
