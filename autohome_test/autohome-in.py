#这个程序从完整口碑页面开始抓取，其中有正确的逻辑
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
    page.goto("https://k.autohome.com.cn/detail/view_01j2dcqv3p6mskjd1q60wg0000.html#pvareaid=2112108")

    # 等待页面加载完成
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # 获取评价信息
    car_name_elem = page.query_selector('//div[contains(@class,"title-name")]//a')
    if car_name_elem:
        car_name = car_name_elem.text_content().strip()
        print(f"Fetching reviews for car: {car_name}")
    else:
        print("未能找到车名")
        browser.close()
        return

    all_reviews = []

    reviewer_id_elem = page.query_selector('//a[contains(@id,"nickname")]')
    if reviewer_id_elem:
        reviewer_id = reviewer_id_elem.text_content().strip()
    else:
        reviewer_id = "未知用户"
        print("未能找到评价人的ID")

    review_items = page.query_selector_all('//p[@class="kb-item-msg"]')
    review_titles = page.query_selector_all('//p[@class="kb-item-msg"]/preceding-sibling::h1')

    review_data = {'车名': car_name, '用户ID': reviewer_id}
    for title, item in zip(review_titles, review_items):
        cleaned_title = clean_text(title.text_content().strip())
        review_data[cleaned_title] = item.text_content().strip()

    all_reviews.append(review_data)

    # 保存为CSV文件
    if all_reviews:
        csv_file_path = Path(base_output_dir) / sanitize_filename(f'{car_name}_reviews.csv')
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
            fieldnames = ['车名', '用户ID'] + list(all_reviews[0].keys())[2:]
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for review in all_reviews:
                writer.writerow(review)

        print(f"数据已保存到 {csv_file_path}")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
