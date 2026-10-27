-- ============================================================
-- 01. department 科室表
-- 类型:主数据表(对接本体 Department 类)
-- 依赖:无
-- 说明:科室信息维护,可自引用形成层级结构
-- ============================================================

CREATE TABLE department (
    dept_id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    dept_code        VARCHAR(20) UNIQUE NOT NULL,    -- 接本体 Department 实例
    name             VARCHAR(50) NOT NULL,
    parent_dept_id   BIGINT,                          -- 上级科室(可选层级)
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_dept_id) REFERENCES department(dept_id)
);
