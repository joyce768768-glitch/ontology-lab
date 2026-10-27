-- ============================================================
-- 02. patient 患者表
-- 类型:主数据表(对接本体 Patient 类)
-- 依赖:无
-- 说明:患者基础信息,id_card 字段对应本体 has_id_card (Functional)
-- ============================================================

CREATE TABLE patient (
    patient_id   BIGINT PRIMARY KEY AUTO_INCREMENT,
    name         VARCHAR(50) NOT NULL,
    gender       CHAR(1),                        -- M/F
    birth_date   DATE,
    id_card      VARCHAR(18) UNIQUE,             -- 身份证号(接本体 has_id_card Functional)
    phone        VARCHAR(20),
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
