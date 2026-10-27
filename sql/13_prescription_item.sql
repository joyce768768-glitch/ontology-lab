-- ============================================================
-- 13. prescription_item 处方明细表
-- 类型:业务事实表
-- 依赖:12_prescription, 05_drug
-- 说明:处方与药品的多对多拆分表,一个处方可开多种药品
-- ============================================================

CREATE TABLE prescription_item (
    item_id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    prescription_id  BIGINT NOT NULL,
    drug_code        VARCHAR(20) NOT NULL,           -- 通过 code 接本体
    dosage           DECIMAL(10,2),                   -- 单次剂量
    frequency        VARCHAR(30),                     -- 每日3次/每晚1次
    duration_days    INT,                              -- 用药天数
    quantity         DECIMAL(10,2),                   -- 总量
    FOREIGN KEY (prescription_id) REFERENCES prescription(prescription_id),
    FOREIGN KEY (drug_code)       REFERENCES drug(drug_code)
);
