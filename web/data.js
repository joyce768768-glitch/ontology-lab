// ============================================================
// data.js - 医院本体教学系统数据层(14张表)
// 数据来源:sql/99_test_data.sql 的等价 JSON 表示
// ============================================================

const TABLES = {
  // ============================================================
  // 主数据表(8张,对接本体)
  // ============================================================
  department: {
    name: "科室表",
    type: "master",
    typeLabel: "主数据表",
    description: "科室信息维护,可自引用形成层级结构",
    columns: [
      { field: "dept_id", label: "ID", width: 70 },
      { field: "dept_code", label: "科室编码", width: 140, ontology: true },
      { field: "name", label: "名称", width: 140 },
      { field: "parent_dept_id", label: "上级ID", width: 80 },
      { field: "created_at", label: "创建时间", width: 160 }
    ],
    data: [
      { dept_id: 1, dept_code: "DEPT-CARD", name: "心内科", parent_dept_id: null, created_at: "2026-08-22 10:00:00" },
      { dept_id: 2, dept_code: "DEPT-ENDO", name: "内分泌科", parent_dept_id: null, created_at: "2026-08-22 10:00:00" },
      { dept_id: 3, dept_code: "DEPT-RESP", name: "呼吸科", parent_dept_id: null, created_at: "2026-08-22 10:00:00" },
      { dept_id: 4, dept_code: "DEPT-NEUR", name: "神经内科", parent_dept_id: null, created_at: "2026-08-22 10:00:00" },
      { dept_id: 5, dept_code: "DEPT-GAST", name: "消化内科", parent_dept_id: null, created_at: "2026-08-22 10:00:00" }
    ]
  },

  patient: {
    name: "患者表",
    type: "master",
    typeLabel: "主数据表",
    description: "患者基础信息,id_card 字段对应本体 has_id_card (Functional)",
    columns: [
      { field: "patient_id", label: "ID", width: 70 },
      { field: "name", label: "姓名", width: 100 },
      { field: "gender", label: "性别", width: 70 },
      { field: "birth_date", label: "出生日期", width: 130 },
      { field: "id_card", label: "身份证号", width: 200, ontology: true },
      { field: "phone", label: "电话", width: 130 },
      { field: "created_at", label: "创建时间", width: 160 }
    ],
    data: [
      { patient_id: 1, name: "张三", gender: "M", birth_date: "1980-01-01", id_card: "440101199001011234", phone: null, created_at: "2026-08-22 10:00:00" },
      { patient_id: 2, name: "李娜", gender: "F", birth_date: "1975-05-12", id_card: "440106197505123456", phone: null, created_at: "2026-08-22 10:00:00" },
      { patient_id: 3, name: "王五", gender: "M", birth_date: "1990-08-20", id_card: "440111199008201122", phone: null, created_at: "2026-08-22 10:00:00" },
      { patient_id: 4, name: "赵六", gender: "M", birth_date: "1965-03-15", id_card: "440103196503150333", phone: null, created_at: "2026-08-22 10:00:00" },
      { patient_id: 5, name: "孙七", gender: "F", birth_date: "2000-11-30", id_card: "440105200011304444", phone: null, created_at: "2026-08-22 10:00:00" }
    ]
  },

  doctor: {
    name: "医生表",
    type: "master",
    typeLabel: "主数据表",
    description: "医生基础信息,dept_id 外键到 department",
    columns: [
      { field: "doctor_id", label: "ID", width: 70 },
      { field: "name", label: "姓名", width: 100 },
      { field: "title", label: "职称", width: 110 },
      { field: "dept_id", label: "科室ID", width: 90, ref: "department" },
      { field: "created_at", label: "创建时间", width: 160 }
    ],
    data: [
      { doctor_id: 1, name: "李四", title: "主任医师", dept_id: 1, created_at: "2026-08-22 10:00:00" },
      { doctor_id: 2, name: "王医生", title: "副主任医师", dept_id: 2, created_at: "2026-08-22 10:00:00" },
      { doctor_id: 3, name: "陈医生", title: "主治医师", dept_id: 3, created_at: "2026-08-22 10:00:00" },
      { doctor_id: 4, name: "刘医生", title: "主任医师", dept_id: 4, created_at: "2026-08-22 10:00:00" },
      { doctor_id: 5, name: "黄医生", title: "副主任医师", dept_id: 5, created_at: "2026-08-22 10:00:00" }
    ]
  },

  disease_dict: {
    name: "疾病字典表",
    type: "master",
    typeLabel: "主数据表",
    description: "疾病编码(ICD-10),通过 disease_code 映射本体 Disease 实例",
    columns: [
      { field: "disease_id", label: "ID", width: 70 },
      { field: "disease_code", label: "ICD-10码", width: 110, ontology: true },
      { field: "name", label: "疾病名称", width: 200 },
      { field: "category", label: "分类", width: 100 },
      { field: "is_chronic", label: "慢性病", width: 90, type: "boolean" },
      { field: "created_at", label: "创建时间", width: 160 }
    ],
    data: [
      { disease_id: 1, disease_code: "I10", name: "高血压", category: "心血管", is_chronic: true, created_at: "2026-08-22 10:00:00" },
      { disease_id: 2, disease_code: "I20", name: "心绞痛", category: "心血管", is_chronic: true, created_at: "2026-08-22 10:00:00" },
      { disease_id: 3, disease_code: "I21", name: "急性心肌梗死", category: "心血管", is_chronic: false, created_at: "2026-08-22 10:00:00" },
      { disease_id: 4, disease_code: "I50", name: "心力衰竭", category: "心血管", is_chronic: true, created_at: "2026-08-22 10:00:00" },
      { disease_id: 5, disease_code: "I48", name: "心房颤动", category: "心血管", is_chronic: true, created_at: "2026-08-22 10:00:00" },
      { disease_id: 6, disease_code: "E11", name: "2型糖尿病", category: "内分泌", is_chronic: true, created_at: "2026-08-22 10:00:00" },
      { disease_id: 7, disease_code: "E10", name: "1型糖尿病", category: "内分泌", is_chronic: true, created_at: "2026-08-22 10:00:00" },
      { disease_id: 8, disease_code: "E03", name: "甲状腺功能减退", category: "内分泌", is_chronic: true, created_at: "2026-08-22 10:00:00" },
      { disease_id: 9, disease_code: "E05", name: "甲状腺功能亢进", category: "内分泌", is_chronic: true, created_at: "2026-08-22 10:00:00" },
      { disease_id: 10, disease_code: "J00", name: "急性鼻咽炎", category: "呼吸", is_chronic: false, created_at: "2026-08-22 10:00:00" },
      { disease_id: 11, disease_code: "J11", name: "流行性感冒", category: "呼吸", is_chronic: false, created_at: "2026-08-22 10:00:00" },
      { disease_id: 12, disease_code: "J20", name: "急性支气管炎", category: "呼吸", is_chronic: false, created_at: "2026-08-22 10:00:00" },
      { disease_id: 13, disease_code: "J44", name: "慢性阻塞性肺疾病", category: "呼吸", is_chronic: true, created_at: "2026-08-22 10:00:00" },
      { disease_id: 14, disease_code: "J45", name: "支气管哮喘", category: "呼吸", is_chronic: true, created_at: "2026-08-22 10:00:00" },
      { disease_id: 15, disease_code: "K29", name: "胃炎", category: "消化", is_chronic: false, created_at: "2026-08-22 10:00:00" },
      { disease_id: 16, disease_code: "K21", name: "胃食管反流病", category: "消化", is_chronic: true, created_at: "2026-08-22 10:00:00" },
      { disease_id: 17, disease_code: "G43", name: "偏头痛", category: "神经", is_chronic: true, created_at: "2026-08-22 10:00:00" },
      { disease_id: 18, disease_code: "G45", name: "短暂性脑缺血发作", category: "神经", is_chronic: false, created_at: "2026-08-22 10:00:00" },
      { disease_id: 19, disease_code: "N39", name: "尿路感染", category: "泌尿", is_chronic: false, created_at: "2026-08-22 10:00:00" },
      { disease_id: 20, disease_code: "F32", name: "抑郁发作", category: "精神", is_chronic: true, created_at: "2026-08-22 10:00:00" }
    ]
  },

  symptom_dict: {
    name: "症状字典表",
    type: "master",
    typeLabel: "主数据表",
    description: "症状编码,通过 symptom_code 映射本体 Symptom 实例",
    columns: [
      { field: "symptom_id", label: "ID", width: 70 },
      { field: "symptom_code", label: "症状码", width: 110, ontology: true },
      { field: "name", label: "症状名称", width: 160 },
      { field: "body_part", label: "部位", width: 100 },
      { field: "created_at", label: "创建时间", width: 160 }
    ],
    data: [
      { symptom_id: 1, symptom_code: "R42", name: "头晕", body_part: "头部", created_at: "2026-08-22 10:00:00" },
      { symptom_id: 2, symptom_code: "R51", name: "头痛", body_part: "头部", created_at: "2026-08-22 10:00:00" },
      { symptom_id: 3, symptom_code: "R40", name: "嗜睡", body_part: "头部", created_at: "2026-08-22 10:00:00" },
      { symptom_id: 4, symptom_code: "R41", name: "记忆障碍", body_part: "头部", created_at: "2026-08-22 10:00:00" },
      { symptom_id: 5, symptom_code: "R44", name: "幻觉", body_part: "头部", created_at: "2026-08-22 10:00:00" },
      { symptom_id: 6, symptom_code: "R07", name: "胸痛", body_part: "胸部", created_at: "2026-08-22 10:00:00" },
      { symptom_id: 7, symptom_code: "R06", name: "呼吸困难", body_part: "胸部", created_at: "2026-08-22 10:00:00" },
      { symptom_id: 8, symptom_code: "R09", name: "心悸", body_part: "胸部", created_at: "2026-08-22 10:00:00" },
      { symptom_id: 9, symptom_code: "R50", name: "发热", body_part: "全身", created_at: "2026-08-22 10:00:00" },
      { symptom_id: 10, symptom_code: "R53", name: "疲乏无力", body_part: "全身", created_at: "2026-08-22 10:00:00" },
      { symptom_id: 11, symptom_code: "R63", name: "体重减轻", body_part: "全身", created_at: "2026-08-22 10:00:00" },
      { symptom_id: 12, symptom_code: "R54", name: "水肿", body_part: "全身", created_at: "2026-08-22 10:00:00" },
      { symptom_id: 13, symptom_code: "R11", name: "恶心呕吐", body_part: "腹部", created_at: "2026-08-22 10:00:00" },
      { symptom_id: 14, symptom_code: "R10", name: "腹痛", body_part: "腹部", created_at: "2026-08-22 10:00:00" },
      { symptom_id: 15, symptom_code: "R14", name: "腹胀", body_part: "腹部", created_at: "2026-08-22 10:00:00" },
      { symptom_id: 16, symptom_code: "R05", name: "咳嗽", body_part: "胸部", created_at: "2026-08-22 10:00:00" },
      { symptom_id: 17, symptom_code: "R09.1", name: "咳痰", body_part: "胸部", created_at: "2026-08-22 10:00:00" },
      { symptom_id: 18, symptom_code: "R30", name: "排尿疼痛", body_part: "盆腔", created_at: "2026-08-22 10:00:00" },
      { symptom_id: 19, symptom_code: "R31", name: "血尿", body_part: "盆腔", created_at: "2026-08-22 10:00:00" }
    ]
  },

  drug: {
    name: "药品表",
    type: "master",
    typeLabel: "主数据表",
    description: "药品基础信息,通过 drug_code 映射本体 Drug 实例",
    columns: [
      { field: "drug_id", label: "ID", width: 70 },
      { field: "drug_code", label: "药品编码", width: 110, ontology: true },
      { field: "name", label: "药品名称", width: 180 },
      { field: "specification", label: "规格", width: 90 },
      { field: "unit", label: "单位", width: 70 },
      { field: "drug_type", label: "类型", width: 80 },
      { field: "created_at", label: "创建时间", width: 160 }
    ],
    data: [
      { drug_id: 1, drug_code: "C02", name: "可乐定片", specification: "0.1mg", unit: "片", drug_type: "西药", created_at: "2026-08-22 10:00:00" },
      { drug_id: 2, drug_code: "C03", name: "氢氯噻嗪片", specification: "25mg", unit: "片", drug_type: "西药", created_at: "2026-08-22 10:00:00" },
      { drug_id: 3, drug_code: "C07", name: "美托洛尔片", specification: "50mg", unit: "片", drug_type: "西药", created_at: "2026-08-22 10:00:00" },
      { drug_id: 4, drug_code: "C08", name: "氨氯地平片", specification: "5mg", unit: "片", drug_type: "西药", created_at: "2026-08-22 10:00:00" },
      { drug_id: 5, drug_code: "C09", name: "依那普利片", specification: "10mg", unit: "片", drug_type: "西药", created_at: "2026-08-22 10:00:00" },
      { drug_id: 6, drug_code: "A10A", name: "普通胰岛素注射液", specification: "400U", unit: "支", drug_type: "西药", created_at: "2026-08-22 10:00:00" },
      { drug_id: 7, drug_code: "A10B", name: "二甲双胍片", specification: "500mg", unit: "片", drug_type: "西药", created_at: "2026-08-22 10:00:00" },
      { drug_id: 8, drug_code: "H03A", name: "左甲状腺素钠片", specification: "50μg", unit: "片", drug_type: "西药", created_at: "2026-08-22 10:00:00" },
      { drug_id: 9, drug_code: "J01A", name: "阿莫西林胶囊", specification: "500mg", unit: "粒", drug_type: "西药", created_at: "2026-08-22 10:00:00" },
      { drug_id: 10, drug_code: "J01F", name: "阿奇霉素片", specification: "250mg", unit: "片", drug_type: "西药", created_at: "2026-08-22 10:00:00" },
      { drug_id: 11, drug_code: "R03A", name: "沙丁胺醇气雾剂", specification: "100μg", unit: "瓶", drug_type: "西药", created_at: "2026-08-22 10:00:00" },
      { drug_id: 12, drug_code: "R03B", name: "布地奈德吸入剂", specification: "200μg", unit: "瓶", drug_type: "西药", created_at: "2026-08-22 10:00:00" },
      { drug_id: 13, drug_code: "A02B", name: "奥美拉唑肠溶胶囊", specification: "20mg", unit: "粒", drug_type: "西药", created_at: "2026-08-22 10:00:00" },
      { drug_id: 14, drug_code: "A02A", name: "铝碳酸镁咀嚼片", specification: "500mg", unit: "片", drug_type: "西药", created_at: "2026-08-22 10:00:00" },
      { drug_id: 15, drug_code: "N02B", name: "对乙酰氨基酚片", specification: "500mg", unit: "片", drug_type: "西药", created_at: "2026-08-22 10:00:00" }
    ]
  },

  lab_test_dict: {
    name: "检验项目字典表",
    type: "master",
    typeLabel: "主数据表",
    description: "检验项目编码,如血常规、肝功能等",
    columns: [
      { field: "lab_test_id", label: "ID", width: 70 },
      { field: "lab_test_code", label: "检验码", width: 110, ontology: true },
      { field: "name", label: "名称", width: 180 },
      { field: "sample_type", label: "样本类型", width: 110 },
      { field: "created_at", label: "创建时间", width: 160 }
    ],
    data: [
      { lab_test_id: 1, lab_test_code: "CBC", name: "血常规", sample_type: "血", created_at: "2026-08-22 10:00:00" },
      { lab_test_id: 2, lab_test_code: "LFT", name: "肝功能", sample_type: "血", created_at: "2026-08-22 10:00:00" },
      { lab_test_id: 3, lab_test_code: "RFT", name: "肾功能", sample_type: "血", created_at: "2026-08-22 10:00:00" },
      { lab_test_id: 4, lab_test_code: "GLU", name: "血糖", sample_type: "血", created_at: "2026-08-22 10:00:00" },
      { lab_test_id: 5, lab_test_code: "UA", name: "尿常规", sample_type: "尿", created_at: "2026-08-22 10:00:00" }
    ]
  },

  exam_dict: {
    name: "检查项目字典表",
    type: "master",
    typeLabel: "主数据表",
    description: "影像/超声等检查项目编码",
    columns: [
      { field: "exam_id", label: "ID", width: 70 },
      { field: "exam_code", label: "检查码", width: 110, ontology: true },
      { field: "name", label: "名称", width: 180 },
      { field: "modality", label: "设备类型", width: 110 },
      { field: "created_at", label: "创建时间", width: 160 }
    ],
    data: [
      { exam_id: 1, exam_code: "CT", name: "CT扫描", modality: "CT", created_at: "2026-08-22 10:00:00" },
      { exam_id: 2, exam_code: "MRI", name: "磁共振成像", modality: "MRI", created_at: "2026-08-22 10:00:00" },
      { exam_id: 3, exam_code: "US", name: "超声检查", modality: "超声", created_at: "2026-08-22 10:00:00" },
      { exam_id: 4, exam_code: "XR", name: "X光摄影", modality: "X光", created_at: "2026-08-22 10:00:00" },
      { exam_id: 5, exam_code: "ECG", name: "心电图", modality: "心电", created_at: "2026-08-22 10:00:00" }
    ]
  },

  // ============================================================
  // 业务事实表(6张,只引用码,不接本体)
  // ============================================================
  visit: {
    name: "就诊表 ★ 核心枢纽",
    type: "fact",
    typeLabel: "业务事实表",
    description: "一次就诊事件,串联所有业务事实",
    columns: [
      { field: "visit_id", label: "ID", width: 70 },
      { field: "patient_id", label: "患者ID", width: 80, ref: "patient" },
      { field: "patient_name", label: "患者", width: 90, virtual: true },
      { field: "doctor_id", label: "医生ID", width: 80, ref: "doctor" },
      { field: "doctor_name", label: "医生", width: 90, virtual: true },
      { field: "dept_id", label: "科室ID", width: 80, ref: "department" },
      { field: "dept_name", label: "科室", width: 100, virtual: true },
      { field: "visit_type", label: "就诊类型", width: 100 },
      { field: "visit_time", label: "就诊时间", width: 160 },
      { field: "chief_complaint", label: "主诉", width: 200 }
    ],
    data: [
      { visit_id: 1, patient_id: 1, patient_name: "张三", doctor_id: 1, doctor_name: "李四", dept_id: 1, dept_name: "心内科", visit_type: "门诊", visit_time: "2026-08-22 10:00:00", chief_complaint: "头晕半月,加重3天" },
      { visit_id: 2, patient_id: 2, patient_name: "李娜", doctor_id: 2, doctor_name: "王医生", dept_id: 2, dept_name: "内分泌科", visit_type: "门诊", visit_time: "2026-08-22 11:00:00", chief_complaint: "口渴多尿2月,体重减轻" },
      { visit_id: 3, patient_id: 3, patient_name: "王五", doctor_id: 3, doctor_name: "陈医生", dept_id: 3, dept_name: "呼吸科", visit_type: "门诊", visit_time: "2026-08-22 14:00:00", chief_complaint: "咳嗽伴发热5天" },
      { visit_id: 4, patient_id: 4, patient_name: "赵六", doctor_id: 4, doctor_name: "刘医生", dept_id: 4, dept_name: "神经内科", visit_type: "门诊", visit_time: "2026-08-22 15:00:00", chief_complaint: "反复头痛1周" },
      { visit_id: 5, patient_id: 1, patient_name: "张三", doctor_id: 1, doctor_name: "李四", dept_id: 1, dept_name: "心内科", visit_type: "复诊", visit_time: "2026-08-29 10:00:00", chief_complaint: "复诊高血压" },
      { visit_id: 6, patient_id: 5, patient_name: "孙七", doctor_id: 5, doctor_name: "黄医生", dept_id: 5, dept_name: "消化内科", visit_type: "门诊", visit_time: "2026-08-22 16:00:00", chief_complaint: "上腹痛2天" },
      { visit_id: 7, patient_id: 2, patient_name: "李娜", doctor_id: 1, doctor_name: "李四", dept_id: 1, dept_name: "心内科", visit_type: "门诊", visit_time: "2026-09-05 09:00:00", chief_complaint: "活动后气促1月" },
      { visit_id: 8, patient_id: 3, patient_name: "王五", doctor_id: 3, doctor_name: "陈医生", dept_id: 3, dept_name: "呼吸科", visit_type: "复诊", visit_time: "2026-09-10 14:00:00", chief_complaint: "复诊哮喘" }
    ]
  },

  diagnosis: {
    name: "诊断记录表",
    type: "fact",
    typeLabel: "业务事实表",
    description: "某次就诊被诊断为什么疾病(disease_code 接本体)",
    columns: [
      { field: "diagnosis_id", label: "ID", width: 90 },
      { field: "visit_id", label: "就诊ID", width: 80, ref: "visit" },
      { field: "disease_code", label: "疾病码", width: 100, ontology: true, ref: "disease_dict" },
      { field: "disease_name", label: "疾病名称", width: 160, virtual: true },
      { field: "diagnosis_type", label: "诊断类型", width: 100 },
      { field: "diagnosis_time", label: "诊断时间", width: 160 },
      { field: "doctor_id", label: "医生ID", width: 80, ref: "doctor" }
    ],
    data: [
      { diagnosis_id: 1, visit_id: 1, disease_code: "I10", disease_name: "高血压", diagnosis_type: "主诊断", diagnosis_time: "2026-08-22 10:30:00", doctor_id: 1 },
      { diagnosis_id: 2, visit_id: 2, disease_code: "E11", disease_name: "2型糖尿病", diagnosis_type: "主诊断", diagnosis_time: "2026-08-22 11:30:00", doctor_id: 2 },
      { diagnosis_id: 3, visit_id: 3, disease_code: "J11", disease_name: "流行性感冒", diagnosis_type: "主诊断", diagnosis_time: "2026-08-22 14:30:00", doctor_id: 3 },
      { diagnosis_id: 4, visit_id: 4, disease_code: "G43", disease_name: "偏头痛", diagnosis_type: "主诊断", diagnosis_time: "2026-08-22 15:30:00", doctor_id: 4 },
      { diagnosis_id: 5, visit_id: 5, disease_code: "I10", disease_name: "高血压", diagnosis_type: "主诊断", diagnosis_time: "2026-08-29 10:30:00", doctor_id: 1 },
      { diagnosis_id: 6, visit_id: 6, disease_code: "K29", disease_name: "胃炎", diagnosis_type: "主诊断", diagnosis_time: "2026-08-22 16:30:00", doctor_id: 5 },
      { diagnosis_id: 7, visit_id: 7, disease_code: "I50", disease_name: "心力衰竭", diagnosis_type: "主诊断", diagnosis_time: "2026-09-05 09:30:00", doctor_id: 1 },
      { diagnosis_id: 8, visit_id: 7, disease_code: "E11", disease_name: "2型糖尿病", diagnosis_type: "副诊断", diagnosis_time: "2026-09-05 09:30:00", doctor_id: 1 },
      { diagnosis_id: 9, visit_id: 8, disease_code: "J45", disease_name: "支气管哮喘", diagnosis_type: "主诊断", diagnosis_time: "2026-09-10 14:30:00", doctor_id: 3 }
    ]
  },

  symptom_record: {
    name: "症状记录表",
    type: "fact",
    typeLabel: "业务事实表",
    description: "某次就诊的主诉/观察到的症状(symptom_code 接本体)",
    columns: [
      { field: "record_id", label: "ID", width: 70 },
      { field: "visit_id", label: "就诊ID", width: 80, ref: "visit" },
      { field: "symptom_code", label: "症状码", width: 100, ontology: true, ref: "symptom_dict" },
      { field: "symptom_name", label: "症状名称", width: 140, virtual: true },
      { field: "severity", label: "严重度", width: 90, type: "number" },
      { field: "duration_days", label: "持续天数", width: 90, type: "number" },
      { field: "recorded_by", label: "记录人ID", width: 100, ref: "doctor" }
    ],
    data: [
      { record_id: 1, visit_id: 1, symptom_code: "R42", symptom_name: "头晕", severity: 5, duration_days: 15, recorded_by: 1 },
      { record_id: 2, visit_id: 2, symptom_code: "R63", symptom_name: "体重减轻", severity: 4, duration_days: 60, recorded_by: 2 },
      { record_id: 3, visit_id: 2, symptom_code: "R53", symptom_name: "疲乏无力", severity: 3, duration_days: 60, recorded_by: 2 },
      { record_id: 4, visit_id: 3, symptom_code: "R05", symptom_name: "咳嗽", severity: 6, duration_days: 5, recorded_by: 3 },
      { record_id: 5, visit_id: 3, symptom_code: "R50", symptom_name: "发热", severity: 7, duration_days: 5, recorded_by: 3 },
      { record_id: 6, visit_id: 4, symptom_code: "R51", symptom_name: "头痛", severity: 7, duration_days: 7, recorded_by: 4 },
      { record_id: 7, visit_id: 6, symptom_code: "R10", symptom_name: "腹痛", severity: 6, duration_days: 2, recorded_by: 5 },
      { record_id: 8, visit_id: 6, symptom_code: "R11", symptom_name: "恶心呕吐", severity: 4, duration_days: 2, recorded_by: 5 },
      { record_id: 9, visit_id: 7, symptom_code: "R06", symptom_name: "呼吸困难", severity: 6, duration_days: 30, recorded_by: 1 },
      { record_id: 10, visit_id: 7, symptom_code: "R54", symptom_name: "水肿", severity: 5, duration_days: 30, recorded_by: 1 },
      { record_id: 11, visit_id: 8, symptom_code: "R05", symptom_name: "咳嗽", severity: 4, duration_days: 14, recorded_by: 3 },
      { record_id: 12, visit_id: 8, symptom_code: "R09.1", symptom_name: "咳痰", severity: 3, duration_days: 14, recorded_by: 3 }
    ]
  },

  prescription: {
    name: "处方主表",
    type: "fact",
    typeLabel: "业务事实表",
    description: "一次开方事件,可包含多种药品(一对多→明细表)",
    columns: [
      { field: "prescription_id", label: "ID", width: 110 },
      { field: "visit_id", label: "就诊ID", width: 80, ref: "visit" },
      { field: "doctor_id", label: "医生ID", width: 80, ref: "doctor" },
      { field: "prescription_time", label: "开方时间", width: 160 },
      { field: "status", label: "状态", width: 90 }
    ],
    data: [
      { prescription_id: 1, visit_id: 1, doctor_id: 1, prescription_time: "2026-08-22 10:35:00", status: "已审" },
      { prescription_id: 2, visit_id: 2, doctor_id: 2, prescription_time: "2026-08-22 11:35:00", status: "已审" },
      { prescription_id: 3, visit_id: 3, doctor_id: 3, prescription_time: "2026-08-22 14:35:00", status: "已审" },
      { prescription_id: 4, visit_id: 4, doctor_id: 4, prescription_time: "2026-08-22 15:35:00", status: "已审" },
      { prescription_id: 5, visit_id: 5, doctor_id: 1, prescription_time: "2026-08-29 10:35:00", status: "已审" },
      { prescription_id: 6, visit_id: 6, doctor_id: 5, prescription_time: "2026-08-22 16:35:00", status: "已审" },
      { prescription_id: 7, visit_id: 7, doctor_id: 1, prescription_time: "2026-09-05 09:35:00", status: "已审" },
      { prescription_id: 8, visit_id: 8, doctor_id: 3, prescription_time: "2026-09-10 14:35:00", status: "已审" }
    ]
  },

  prescription_item: {
    name: "处方明细表",
    type: "fact",
    typeLabel: "业务事实表",
    description: "处方与药品的多对多拆分表,一个处方可开多种药品",
    columns: [
      { field: "item_id", label: "ID", width: 70 },
      { field: "prescription_id", label: "处方ID", width: 100, ref: "prescription" },
      { field: "drug_code", label: "药品码", width: 100, ontology: true, ref: "drug" },
      { field: "drug_name", label: "药品名称", width: 160, virtual: true },
      { field: "dosage", label: "单次剂量", width: 100, type: "number" },
      { field: "frequency", label: "频次", width: 110 },
      { field: "duration_days", label: "用药天数", width: 100, type: "number" },
      { field: "quantity", label: "总量", width: 90, type: "number" }
    ],
    data: [
      { item_id: 1, prescription_id: 1, drug_code: "C08", drug_name: "氨氯地平片", dosage: 1.00, frequency: "每日1次", duration_days: 30, quantity: 30 },
      { item_id: 2, prescription_id: 1, drug_code: "C07", drug_name: "美托洛尔片", dosage: 1.00, frequency: "每日2次", duration_days: 30, quantity: 60 },
      { item_id: 3, prescription_id: 2, drug_code: "A10B", drug_name: "二甲双胍片", dosage: 1.00, frequency: "每日3次", duration_days: 30, quantity: 90 },
      { item_id: 4, prescription_id: 3, drug_code: "J01F", drug_name: "阿奇霉素片", dosage: 1.00, frequency: "每日1次", duration_days: 5, quantity: 5 },
      { item_id: 5, prescription_id: 3, drug_code: "N02B", drug_name: "对乙酰氨基酚片", dosage: 1.00, frequency: "必要时", duration_days: 5, quantity: 10 },
      { item_id: 6, prescription_id: 4, drug_code: "N02B", drug_name: "对乙酰氨基酚片", dosage: 1.00, frequency: "必要时", duration_days: 7, quantity: 14 },
      { item_id: 7, prescription_id: 5, drug_code: "C08", drug_name: "氨氯地平片", dosage: 1.00, frequency: "每日1次", duration_days: 30, quantity: 30 },
      { item_id: 8, prescription_id: 6, drug_code: "A02B", drug_name: "奥美拉唑肠溶胶囊", dosage: 1.00, frequency: "每日1次", duration_days: 14, quantity: 14 },
      { item_id: 9, prescription_id: 6, drug_code: "A02A", drug_name: "铝碳酸镁咀嚼片", dosage: 1.00, frequency: "每日3次", duration_days: 7, quantity: 21 },
      { item_id: 10, prescription_id: 7, drug_code: "C03", drug_name: "氢氯噻嗪片", dosage: 1.00, frequency: "每日1次", duration_days: 14, quantity: 14 },
      { item_id: 11, prescription_id: 7, drug_code: "C09", drug_name: "依那普利片", dosage: 1.00, frequency: "每日1次", duration_days: 14, quantity: 14 },
      { item_id: 12, prescription_id: 8, drug_code: "R03A", drug_name: "沙丁胺醇气雾剂", dosage: 2.00, frequency: "必要时", duration_days: 30, quantity: 1 },
      { item_id: 13, prescription_id: 8, drug_code: "R03B", drug_name: "布地奈德吸入剂", dosage: 2.00, frequency: "每日2次", duration_days: 30, quantity: 1 }
    ]
  },

  allergy: {
    name: "过敏记录表",
    type: "fact",
    typeLabel: "业务事实表",
    description: "患者长期属性,不属于某次就诊;开药时必须查询",
    columns: [
      { field: "allergy_id", label: "ID", width: 70 },
      { field: "patient_id", label: "患者ID", width: 80, ref: "patient" },
      { field: "patient_name", label: "患者", width: 90, virtual: true },
      { field: "allergen_type", label: "过敏原类型", width: 110 },
      { field: "allergen_code", label: "过敏原编码", width: 130, ontology: true },
      { field: "severity", label: "严重度", width: 90 },
      { field: "reaction", label: "反应描述", width: 200 }
    ],
    data: [
      { allergy_id: 1, patient_id: 1, patient_name: "张三", allergen_type: "药物", allergen_code: "J01A", severity: "中", reaction: "青霉素皮疹" },
      { allergy_id: 2, patient_id: 2, patient_name: "李娜", allergen_type: "药物", allergen_code: "N02A", severity: "重", reaction: "阿片类呼吸困难" },
      { allergy_id: 3, patient_id: 5, patient_name: "孙七", allergen_type: "食物", allergen_code: "FOOD-SEAFOOD", severity: "中", reaction: "海鲜荨麻疹" }
    ]
  },

  // ============================================================
  // 知识层主数据表(9张,推理基础)
  // ============================================================
  disease_symptom: {
    name: "疾病-症状关联表",
    type: "master",
    typeLabel: "主数据表(知识层)",
    description: "把疾病和症状关联起来,weight=关联强度,is_primary=主要症状;是症状→疾病概率推理的知识基础",
    columns: [
      { field: "ds_id", label: "ID", width: 70 },
      { field: "disease_code", label: "疾病码", width: 100, ontology: true, ref: "disease_dict" },
      { field: "disease_name", label: "疾病名称", width: 160, virtual: true },
      { field: "symptom_code", label: "症状码", width: 100, ontology: true, ref: "symptom_dict" },
      { field: "symptom_name", label: "症状名称", width: 140, virtual: true },
      { field: "weight", label: "权重", width: 90, type: "number" },
      { field: "is_primary", label: "主要", width: 80, type: "boolean" },
      { field: "created_at", label: "创建时间", width: 160 }
    ],
    data: [
      { ds_id: 1,  disease_code: "I10", disease_name: "高血压",        symptom_code: "R51",   symptom_name: "头痛",     weight: 0.70, is_primary: true,  created_at: "2026-08-22 10:00:00" },
      { ds_id: 2,  disease_code: "I10", disease_name: "高血压",        symptom_code: "R42",   symptom_name: "头晕",     weight: 0.60, is_primary: false, created_at: "2026-08-22 10:00:00" },
      { ds_id: 3,  disease_code: "I10", disease_name: "高血压",        symptom_code: "R09",   symptom_name: "心悸",     weight: 0.50, is_primary: false, created_at: "2026-08-22 10:00:00" },
      { ds_id: 4,  disease_code: "I20", disease_name: "心绞痛",        symptom_code: "R07",   symptom_name: "胸痛",     weight: 0.90, is_primary: true,  created_at: "2026-08-22 10:00:00" },
      { ds_id: 5,  disease_code: "I21", disease_name: "急性心肌梗死", symptom_code: "R07",   symptom_name: "胸痛",     weight: 0.95, is_primary: true,  created_at: "2026-08-22 10:00:00" },
      { ds_id: 6,  disease_code: "I21", disease_name: "急性心肌梗死", symptom_code: "R06",   symptom_name: "呼吸困难", weight: 0.60, is_primary: false, created_at: "2026-08-22 10:00:00" },
      { ds_id: 7,  disease_code: "I50", disease_name: "心力衰竭",      symptom_code: "R06",   symptom_name: "呼吸困难", weight: 0.80, is_primary: true,  created_at: "2026-08-22 10:00:00" },
      { ds_id: 8,  disease_code: "J11", disease_name: "流行性感冒",    symptom_code: "R50",   symptom_name: "发热",     weight: 0.90, is_primary: true,  created_at: "2026-08-22 10:00:00" },
      { ds_id: 9,  disease_code: "J11", disease_name: "流行性感冒",    symptom_code: "R05",   symptom_name: "咳嗽",     weight: 0.70, is_primary: false, created_at: "2026-08-22 10:00:00" },
      { ds_id: 10, disease_code: "J11", disease_name: "流行性感冒",    symptom_code: "R51",   symptom_name: "头痛",     weight: 0.60, is_primary: false, created_at: "2026-08-22 10:00:00" },
      { ds_id: 11, disease_code: "G43", disease_name: "偏头痛",        symptom_code: "R51",   symptom_name: "头痛",     weight: 0.95, is_primary: true,  created_at: "2026-08-22 10:00:00" },
      { ds_id: 12, disease_code: "N39", disease_name: "尿路感染",      symptom_code: "R30",   symptom_name: "排尿疼痛", weight: 0.85, is_primary: true,  created_at: "2026-08-22 10:00:00" }
    ]
  }
};

// 列标记说明:
// - ontology: true   → 该列通过 code/id 对接本体实例(显示蓝色徽章)
// - ref: "table"     → 该列是外键(显示绿色徽章+可点击跳转)
// - virtual: true    → 该列是 JOIN 出来的展示字段(显示灰色徽章)
// - type: "boolean"  → 布尔值显示为是/否
// - type: "number"   → 数字右对齐
