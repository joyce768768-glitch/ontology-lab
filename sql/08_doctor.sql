-- ============================================================
-- 08. doctor 医生表
-- 类型:主数据表(对接本体 Doctor 类)
-- 依赖:01_department
-- 说明:医生基础信息,dept_id 外键到 department
-- ============================================================

CREATE TABLE doctor (
    doctor_id      BIGINT PRIMARY KEY AUTO_INCREMENT,
    name           VARCHAR(50) NOT NULL,
    title          VARCHAR(20),                    -- 主任医师/副主任医师/...
    dept_id        BIGINT,                          -- 所属科室
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dept_id) REFERENCES department(dept_id)
);
