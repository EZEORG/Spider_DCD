from playwright.sync_api import sync_playwright
import re
import time
from pathlib import Path
import csv

def create_directory(path):
    directory = Path(path)
    if not directory.exists():
        directory.mkdir(parents=True)
        print(f"目录 {path} 已创建")
    else:
        print(f"目录 {path} 已存在")

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', '_', filename)

def run(playwright):
    base_output_dir = 'output_files'
    create_directory(base_output_dir)

    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.dongchedi.com/auto/library/x-x-x-x-x-x-x-x-x-x-x")

    # 获取所有车的卡片元素
    car_cards = page.query_selector_all('//div[contains(@class,"car-list_card")]')
    print(f"Found {len(car_cards)} car cards.")

    for index, card in enumerate(car_cards, start=1):
        try:
            # 点击“参数”按钮
            param_button = card.query_selector('//a[contains(text(),"参数")]')
            if param_button:
                with context.expect_page() as new_page_info:
                    param_button.click()

                new_page = new_page_info.value
                new_page.wait_for_load_state("networkidle")
                time.sleep(2)

                # 获取当前卡片中的所有车名
                car_names = new_page.query_selector_all('//a[contains(@class,"cell_car")]')
                car_name_texts = [name.text_content().strip() for name in car_names]

                # 保存车名为car_index_name.txt
                car_name_file = sanitize_filename(f'car_{index}_name.txt')
                car_name_path = Path(base_output_dir) / car_name_file
                with open(car_name_path, 'w', encoding='utf-8') as name_file:
                    name_file.write("\n".join(car_name_texts))

                print(f"Car {index} names: {car_name_texts}")

                # 获取所有属性名
                attribute_elements = new_page.query_selector_all('//div[@data-row-anchor]//div[contains(@style,"index:0")]')
                attribute_names = [attr.text_content().strip() for attr in attribute_elements]
                print(f"Car {index} 属性: {attribute_names}")

                # 初始化车数据
                car_data = []
                for car_name in car_name_texts:
                    car_data.append({"车名": car_name})

                # 按行抓取属性值
                for attr_idx, attr_name in enumerate(attribute_names):
                    for car_idx, car_name in enumerate(car_name_texts):
                        car_info = car_data[car_idx]
                        try:
                            attr_value_elem = new_page.query_selector(f'//div[@data-row-anchor][{attr_idx + 1}]//div[contains(@style,"index:{car_idx + 1}")]')
                            if attr_value_elem:
                                # 检查是否有图片元素
                                if attr_value_elem.query_selector('img'):
                                    attr_values_str = "NULL"
                                else:
                                    attr_values_str = attr_value_elem.text_content().strip()

                                # 检查是否有多个值
                                nested_divs = attr_value_elem.query_selector_all('div[class*="is-nest"] div')
                                if nested_divs:
                                    nested_values = [nested_div.text_content().strip() for nested_div in nested_divs]
                                    attr_values_str = " | ".join(nested_values)

                                car_info[attr_name] = attr_values_str
                                print(f"Car {index} {car_name} 属性 {attr_name}: {attr_values_str}")
                        except Exception as e:
                            print(f"获取属性 {attr_name} 值时出错 for car {index} {car_name}: {e}")

                # 保存为CSV文件
                if car_data:
                    csv_file_path = Path(base_output_dir) / sanitize_filename(f'car_{index}.csv')
                    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
                        writer = csv.DictWriter(csv_file, fieldnames=car_data[0].keys())
                        writer.writeheader()
                        writer.writerows(car_data)
                    print(f"数据已保存到 {csv_file_path}")

                new_page.close()

        except Exception as e:
            print(f"抓取 car {index} 信息时出错：{e}")

    # 等待3秒，确保所有操作完成
    page.wait_for_timeout(3000)
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
