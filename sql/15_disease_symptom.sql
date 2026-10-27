-- ============================================================
-- 15. disease_symptom 疾病-症状关联表
-- 类型:主数据表(知识层,对接本体 Disease has_symptom Symptom)
-- 依赖:03_disease_dict.sql, 04_symptom_dict.sql
-- 说明:把一个疾病和它对应的症状集合关联起来,
--       weight 表示关联强度(0~1),is_primary 表示是否主要症状
--       本表是"症状 → 疾病"概率推理的知识基础
-- ============================================================

CREATE TABLE disease_symptom (
    ds_id         BIGINT PRIMARY KEY AUTO_INCREMENT,
    disease_code  VARCHAR(20) NOT NULL,           -- FK → disease_dict.disease_code
    symptom_code  VARCHAR(20) NOT NULL,           -- FK → symptom_dict.symptom_code
    weight        DECIMAL(4,2) DEFAULT 1.00,      -- 关联强度 0.00~1.00
    is_primary    BOOLEAN DEFAULT FALSE,         -- 是否主要(标志性)症状
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_disease_symptom (disease_code, symptom_code),
    KEY idx_disease (disease_code),
    KEY idx_symptom (symptom_code),
    CONSTRAINT fk_ds_disease FOREIGN KEY (disease_code) REFERENCES disease_dict(disease_code),
    CONSTRAINT fk_ds_symptom FOREIGN KEY (symptom_code) REFERENCES symptom_dict(symptom_code)
);

-- 注: 测试数据已移至 99_test_data.sql,避免外键约束在字典表数据灌入前失败

