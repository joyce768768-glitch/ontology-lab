-- ============================================================
-- 11. symptom_record 症状记录表
-- 类型:业务事实表
-- 依赖:09_visit, 04_symptom_dict
-- 说明:某次就诊的主诉/观察到的症状(symptom_code 接本体)
-- ============================================================

CREATE TABLE symptom_record (
    record_id      BIGINT PRIMARY KEY AUTO_INCREMENT,
    visit_id       BIGINT NOT NULL,
    symptom_code   VARCHAR(20) NOT NULL,           -- 通过 code 接本体
    severity       TINYINT,                         -- 1-10 级
    duration_days  INT,                              -- 持续天数
    recorded_by    BIGINT,                           -- 记录人(医生)
    recorded_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (visit_id)      REFERENCES visit(visit_id),
    FOREIGN KEY (symptom_code)  REFERENCES symptom_dict(symptom_code),
    INDEX idx_visit (visit_id),
    INDEX idx_symptom (symptom_code)
);
