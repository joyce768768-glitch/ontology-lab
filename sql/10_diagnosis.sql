-- ============================================================
-- 10. diagnosis 诊断记录表
-- 类型:业务事实表
-- 依赖:09_visit, 03_disease_dict, 08_doctor
-- 说明:某次就诊被诊断为什么疾病(disease_code 接本体)
-- ============================================================

CREATE TABLE diagnosis (
    diagnosis_id     BIGINT PRIMARY KEY AUTO_INCREMENT,
    visit_id         BIGINT NOT NULL,
    disease_code     VARCHAR(20) NOT NULL,           -- 通过 code 接本体
    diagnosis_type   VARCHAR(20),                    -- 主诊断/副诊断
    diagnosis_time   DATETIME NOT NULL,
    doctor_id        BIGINT NOT NULL,
    FOREIGN KEY (visit_id)     REFERENCES visit(visit_id),
    FOREIGN KEY (disease_code) REFERENCES disease_dict(disease_code),
    FOREIGN KEY (doctor_id)    REFERENCES doctor(doctor_id),
    INDEX idx_visit (visit_id),
    INDEX idx_disease (disease_code)
);
