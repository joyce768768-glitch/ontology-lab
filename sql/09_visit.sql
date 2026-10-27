-- ============================================================
-- 09. visit 就诊表 ★ 核心枢纽表
-- 类型:业务事实表(不接本体,只通过码引用主数据)
-- 依赖:02_patient, 08_doctor, 01_department
-- 说明:一次就诊事件,串联所有业务事实
-- ============================================================

CREATE TABLE visit (
    visit_id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    patient_id        BIGINT NOT NULL,
    doctor_id         BIGINT NOT NULL,
    dept_id           BIGINT NOT NULL,
    visit_type        VARCHAR(20),                  -- 门诊/急诊/住院
    visit_time        DATETIME NOT NULL,
    chief_complaint   TEXT,                          -- 主诉(自由文本)
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
    FOREIGN KEY (doctor_id)  REFERENCES doctor(doctor_id),
    FOREIGN KEY (dept_id)    REFERENCES department(dept_id),
    INDEX idx_visit_time (visit_time),
    INDEX idx_patient (patient_id)
);
