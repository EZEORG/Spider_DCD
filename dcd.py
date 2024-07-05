from playwright.sync_api import sync_playwright
import re
import time
from pathlib import Path

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

                # 抓取页面上所有//a[contains(@class,"cell_car")]//text()
                car_names = new_page.query_selector_all('//a[contains(@class,"cell_car")]')
                car_name_texts = [name.text_content().strip() for name in car_names]

                # 保存车名为car_index_name.txt
                car_name_file = sanitize_filename(f'car_{index}_name.txt')
                car_name_path = Path(base_output_dir) / car_name_file
                with open(car_name_path, 'w', encoding='utf-8') as name_file:
                    name_file.write("\n".join(car_name_texts))

                data_elements = new_page.query_selector_all('//div[@data-row-anchor]/div')
                text_content = []
                for element in data_elements:
                    if element.query_selector('img'):
                        text_content.append("NULL")
                    else:
                        element_text = element.text_content()
                        text_content.append(element_text)

                # 生成文件名并保存内容
                sanitized_filename = sanitize_filename(f'car_{index}.txt')
                file_path = Path(base_output_dir) / sanitized_filename

                with open(file_path, 'w', encoding='utf-8') as txt_file:
                    txt_file.write("\n".join(text_content) + '\n')

                new_page.close()
        
        except Exception as e:
            print(f"抓取 car {index} 信息时出错：{e}")

    # 等待3秒，确保所有操作完成
    page.wait_for_timeout(3000)
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
