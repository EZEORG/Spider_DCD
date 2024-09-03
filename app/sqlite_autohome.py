import os
import sqlite3
import pandas as pd
from pathlib import Path

# 定义目录和数据库文件路径
csv_directory = './autohome_reviews'
db_directory = './autohome_reviews/db'
db_file = os.path.join(db_directory, 'reviews.db')
table_name = 'reviews'

# 创建数据库目录（如果不存在）
Path(db_directory).mkdir(parents=True, exist_ok=True)

# 创建数据库连接
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# 获取所有CSV文件
csv_files = [f for f in os.listdir(csv_directory) if f.endswith('.csv')]

if not csv_files:
    print("没有找到CSV文件。")
    exit()

# 创建表时的初始列集
existing_columns = set()

# 定义函数以动态添加列
def add_missing_columns(new_columns):
    """动态添加表中不存在的新列"""
    for column in new_columns:
        if column not in existing_columns:
            alter_table_sql = f'ALTER TABLE {table_name} ADD COLUMN "{column}" TEXT;'
            cursor.execute(alter_table_sql)
            existing_columns.add(column)
            print(f"添加新列: {column}")

# 检查表是否存在
cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
table_exists = cursor.fetchone()

if not table_exists:
    # 如果表不存在，使用第一个CSV文件创建表
    first_file = csv_files[0]
    first_file_path = os.path.join(csv_directory, first_file)
    
    df = pd.read_csv(first_file_path, on_bad_lines='skip')
    existing_columns = set(df.columns)
    
    columns_str = ', '.join([f'"{col}" TEXT' for col in existing_columns])
    
    # 创建表
    create_table_sql = f'''
    CREATE TABLE IF NOT EXISTS {table_name} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        {columns_str}
    )
    '''
    cursor.execute(create_table_sql)
    print(f"表 '{table_name}' 已创建。")

# 遍历所有CSV文件并插入数据
for csv_file in csv_files:
    file_path = os.path.join(csv_directory, csv_file)
    
    try:
        df = pd.read_csv(file_path, on_bad_lines='skip')
    except pd.errors.ParserError as e:
        print(f"读取文件 {csv_file} 时发生错误: {e}")
        continue
    
    # 检查并添加缺失的列
    new_columns = set(df.columns) - existing_columns
    if new_columns:
        add_missing_columns(new_columns)
    
    # 将数据插入到数据库表中
    for row in df.itertuples(index=False, name=None):
        placeholders = ', '.join(['?' for _ in row])
        insert_sql = f'INSERT INTO {table_name} ({", ".join(df.columns)}) VALUES ({placeholders})'
        try:
            cursor.execute(insert_sql, row)
        except sqlite3.OperationalError as e:
            print(f"插入数据时出错: {e}")
            print(f"SQL语句: {insert_sql}")
            print(f"行数据: {row}")
            continue

# 提交更改并关闭连接
conn.commit()
conn.close()

print("数据导入完成。")
