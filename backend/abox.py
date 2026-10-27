"""ABox 胶水代码:把 MySQL 数据灌入 hospital.owl,生成带实例的本体

流程:
    1. 加载 hospital.owl(TBox + RBox)
    2. 从 MySQL 读 15 张表
    3. 创建 ABox 实例 + 对象属性关系
    4. 保存为 hospital_with_abox.owl
    5. (可选)用 Pellet 推理机做一致性检查 + 隐含关系推理

运行:
    cd /Users/moon/Trae/Ontology研究
    python3 backend/abox.py

输出:
    ontology/hospital_with_abox.owl  (含 TBox + RBox + ABox)

设计原则:
    - 主数据实例用业务编码做 IRI(如 Disease I10、Symptom R51),便于和数据库双向映射
    - 字典类(Disease/Symptom/Drug)用 code,实体类(Patient/Doctor/Visit/Department)用 id
    - 数据属性值用 list 包裹(owlready2 约定:即使单值也用 list)
"""
import os
import sys
import mysql.connector

# 确保能 import 同目录下的 config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import Config

from owlready2 import get_ontology, sync_reasoner_pellet, sync_reasoner_hermit

# ============================================================
# 路径配置
# ============================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ONTOLOGY_DIR = os.path.join(BASE_DIR, "ontology")
TBOX_FILE = os.path.join(ONTOLOGY_DIR, "hospital.owl")
ABOX_FILE = os.path.join(ONTOLOGY_DIR, "hospital_with_abox.owl")

ONTO_IRI = "http://www.semanticweb.org/hospital-ontology"


def get_db():
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE,
        charset=Config.MYSQL_CHARSET,
    )


def fetch_all(cur, sql):
    cur.execute(sql)
    # cur 是 dictionary cursor, fetchall() 已返回 list[dict], 直接返回即可
    return cur.fetchall()


def main():
    # ============================================================
    # 1. 加载 TBox
    # ============================================================
    print(f"[1/5] 加载 TBox: {TBOX_FILE}")
    onto = get_ontology(f"file://{TBOX_FILE}").load()
    print(f"      类: {len(list(onto.classes()))} 个, "
          f"对象属性: {len(list(onto.object_properties()))} 个, "
          f"数据属性: {len(list(onto.data_properties()))} 个")

    # 取类和属性引用
    Patient = onto.Patient
    Doctor = onto.Doctor
    Disease = onto.Disease
    Symptom = onto.Symptom
    Department = onto.Department
    Visit = onto.Visit
    Drug = onto.Drug

    # 数据属性
    has_name = onto.has_name
    has_gender = onto.has_gender
    has_birth_date = onto.has_birth_date
    has_age = onto.has_age
    has_id_card = onto.has_id_card
    has_phone = onto.has_phone
    has_title = onto.has_title
    has_disease_code = onto.has_disease_code
    has_category = onto.has_category
    is_chronic = onto.is_chronic
    has_symptom_code = onto.has_symptom_code
    has_body_part = onto.has_body_part
    has_dept_code = onto.has_dept_code
    has_drug_code = onto.has_drug_code
    has_specification = onto.has_specification
    has_visit_type = onto.has_visit_type
    has_visit_time = onto.has_visit_time
    has_chief_complaint = onto.has_chief_complaint

    # 对象属性
    has_symptom = onto.has_symptom            # Disease → Symptom (知识层)
    has_visit = onto.has_visit                # Patient → Visit
    treated_by = onto.treated_by              # Visit → Doctor
    treated_in = onto.treated_in              # Visit → Department
    recorded_symptom = onto.recorded_symptom  # Visit → Symptom
    diagnosed_with = onto.diagnosed_with      # Visit → Disease
    prescribed_drug = onto.prescribed_drug    # Visit → Drug
    works_in = onto.works_in                  # Doctor → Department
    allergic_to = onto.allergic_to            # Patient → Drug

    # ============================================================
    # 2. 连接数据库
    # ============================================================
    print(f"[2/5] 连接 MySQL: {Config.MYSQL_HOST}:{Config.MYSQL_PORT}/{Config.MYSQL_DATABASE}")
    db = get_db()
    cur = db.cursor(dictionary=True)

    # ============================================================
    # 3. 灌主数据实例(字典类 + 实体类)
    # ============================================================
    print("[3/5] 创建主数据实例...")

    # ---- Department ----
    for row in fetch_all(cur, "SELECT * FROM department"):
        inst = Department(f"dept_{row['dept_id']}")
        inst.has_name = [row["name"]]
        inst.has_dept_code = [row["dept_code"]]
    print(f"      Department: {len(fetch_all(cur, 'SELECT * FROM department'))} 个")

    # ---- Patient ----
    for row in fetch_all(cur, "SELECT * FROM patient"):
        inst = Patient(f"patient_{row['patient_id']}")
        inst.has_name = [row["name"]]
        inst.has_gender = [row["gender"]] if row["gender"] else []
        if row["birth_date"]:
            inst.has_birth_date = [str(row["birth_date"])]
        if row["id_card"]:
            # has_id_card 是 FunctionalProperty, 直接赋单值(不要用列表)
            inst.has_id_card = row["id_card"]
        if row["phone"]:
            inst.has_phone = [row["phone"]]
    print(f"      Patient: {len(fetch_all(cur, 'SELECT * FROM patient'))} 个")

    # ---- Doctor ----
    for row in fetch_all(cur, "SELECT * FROM doctor"):
        inst = Doctor(f"doctor_{row['doctor_id']}")
        inst.has_name = [row["name"]]
        if row["title"]:
            inst.has_title = [row["title"]]
        # works_in: doctor.dept_id → Department
        if row["dept_id"]:
            dept_inst = onto.search_one(iri=f"{ONTO_IRI}#dept_{row['dept_id']}")
            if dept_inst:
                inst.works_in = [dept_inst]
    print(f"      Doctor: {len(fetch_all(cur, 'SELECT * FROM doctor'))} 个")

    # ---- Disease (用 ICD-10 码做 IRI) ----
    for row in fetch_all(cur, "SELECT * FROM disease_dict"):
        code = str(row["disease_code"])
        inst = Disease(code)
        inst.has_name = [row["name"]]
        inst.has_disease_code = [code]
        if row["category"]:
            inst.has_category = [row["category"]]
        inst.is_chronic = [bool(row["is_chronic"])]
    print(f"      Disease: {len(fetch_all(cur, 'SELECT * FROM disease_dict'))} 个")

    # ---- Symptom (用症状码做 IRI,码里的点号替换成下划线避免 IRI 问题) ----
    for row in fetch_all(cur, "SELECT * FROM symptom_dict"):
        raw_code = str(row["symptom_code"])
        iri_code = raw_code.replace(".", "_")
        inst = Symptom(iri_code)
        inst.has_name = [row["name"]]
        inst.has_symptom_code = [raw_code]
        if row["body_part"]:
            inst.has_body_part = [row["body_part"]]
    print(f"      Symptom: {len(fetch_all(cur, 'SELECT * FROM symptom_dict'))} 个")

    # ---- Drug ----
    for row in fetch_all(cur, "SELECT * FROM drug"):
        code = str(row["drug_code"])
        inst = Drug(code)
        inst.has_name = [row["name"]]
        inst.has_drug_code = [code]
        if row["specification"]:
            inst.has_specification = [row["specification"]]
    print(f"      Drug: {len(fetch_all(cur, 'SELECT * FROM drug'))} 个")

    # ---- disease_symptom: 知识层 Disease has_symptom Symptom ----
    ds_rows = fetch_all(cur, "SELECT disease_code, symptom_code, weight, is_primary FROM disease_symptom")
    for row in ds_rows:
        d_code = str(row["disease_code"])
        s_raw = str(row["symptom_code"])
        s_iri = s_raw.replace(".", "_")
        disease_inst = onto.search_one(iri=f"{ONTO_IRI}#{d_code}")
        symptom_inst = onto.search_one(iri=f"{ONTO_IRI}#{s_iri}")
        if disease_inst and symptom_inst:
            disease_inst.has_symptom.append(symptom_inst)
    print(f"      has_symptom (知识层关联): {len(ds_rows)} 条")

    # ============================================================
    # 4. 灌业务事实实例(Visit + 关联关系)
    # ============================================================
    print("[4/5] 创建业务事实实例...")

    # 缓存字典实例,避免反复 search
    disease_cache = {str(r["disease_code"]): onto.search_one(iri=f"{ONTO_IRI}#{r['disease_code']}")
                     for r in fetch_all(cur, "SELECT disease_code FROM disease_dict")}
    symptom_cache = {}
    for r in fetch_all(cur, "SELECT symptom_code FROM symptom_dict"):
        raw = str(r["symptom_code"])
        symptom_cache[raw] = onto.search_one(iri=f"{ONTO_IRI}#{raw.replace('.', '_')}")
    drug_cache = {str(r["drug_code"]): onto.search_one(iri=f"{ONTO_IRI}#{r['drug_code']}")
                  for r in fetch_all(cur, "SELECT drug_code FROM drug")}

    # ---- Visit ----
    for row in fetch_all(cur, "SELECT * FROM visit"):
        vid = row["visit_id"]
        inst = Visit(f"visit_{vid}")
        if row["visit_type"]:
            inst.has_visit_type = [row["visit_type"]]
        if row["visit_time"]:
            inst.has_visit_time = [str(row["visit_time"])]
        if row["chief_complaint"]:
            inst.has_chief_complaint = [row["chief_complaint"]]

        # Patient has_visit
        if row["patient_id"]:
            p = onto.search_one(iri=f"{ONTO_IRI}#patient_{row['patient_id']}")
            if p:
                p.has_visit.append(inst)
        # Visit treated_by Doctor
        if row["doctor_id"]:
            d = onto.search_one(iri=f"{ONTO_IRI}#doctor_{row['doctor_id']}")
            if d:
                inst.treated_by = [d]
        # Visit treated_in Department
        if row["dept_id"]:
            dept = onto.search_one(iri=f"{ONTO_IRI}#dept_{row['dept_id']}")
            if dept:
                inst.treated_in = [dept]

    print(f"      Visit: {len(fetch_all(cur, 'SELECT * FROM visit'))} 个")

    # ---- diagnosis: Visit diagnosed_with Disease ----
    diag_rows = fetch_all(cur, "SELECT visit_id, disease_code FROM diagnosis")
    for row in diag_rows:
        visit_inst = onto.search_one(iri=f"{ONTO_IRI}#visit_{row['visit_id']}")
        disease_inst = disease_cache.get(str(row["disease_code"]))
        if visit_inst and disease_inst:
            visit_inst.diagnosed_with.append(disease_inst)
    print(f"      diagnosed_with: {len(diag_rows)} 条")

    # ---- symptom_record: Visit recorded_symptom Symptom ----
    sr_rows = fetch_all(cur, "SELECT visit_id, symptom_code FROM symptom_record")
    for row in sr_rows:
        visit_inst = onto.search_one(iri=f"{ONTO_IRI}#visit_{row['visit_id']}")
        symptom_inst = symptom_cache.get(str(row["symptom_code"]))
        if visit_inst and symptom_inst:
            visit_inst.recorded_symptom.append(symptom_inst)
    print(f"      recorded_symptom: {len(sr_rows)} 条")

    # ---- prescription + prescription_item: Visit prescribed_drug Drug ----
    rx_rows = fetch_all(cur, """
        SELECT p.visit_id, pi.drug_code
        FROM prescription p
        JOIN prescription_item pi ON p.prescription_id = pi.prescription_id
    """)
    for row in rx_rows:
        visit_inst = onto.search_one(iri=f"{ONTO_IRI}#visit_{row['visit_id']}")
        drug_inst = drug_cache.get(str(row["drug_code"]))
        if visit_inst and drug_inst:
            visit_inst.prescribed_drug.append(drug_inst)
    print(f"      prescribed_drug: {len(rx_rows)} 条")

    # ---- allergy: Patient allergic_to Drug ----
    # 注意:allergy 表 allergen_type 可能不全是药品,这里只处理药品类型
    allergy_rows = fetch_all(cur, """
        SELECT patient_id, allergen_code FROM allergy
        WHERE allergen_type = 'drug' OR allergen_type LIKE '%药%'
    """)
    for row in allergy_rows:
        patient_inst = onto.search_one(iri=f"{ONTO_IRI}#patient_{row['patient_id']}")
        drug_inst = drug_cache.get(str(row["allergen_code"]))
        if patient_inst and drug_inst:
            patient_inst.allergic_to.append(drug_inst)
    print(f"      allergic_to: {len(allergy_rows)} 条")

    cur.close()
    db.close()

    # ============================================================
    # 5. 保存 + 推理验证
    # ============================================================
    print(f"[5/5] 保存到 {ABOX_FILE}")
    onto.save(file=ABOX_FILE, format="rdfxml")

    total_individuals = len(list(onto.individuals()))
    print(f"\n=== ABox 生成完成 ===")
    print(f"实例总数: {total_individuals}")
    print(f"输出文件: {ABOX_FILE}")

    # 可选:推理机验证一致性
    run_reasoner = "--reasoner" in sys.argv
    if run_reasoner:
        print("\n运行 HermiT 推理机...")
        try:
            sync_reasoner_hermit(onto)
            print("✓ 推理完成,本体一致 (consistent)")
            # 打印推理出来的关系示例
            print("\n推理验证示例:")
            # 查一个疾病的症状(知识层)
            flu = onto.search_one(iri=f"{ONTO_IRI}#J11")
            if flu:
                syms = [s.has_name[0] if s.has_name else s.name for s in flu.has_symptom]
                print(f"  流感(J11) 的知识层症状: {syms}")
            # 查一个患者的就诊
            p1 = onto.search_one(iri=f"{ONTO_IRI}#patient_1")
            if p1:
                visits = [v.name for v in p1.has_visit]
                print(f"  patient_1(张三) 的就诊记录: {visits}")
        except Exception as e:
            print(f"✗ 推理失败: {e}")
            print("  (试试 Pellet: 把 sync_reasoner_hermit 改成 sync_reasoner_pellet)")
    else:
        print("\n提示: 加 --reasoner 参数可运行 HermiT 推理机验证一致性")
        print("      或在 Protege 中打开 hospital_with_abox.owl 跑 HermiT")


if __name__ == "__main__":
    main()
