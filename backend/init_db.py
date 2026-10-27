"""一键初始化数据库

执行流程:
1. 连接 MySQL(不指定库)
2. 创建数据库 ontology_hospital
3. 依次执行 sql/01-08(主数据建表)
4. 依次执行 sql/09-14(业务事实建表)
5. 执行 sql/99_test_data.sql(灌测试数据)

用法:
    cd backend
    python init_db.py
"""
import os
import re
import sys
import mysql.connector
from config import Config

SQL_DIR = os.path.join(os.path.dirname(__file__), "..", "sql")


def split_sql_statements(sql_text):
    """简单 SQL 分号切分,跳过注释行和 SOURCE 语句"""
    statements = []
    current = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        if stripped.upper().startswith("SOURCE"):
            continue  # 跳过 MySQL 客户端专有 SOURCE 命令
        current.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(current))
            current = []
    if current:
        statements.append("\n".join(current))
    return statements


def init_database():
    print(f"=== 初始化数据库 {Config.MYSQL_DATABASE} ===")
    print(f"MySQL: {Config.MYSQL_USER}@{Config.MYSQL_HOST}:{Config.MYSQL_PORT}")

    # 1. 创建数据库
    conn = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
    )
    cursor = conn.cursor()
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{Config.MYSQL_DATABASE}` "
        f"DEFAULT CHARACTER SET {Config.MYSQL_CHARSET}"
    )
    conn.commit()
    cursor.close()
    conn.close()
    print(f"[1/3] 数据库已创建: {Config.MYSQL_DATABASE}")

    # 2. 连到数据库,执行建表 SQL(按文件名顺序)
    conn = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE,
        charset=Config.MYSQL_CHARSET,
    )
    cursor = conn.cursor()

    sql_files = sorted([
        f for f in os.listdir(SQL_DIR)
        if f.endswith(".sql") and f[0].isdigit() and not f.startswith("99")
    ])

    for sql_file in sql_files:
        path = os.path.join(SQL_DIR, sql_file)
        print(f"  - 执行 {sql_file}")
        with open(path, "r", encoding="utf-8") as f:
            sql_text = f.read()
        for stmt in split_sql_statements(sql_text):
            try:
                cursor.execute(stmt)
            except mysql.connector.Error as e:
                print(f"    ✗ {sql_file} 语句执行失败: {e}")
                print(f"    SQL(前120字): {stmt.strip()[:120]}")
                conn.rollback()
                cursor.close()
                conn.close()
                sys.exit(1)
    conn.commit()
    print(f"[2/3] 已创建 {len(sql_files)} 张表")

    # 3. 灌测试数据
    test_data_path = os.path.join(SQL_DIR, "99_test_data.sql")
    if os.path.exists(test_data_path):
        print(f"  - 执行 99_test_data.sql")
        with open(test_data_path, "r", encoding="utf-8") as f:
            sql_text = f.read()
        stmts = split_sql_statements(sql_text)
        for i, stmt in enumerate(stmts):
            try:
                cursor.execute(stmt)
            except mysql.connector.Error as e:
                print(f"    ✗ 第 {i+1}/{len(stmts)} 条语句失败: {e}")
                print(f"    SQL(前120字): {stmt.strip()[:120]}")
                conn.rollback()
                cursor.close()
                conn.close()
                sys.exit(1)
        conn.commit()
        print(f"[3/3] 测试数据已加载 ({len(stmts)} 条语句)")

    cursor.close()
    conn.close()
    print(f"\n✓ 初始化完成!数据库 {Config.MYSQL_DATABASE} 已就绪")
    print(f"  可启动后端:python app.py")
    print(f"  浏览器访问 API:http://localhost:5000/api/visit")


if __name__ == "__main__":
    try:
        init_database()
    except mysql.connector.Error as e:
        print(f"\n✗ MySQL 错误: {e}")
        print("\n排查建议:")
        print("  1. MySQL 服务是否启动:brew services list | grep mysql")
        print("  2. 用户名/密码是否正确:修改 backend/config.py 的 MYSQL_USER / MYSQL_PASSWORD")
        print("  3. 端口是否被占用:修改 MYSQL_PORT")
    except FileNotFoundError as e:
        print(f"\n✗ 文件错误: {e}")
