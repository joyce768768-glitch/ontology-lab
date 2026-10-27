-- ============================================================
-- 12. prescription 处方主表
-- 类型:业务事实表
-- 依赖:09_visit, 08_doctor
-- 说明:一次开方事件,可包含多种药品(一对多→明细表)
-- ============================================================

CREATE TABLE prescription (
    prescription_id    BIGINT PRIMARY KEY AUTO_INCREMENT,
    visit_id           BIGINT NOT NULL,
    doctor_id          BIGINT NOT NULL,
    prescription_time  DATETIME NOT NULL,
    status             VARCHAR(20),                  -- 待审/已审/已发药
    FOREIGN KEY (visit_id)  REFERENCES visit(visit_id),
    FOREIGN KEY (doctor_id) REFERENCES doctor(doctor_id)
);
