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

def clean_text(text):
    # 去掉数字和换行符
    cleaned_text = re.sub(r'\d+', '', text).replace('\n', '').strip()
    return cleaned_text

def run(playwright):
    base_output_dir = 'autohome_reviews'
    create_directory(base_output_dir)

    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.autohome.com.cn/price/#pvareaid=6861598")
    page.wait_for_load_state("networkidle")
    car_cards = page.query_selector_all('//li[contains(@class,"group")]')
    print(f"Found {len(car_cards)} car cards.")

    for index, card in enumerate(car_cards, start=1):
        try:
            with context.expect_page() as new_page_info:
                card.click()

            new_page = new_page_info.value
            new_page.wait_for_load_state("networkidle")
            time.sleep(5)

            # 弹窗检测
            new_page.mouse.click(100, 100)
            time.sleep(1)

            # 点击“口碑”按钮
            koubei_button = new_page.query_selector('//li/a[text()="口碑"]')
            if koubei_button:
                with context.expect_page() as koubei_page_info:
                    koubei_button.click()

                koubei_page = koubei_page_info.value
                koubei_page.wait_for_load_state("networkidle")
                time.sleep(2)

                csv_file_path = None
                fieldnames = None
                writer = None
                all_reviews = []

                while True:
                    # 获取所有完整口碑按钮
                    review_buttons = koubei_page.query_selector_all('//a[contains(text(),"查看完整口碑")]')
                    print(f"Found {len(review_buttons)} reviews on this page.")

                    for review_button in review_buttons:
                        try:
                            with context.expect_page() as review_page_info:
                                review_button.click()

                            review_page = review_page_info.value
                            review_page.wait_for_load_state("networkidle")
                            time.sleep(2)

                            # 获取评价信息
                            car_name_elem = review_page.query_selector('//div[contains(@class,"title-name")]//a')
                            if car_name_elem:
                                car_name = car_name_elem.text_content().strip()
                                print(f"Fetching reviews for car: {car_name}")
                            else:
                                print("未能找到车名")
                                return

                            reviewer_id_elem = review_page.query_selector('//a[contains(@id,"nickname")]')
                            if reviewer_id_elem:
                                reviewer_id = reviewer_id_elem.text_content().strip()
                            else:
                                reviewer_id = "未知用户"
                                print("未能找到评价人的ID")

                            review_items = review_page.query_selector_all('//p[@class="kb-item-msg"]')
                            review_titles = review_page.query_selector_all('//p[@class="kb-item-msg"]/preceding-sibling::h1')

                            review_data = {'车名': car_name, '用户ID': reviewer_id}
                            for title, item in zip(review_titles, review_items):
                                cleaned_title = clean_text(title.text_content().strip())
                                review_data[cleaned_title] = item.text_content().strip()

                            # 保存每个评价到CSV的一行
                            if not csv_file_path:
                                csv_file_path = Path(base_output_dir) / sanitize_filename(f'{car_name}_reviews.csv')
                                with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
                                    fieldnames = ['车名', '用户ID'] + list(review_data.keys())[2:]
                                    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                                    writer.writeheader()
                                    writer.writerow(review_data)
                            else:
                                with open(csv_file_path, 'a', newline='', encoding='utf-8') as csv_file:
                                    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                                    writer.writerow(review_data)

                            print(f"数据已保存到 {csv_file_path}")

                            review_page.close()

                        except Exception as e:
                            print(f"抓取 car {index} 的评价时出错：{e}")

                    # 点击下一页按钮
                    next_button = koubei_page.query_selector('//a[contains(@class,"next")]')
                    if next_button:
                        next_button.click()
                        koubei_page.wait_for_load_state("networkidle")
                        time.sleep(2)
                    else:
                        break

                koubei_page.close()

            else:
                print(f"未能找到 car {index} 的口碑按钮")

        except Exception as e:
            print(f"抓取 car {index} 信息时出错：{e}")

    # 等待3秒，确保所有操作完成
    page.wait_for_timeout(3000)
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
