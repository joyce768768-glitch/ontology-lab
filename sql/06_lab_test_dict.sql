-- ============================================================
-- 06. lab_test_dict 检验项目字典表
-- 类型:主数据表(对接本体 LabTest 类)
-- 依赖:无
-- 说明:检验项目编码,如血常规、肝功能等
-- ============================================================

CREATE TABLE lab_test_dict (
    lab_test_id     BIGINT PRIMARY KEY AUTO_INCREMENT,
    lab_test_code   VARCHAR(20) UNIQUE NOT NULL,   -- 接本体 LabTest 实例
    name            VARCHAR(100) NOT NULL,
    sample_type     VARCHAR(30),                    -- 血/尿/便
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
