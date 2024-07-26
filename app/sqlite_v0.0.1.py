import os
import sqlite3
import pandas as pd

# 定义目录和数据库文件路径
csv_directory = './autohome_reviews_save'
db_path = 'db/data.db'
table_name = 'reviews'

# 创建数据库连接
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 获取所有CSV文件
csv_files = [f for f in os.listdir(csv_directory) if f.endswith('.csv')]

if not csv_files:
    print("没有找到CSV文件。")
    exit()

# 读取第一个CSV文件的列名和数据类型
first_file = csv_files[0]
first_file_path = os.path.join(csv_directory, first_file)

# 使用pandas读取CSV文件以获取列信息
df = pd.read_csv(first_file_path, nrows=0)
columns = df.columns
columns_str = ', '.join([f'"{col}" TEXT' for col in columns])

# 创建表
create_table_sql = f'''
CREATE TABLE IF NOT EXISTS {table_name} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    {columns_str}
)
'''
cursor.execute(create_table_sql)

# 遍历所有CSV文件并插入数据
for csv_file in csv_files:
    file_path = os.path.join(csv_directory, csv_file)
    df = pd.read_csv(file_path)
    
    # 将数据插入到数据库表中
    for row in df.itertuples(index=False):
        placeholders = ', '.join(['?' for _ in row])
        insert_sql = f'INSERT INTO {table_name} ({", ".join(columns)}) VALUES ({placeholders})'
        cursor.execute(insert_sql, row)

# 提交更改并关闭连接
conn.commit()
conn.close()

print("数据导入完成。")
