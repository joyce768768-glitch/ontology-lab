-- ============================================================
-- 14. allergy 过敏记录表
-- 类型:业务事实表
-- 依赖:02_patient
-- 说明:患者长期属性,不属于某次就诊;开药时必须查询
-- ============================================================

CREATE TABLE allergy (
    allergy_id      BIGINT PRIMARY KEY AUTO_INCREMENT,
    patient_id      BIGINT NOT NULL,
    allergen_type   VARCHAR(30),                    -- 药物/食物/其他
    allergen_code   VARCHAR(30),                    -- 过敏原编码(可接本体)
    severity        VARCHAR(20),                     -- 轻/中/重
    reaction        TEXT,                            -- 反应描述
    recorded_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
    INDEX idx_patient (patient_id)
);
