-- ============================================================
-- 04. symptom_dict 症状字典表
-- 类型:主数据表(对接本体 Symptom 类)
-- 依赖:无
-- 说明:症状编码,通过 symptom_code 映射本体 Symptom 实例
-- ============================================================

CREATE TABLE symptom_dict (
    symptom_id    BIGINT PRIMARY KEY AUTO_INCREMENT,
    symptom_code  VARCHAR(20) UNIQUE NOT NULL,   -- 接本体 Symptom 实例
    name          VARCHAR(100) NOT NULL,
    body_part     VARCHAR(50),                    -- 部位
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
