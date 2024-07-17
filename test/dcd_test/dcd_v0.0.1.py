from playwright.sync_api import sync_playwright
import re
import time
from pathlib import Path
import csv
from lxml import html

def create_directory(path):
    # 创建目录
    directory = Path(path)
    if not directory.exists():
        directory.mkdir(parents=True)
        print(f"目录 {path} 已创建")
    else:
        print(f"目录 {path} 已存在")

def sanitize_filename(filename):
    # 替换特殊字符
    return re.sub(r'[\\/*?:"<>|]', '_', filename)

def run(playwright):
    base_output_dir = 'dcd_data'
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
                content = new_page.content()
                dom = html.fromstring(content)

                # 获取所有车名
                car_names = dom.xpath('//a[contains(@class,"cell_car")]/text()')
                car_name_texts = [name.strip() for name in car_names]

                # 获取属性名
                attribute_names = dom.xpath('//label/text()')
                attribute_names = [attr.strip() for attr in attribute_names]

                # 初始化数据结构
                car_data = {name: {attr: '' for attr in attribute_names} for name in car_name_texts}

                # 获取价格信息
                prices = dom.xpath('//div[contains(@class,"official-price")]/text()')
                price_texts = [price.strip() for price in prices]

                # 将价格信息填充到“官方指导价”列中
                for i, car_name in enumerate(car_name_texts):
                    if i < len(price_texts):
                        car_data[car_name]['官方指导价'] = price_texts[i]

                # 获取属性值
                xpath2_elements = dom.xpath('//div[@data-row-anchor]')
                for elem in xpath2_elements:
                    nested_elem = elem.xpath('.//div[contains(@class,"nest")]')
                    if nested_elem:
                        for i in range(1, len(car_name_texts) + 1):
                            index_texts = elem.xpath(f'.//div[contains(@style,"index:{i}")]//text()')
                            index_texts = [text.strip() for text in index_texts if text.strip()]
                            if index_texts:
                                attribute_value = " ".join(index_texts)
                                car_data[car_name_texts[i-1]][attribute_names[xpath2_elements.index(elem)]] = attribute_value
                    else:
                        cell_normal_elements = elem.xpath('.//div[contains(@class,"cell_normal")]')
                        for i, cell in enumerate(cell_normal_elements):
                            if cell.xpath('.//img'):
                                text = 'NULL'
                            else:
                                text = cell.text_content().strip()
                            if text:
                                car_data[car_name_texts[i]][attribute_names[xpath2_elements.index(elem)]] = text

                # 保存为CSV文件
                csv_file_path = Path(base_output_dir) / sanitize_filename(f'car_{index}.csv')
                with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
                    writer = csv.DictWriter(csv_file, fieldnames=['车名'] + attribute_names)
                    writer.writeheader()
                    for car_name in car_name_texts:
                        row = {'车名': car_name}
                        row.update(car_data[car_name])
                        writer.writerow(row)

                print(f"数据已保存到 {csv_file_path}")

                new_page.close()

        except Exception as e:
            print(f"抓取 car {index} 信息时出错：{e}")

    # 等待3秒，确保所有操作完成
    page.wait_for_timeout(3000)
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
