import re
import time
import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from logging import handlers
from playwright.sync_api import sync_playwright

def create_directory(path):
    directory = Path(path)
    if not directory.exists():
        directory.mkdir(parents=True)
        logger.info(f"目录 {path} 已创建")
    else:
        logger.info(f"目录 {path} 已存在")

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', '_', filename)

def load_progress():
    progress_file = Path('autohome_reviews/autohome_progressed.json')
    if progress_file.exists():
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_progress(car_name, status, last_user_id=None, review_progress=None):
    progress_file = Path('autohome_reviews/autohome_progressed.json')
    if progress_file.exists():
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress = json.load(f)
    else:
        progress = {}

    progress[car_name] = {
        'status': status,
        'last_user_id': last_user_id,
        'review_progress': review_progress
    }
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=4)

def get_existing_car_files(directory):
    existing_files = set()
    for file_path in Path(directory).glob('*_评价.csv'):
        car_name = file_path.stem.replace('_评价', '')
        existing_files.add(car_name)
    return existing_files

def get_last_reviewed_user_id(file_path):
    last_user_id = None
    if file_path.exists():
        with open(file_path, 'r', newline='', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            rows = list(reader)
            if rows:
                last_user_id = rows[-1]['用户ID']
    return last_user_id

def write_to_csv(file_path, data, mode='a', fieldnames=None):
    with open(file_path, mode, newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if mode == 'w':
            writer.writeheader()
        writer.writerow(data)

def setup_logging():
    global logger
    logger = logging.getLogger('autohome_crawler')
    logger.setLevel(logging.INFO)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 创建文件处理器
    log_dir = Path('autohome_reviews') / 'logs'
    create_directory(log_dir)
    log_filename = log_dir / f"scraper_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    file_handler = handlers.RotatingFileHandler(log_filename, maxBytes=5*1024*1024, backupCount=3)
    file_handler.setLevel(logging.INFO)

    # 设置日志格式
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # 添加处理器到记录器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

def run(playwright):
    setup_logging()

    base_output_dir = 'autohome_reviews'
    create_directory(base_output_dir)

    existing_files = get_existing_car_files(base_output_dir)
    progress = load_progress()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate, br"
    }

    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    def handle_request(route, request):
        route.continue_(headers={**request.headers, **headers})

    page.route("**/*", handle_request)

    page.goto("https://www.autohome.com.cn/price/#pvareaid=6861598")

    car_data = {}
    previous_height = 0

    while True:
        car_cards = page.query_selector_all('//li[contains(@class,"group")]')
        logger.info(f"Found {len(car_cards)} car cards.")

        new_cards = 0
        for car_card in car_cards:
            car_name = car_card.query_selector('//a[contains(@class,"text")]').inner_text().strip()
            sanitized_car_name = sanitize_filename(car_name)
            if sanitized_car_name not in car_data and sanitized_car_name not in existing_files:
                car_data[sanitized_car_name] = car_card
                new_cards += 1

        if new_cards > 0:
            logger.info(f"{new_cards} new car cards found, starting to scrape...")

            for car_name, car_card in car_data.items():
                try:
                    car_name_out = car_name
                    car_progress = progress.get(car_name_out, {})
                    if car_progress.get('status') == 'completed':
                        logger.info(f"Skipping {car_name_out} as it is already completed.")
                        continue

                    save_progress(car_name_out, 'incomplete')

                    with context.expect_page() as new_page_info:
                        car_card.click()

                    new_page = new_page_info.value
                    new_page.wait_for_load_state("networkidle")
                    time.sleep(5)

                    new_page.mouse.click(100, 100)
                    time.sleep(1)

                    koubei_button = new_page.query_selector('//li/a[text()="口碑"]')
                    if koubei_button:
                        with context.expect_page() as koubei_page_info:
                            koubei_button.click()

                        koubei_page = koubei_page_info.value
                        koubei_page.wait_for_load_state("networkidle")
                        time.sleep(2)

                        csv_file_path = Path(base_output_dir) / f'{car_name_out}_评价.csv'
                        last_user_id = get_last_reviewed_user_id(csv_file_path)
                        if last_user_id is None:
                            last_user_id = car_progress.get('last_user_id')

                        review_progress = car_progress.get('review_progress', {})
                        logger.info(f"Last reviewed user ID for {car_name_out} is {last_user_id}")

                        current_page = 1
                        while True:
                            review_buttons = koubei_page.query_selector_all('//a[contains(text(),"查看完整口碑")]')
                            logger.info(f"Found {len(review_buttons)} reviews on page {current_page} for {car_name_out}.")

                            for index, review_button in enumerate(review_buttons):
                                review_id = f"page_{current_page}_item_{index+1}"
                                review_progress_for_id = review_progress.get(review_id, {})

                                if review_progress_for_id.get('reviewed'):
                                    logger.info(f"Review {review_id} has already been processed. Skipping...")
                                    continue

                                with context.expect_page() as review_page_info:
                                    review_button.click()

                                review_page = review_page_info.value
                                review_page.wait_for_load_state("networkidle")
                                time.sleep(2)

                                car_name_elem = review_page.query_selector('//div[contains(@class,"title-name")]//a')
                                if car_name_elem:
                                    car_name = car_name_elem.text_content().strip()
                                    logger.info(f"Fetching reviews for car: {car_name}")
                                else:
                                    logger.warning("未能找到车名")
                                    continue

                                reviewer_id_elem = review_page.query_selector('//a[contains(@id,"nickname")]')
                                if reviewer_id_elem:
                                    reviewer_id = reviewer_id_elem.text_content().strip()
                                    if reviewer_id == last_user_id:
                                        logger.info(f"Review by user {reviewer_id} has already been processed. Skipping...")
                                        continue
                                else:
                                    reviewer_id = "未知用户"
                                    logger.warning("未能找到评价人的ID")

                                review_items = review_page.query_selector_all('//p[@class="kb-item-msg"]')
                                review_titles = review_page.query_selector_all('//p[@class="kb-item-msg"]/preceding-sibling::h1')
                                review_scores = review_page.query_selector_all('//p[@class="kb-item-msg"]/preceding-sibling::h1/span')


                                # 构建包含标题及评分的字典
                                review_data = {'车名': car_name, '用户ID': reviewer_id}
                                for title, item, score in zip(review_titles, review_items, review_scores):
                                    # 仅保留标题中的中文字符
                                    cleaned_title = ''.join(re.findall(r'[\u4e00-\u9fa5]', title.text_content().strip()))
                                    cleaned_item = item.text_content().strip()
                                    cleaned_score = score.text_content().strip() if score else '无评分'
                                    
                                    # 以清理后的标题为键名保存数据
                                    review_data[f'{cleaned_title}'] = cleaned_item
                                    review_data[f'{cleaned_title}评分'] = cleaned_score


                                if not csv_file_path.exists():
                                    fieldnames = list(review_data.keys())
                                    write_to_csv(csv_file_path, review_data, 'w', fieldnames=fieldnames)
                                else:
                                    write_to_csv(csv_file_path, review_data, 'a', fieldnames=list(review_data.keys()))
                                logger.info(f"Review saved for car {car_name_out} by user {reviewer_id}")

                                review_progress[review_id] = {'reviewed': True}
                                save_progress(car_name_out, 'incomplete', reviewer_id, review_progress)

                                review_page.close()

                            next_page_button = koubei_page.query_selector('//a[@class="page-item-next"]')
                            if next_page_button and not next_page_button.get_property('classList').contains('disabled'):
                                next_page_button.click()
                                koubei_page.wait_for_load_state("networkidle")
                                time.sleep(2)
                                current_page += 1
                            else:
                                break

                        save_progress(car_name_out, 'completed')

                    koubei_page.close()

                    new_page.close()

                except Exception as e:
                    logger.error(f"An error occurred while processing {car_name_out}: {str(e)}")
                    save_progress(car_name_out, 'error')
                    continue

        page.evaluate("window.scrollBy(0, document.body.scrollHeight);")
        time.sleep(2)

        current_height = page.evaluate("document.body.scrollHeight")
        if current_height == previous_height:
            break

        previous_height = current_height

    logger.info("Scraping completed.")
    context.close()
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
