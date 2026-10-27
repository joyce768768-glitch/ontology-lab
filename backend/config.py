"""MySQL & Flask 配置

可通过环境变量覆盖,也可直接改本文件。
示例:
    export MYSQL_PASSWORD=your_password
    python app.py
"""
import os


class Config:
    # MySQL 连接
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")   # ← 改成你的 MySQL 密码
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "ontology_hospital")
    MYSQL_CHARSET = "utf8mb4"

    # Flask 服务
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    DEBUG = True

    # DeepSeek API(用于自然语言 → 结构化 JSON,术语归一化前置)
    # 通过环境变量 DEEPSEEK_API_KEY 提供,勿在代码中硬编码
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    DEEPSEEK_TEMPERATURE = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.2"))
