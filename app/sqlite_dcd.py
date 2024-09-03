import os
import csv
import sqlite3
import re
import pypinyin
from pathlib import Path
from collections import Counter

def convert_to_pinyin(name):
    """将名称中的中文字符转换为拼音"""
    return ''.join(pypinyin.lazy_pinyin(name))

def sanitize_table_name(filename):
    """将文件名转换为可以在SQLite中用作表名的格式"""
    name, _ = os.path.splitext(filename)
    name = re.sub(r'[^\w]', '_', name)  # 将非字母数字的字符替换为下划线
    # 如果名称中包含非ASCII字符（例如中文），则转换为拼音
    if not all(ord(char) < 128 for char in name):
        name = convert_to_pinyin(name)
    return name

def make_unique_fieldnames(fieldnames):
    """处理重复的列名，确保每个列名在表中唯一"""
    counts = Counter(fieldnames)
    result = []
    suffix_counters = {}

    for name in fieldnames:
        if counts[name] > 1:
            if name not in suffix_counters:
                suffix_counters[name] = 1
            else:
                suffix_counters[name] += 1
            unique_name = f"{name}_{suffix_counters[name]}"
            result.append(unique_name)
        else:
            result.append(name)
    
    return result

def create_table(cursor, table_name, fieldnames):
    """创建一个SQLite表，表名和列名根据CSV文件内容确定"""
    unique_fieldnames = make_unique_fieldnames(fieldnames)
    columns = [f'"{name}" TEXT' for name in unique_fieldnames]
    columns_sql = ", ".join(columns)
    create_table_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({columns_sql});'
    cursor.execute(create_table_sql)

def insert_data(cursor, table_name, fieldnames, rows):
    """将数据插入到SQLite表中"""
    unique_fieldnames = make_unique_fieldnames(fieldnames)
    fieldnames_sql = ', '.join(f'"{name}"' for name in unique_fieldnames)
    placeholders = ', '.join('?' * len(unique_fieldnames))
    insert_sql = f'INSERT INTO "{table_name}" ({fieldnames_sql}) VALUES ({placeholders})'

    # 打印 SQL 语句用于调试
    print(f"Executing SQL: {insert_sql}")
    
    cursor.executemany(insert_sql, rows)

def process_csv_file(db_conn, csv_file_path):
    """处理单个CSV文件，并将其数据插入到SQLite数据库中"""
    table_name = sanitize_table_name(csv_file_path.stem)
    with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = reader.fieldnames
        if not fieldnames:
            return  # 跳过空的CSV文件

        cursor = db_conn.cursor()

        # 如果表不存在则创建表
        create_table(cursor, table_name, fieldnames)

        # 插入数据
        rows = [tuple(row.get(col, 'NULL') for col in fieldnames) for row in reader]
        insert_data(cursor, table_name, fieldnames, rows)

        db_conn.commit()

def main():
    base_dir = Path('../dcd_data')  # 更新后的相对目录路径
    db_dir = base_dir / 'db'  # 数据库存放的文件夹
    db_file = db_dir / 'dcd_data.db'

    # 如果数据库文件夹不存在，则创建它
    db_dir.mkdir(parents=True, exist_ok=True)

    # 连接到SQLite数据库（如果数据库不存在，将自动创建）
    db_conn = sqlite3.connect(db_file)

    # 处理目录中的每个CSV文件
    for csv_file_path in base_dir.glob('*.csv'):
        process_csv_file(db_conn, csv_file_path)
        print(f"已处理 {csv_file_path.name}")

    db_conn.close()
    print(f"数据已导入到 {db_file}")

if __name__ == '__main__':
    main()
