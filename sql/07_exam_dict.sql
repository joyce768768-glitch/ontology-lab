-- ============================================================
-- 07. exam_dict 检查项目字典表
-- 类型:主数据表(对接本体 Exam 类)
-- 依赖:无
-- 说明:影像/超声等检查项目编码
-- ============================================================

CREATE TABLE exam_dict (
    exam_id        BIGINT PRIMARY KEY AUTO_INCREMENT,
    exam_code      VARCHAR(20) UNIQUE NOT NULL,   -- 接本体 Exam 实例
    name           VARCHAR(100) NOT NULL,
    modality       VARCHAR(30),                   -- CT/MRI/超声/X光
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);
