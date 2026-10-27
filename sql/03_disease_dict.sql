-- ============================================================
-- 03. disease_dict 疾病字典表
-- 类型:主数据表(对接本体 Disease 类)
-- 依赖:无
-- 说明:疾病编码(ICD-10),通过 disease_code 映射本体 Disease 实例
-- ============================================================

CREATE TABLE disease_dict (
    disease_id    BIGINT PRIMARY KEY AUTO_INCREMENT,
    disease_code  VARCHAR(20) UNIQUE NOT NULL,   -- ICD-10码,接本体 Disease 实例
    name          VARCHAR(100) NOT NULL,
    category      VARCHAR(50),                    -- 心血管/内分泌/呼吸(冗余,主要靠本体)
    is_chronic    BOOLEAN DEFAULT FALSE,          -- 是否慢性病
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
