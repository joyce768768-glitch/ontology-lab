-- ============================================================
-- 00. 汇总执行文件
-- 按外键依赖顺序执行所有建表 SQL
-- 用法:source 00_run_all.sql
-- ============================================================

-- 数据库初始化(可选,按需修改数据库名)
-- CREATE DATABASE IF NOT EXISTS ontology_hospital DEFAULT CHARSET utf8mb4;
-- USE ontology_hospital;

-- ===== 主数据表(9张)=====
SOURCE 01_department.sql;
SOURCE 02_patient.sql;
SOURCE 03_disease_dict.sql;
SOURCE 04_symptom_dict.sql;
SOURCE 05_drug.sql;
SOURCE 06_lab_test_dict.sql;
SOURCE 07_exam_dict.sql;
SOURCE 08_doctor.sql;
SOURCE 15_disease_symptom.sql;

-- ===== 业务事实表(6张)=====
SOURCE 09_visit.sql;
SOURCE 10_diagnosis.sql;
SOURCE 11_symptom_record.sql;
SOURCE 12_prescription.sql;
SOURCE 13_prescription_item.sql;
SOURCE 14_allergy.sql;

-- ===== 表关系总览(便于回看)=====
-- department ←──┐
--               ├── doctor ←──┐
-- patient ──────┼─────────────┤
--               │             │
--               ↓             ↓
--             visit ──────────┘
--               │
--    ┌──────────┼──────────────┬──────────────┐
--    ↓          ↓              ↓              ↓
--  diagnosis  symptom_record prescription   allergy
--    │          │              │             │
--    ↓          ↓              ↓             ↓
-- disease_dict symptom_dict   prescription_item
--    │          │              │
--    └────┬─────┘              ↓
--         ↓                   drug
--    disease_symptom
--    (知识层:疾病↔症状,推理基础)
--
-- 主数据表(9张,对接本体):
--   department, patient, doctor, disease_dict, symptom_dict,
--   drug, lab_test_dict, exam_dict, disease_symptom
--
-- 业务事实表(6张,只引用码,不接本体):
--   visit, diagnosis, symptom_record, prescription,
--   prescription_item, allergy
