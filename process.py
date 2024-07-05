import json
import re
from pathlib import Path

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', '_', filename)

def process_txt_files(base_dir):
    base_path = Path(base_dir)
    json_results = []

    # 找到所有 car_*.txt 文件和对应的 car_*_name.txt 文件
    car_name_files = list(base_path.glob('car_*_name.txt'))

    for car_name_file in car_name_files:
        index = re.findall(r'car_(\d+)_name.txt', car_name_file.name)[0]
        car_data_file = base_path / f'car_{index}.txt'

        if not car_data_file.exists():
            print(f"{car_data_file} 不存在，跳过...")
            continue

        with open(car_name_file, 'r', encoding='utf-8') as f:
            car_names = [line.strip() for line in f.readlines()]
            n = len(car_names)

        with open(car_data_file, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines()]

        attribute_names = lines[0::n+1]  # 每隔 n+1 行取一次，取属性名
        attribute_data = [lines[i+1:i+1+n] for i in range(0, len(lines), n+1) if i+1+n <= len(lines)]

        car_info_list = [{} for _ in range(n)]

        for i, car_name in enumerate(car_names):
            car_info = {"车名": car_name}
            for j, attribute in enumerate(attribute_names):
                if j < len(attribute_data) and i < len(attribute_data[j]):
                    car_info[attribute] = attribute_data[j][i]
                else:
                    car_info[attribute] = ""
            car_info_list[i] = car_info

        json_results.extend(car_info_list)

    # 将结果写入 JSON 文件
    output_file = base_path / 'car_data.json'
    with open(output_file, 'w', encoding='utf-8') as json_file:
        json.dump(json_results, json_file, ensure_ascii=False, indent=4)

    print(f"结果已写入 {output_file}")

if __name__ == "__main__":
    base_directory = 'output_files'
    process_txt_files(base_directory)
