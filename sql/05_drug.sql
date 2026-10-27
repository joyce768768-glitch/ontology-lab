-- ============================================================
-- 05. drug 药品表
-- 类型:主数据表(对接本体 Drug 类)
-- 依赖:无
-- 说明:药品基础信息,通过 drug_code 映射本体 Drug 实例
-- ============================================================

CREATE TABLE drug (
    drug_id        BIGINT PRIMARY KEY AUTO_INCREMENT,
    drug_code      VARCHAR(20) UNIQUE NOT NULL,   -- 接本体 Drug 实例
    name           VARCHAR(100) NOT NULL,
    specification  VARCHAR(50),                   -- 规格
    unit           VARCHAR(20),                  -- 单位
    drug_type      VARCHAR(30),                  -- 西药/中药
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);
