# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import re
import time
from pathlib import Path
import csv
import logging
import json

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_directory(path):
    directory = Path(path)
    if not directory.exists():
        directory.mkdir(parents=True)
        logging.info(f"目录 {path} 已创建")
    else:
        logging.info(f"目录 {path} 已存在")

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', '_', filename)

def clean_text(text):
    cleaned_text = re.sub(r'\d+', '', text).replace('\n', '').strip()
    return cleaned_text

def write_to_csv(file_path, data, mode='a', fieldnames=None):
    with open(file_path, mode, newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if mode == 'w':
            writer.writeheader()
        writer.writerow(data)

def take_screenshot(page, filename):
    screenshot_path = Path("screenshots")
    create_directory(screenshot_path)
    filepath = screenshot_path / sanitize_filename(filename)
    page.screenshot(path=filepath)
    logging.info(f"Screenshot saved to {filepath}")

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

def save_progress(car_name, status, last_user_id=None, review_progress=None):
    progress_file = Path('progress.json')
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

def load_progress():
    progress_file = Path('progress.json')
    if progress_file.exists():
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def run(playwright):
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
    scroll_count = 0
    max_scrolls = 2

    while scroll_count < max_scrolls:
        try:
            car_cards = page.query_selector_all('//li[contains(@class,"group")]')
            logging.info(f"Found {len(car_cards)} car cards on scroll {scroll_count + 1}.")

            for car_card in car_cards:
                car_name = car_card.query_selector('//a[contains(@class,"text")]').inner_text().strip()
                sanitized_car_name = sanitize_filename(car_name)
                if sanitized_car_name in existing_files and progress.get(sanitized_car_name, {}).get('status') == 'completed':
                    logging.info(f"Skipping {sanitized_car_name} as it is already completed.")
                    continue
                car_data[sanitized_car_name] = car_card

            last_height = page.evaluate("document.body.scrollHeight")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            new_height = page.evaluate("document.body.scrollHeight")

            if new_height == last_height:
                break

            scroll_count += 1

        except Exception as e:
            logging.error(f"Scrolling error: {e}")
            take_screenshot(page, f"scroll_error_{scroll_count}.png")

    for car_name, car_card in car_data.items():
        try:
            car_name_out = car_name
            car_progress = progress.get(car_name_out, {})
            if car_progress.get('status') == 'completed':
                logging.info(f"Skipping {car_name_out} as it is already completed.")
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
                logging.info(f"Last reviewed user ID for {car_name_out} is {last_user_id}")

                try:
                    review_buttons = koubei_page.query_selector_all('//a[contains(text(),"查看完整口碑")]')
                    logging.info(f"Found {len(review_buttons)} reviews on this page for {car_name_out}.")

                    for index, review_button in enumerate(review_buttons):
                        review_id = f"page_{index+1}_item_{index+1}"
                        review_progress_for_id = review_progress.get(review_id, {})

                        if review_progress_for_id.get('reviewed'):
                            logging.info(f"Review {review_id} has already been processed. Skipping...")
                            continue

                        try:
                            with context.expect_page() as review_page_info:
                                review_button.click()

                            review_page = review_page_info.value
                            review_page.wait_for_load_state("networkidle")
                            time.sleep(2)

                            car_name_elem = review_page.query_selector('//div[contains(@class,"title-name")]//a')
                            if car_name_elem:
                                car_name = car_name_elem.text_content().strip()
                                logging.info(f"Fetching reviews for car: {car_name}")
                            else:
                                logging.warning("未能找到车名")
                                take_screenshot(review_page, "car_name_not_found.png")
                                continue

                            reviewer_id_elem = review_page.query_selector('//a[contains(@id,"nickname")]')
                            if reviewer_id_elem:
                                reviewer_id = reviewer_id_elem.text_content().strip()
                                if reviewer_id == last_user_id:
                                    logging.info(f"Review by user {reviewer_id} has already been processed. Skipping...")
                                    continue
                            else:
                                reviewer_id = "未知用户"
                                logging.warning("未能找到评价人的ID")

                            review_items = review_page.query_selector_all('//p[@class="kb-item-msg"]')
                            review_titles = review_page.query_selector_all('//p[@class="kb-item-msg"]/preceding-sibling::h1')

                            review_data = {'车名': car_name, '用户ID': reviewer_id}
                            for title, item in zip(review_titles, review_items):
                                cleaned_title = clean_text(title.text_content().strip())
                                cleaned_item = clean_text(item.text_content().strip())
                                review_data[cleaned_title] = cleaned_item

                            write_to_csv(csv_file_path, review_data, 'a', fieldnames=list(review_data.keys()))
                            logging.info(f"Review saved for car {car_name_out} by user {reviewer_id}")

                            review_progress[review_id] = {'reviewed': True}
                            save_progress(car_name_out, 'incomplete', reviewer_id, review_progress)

                        except Exception as e:
                            logging.error(f"Error processing review button click: {e}")
                            take_screenshot(review_page, f"review_button_click_error_{car_name_out}.png")

                except Exception as e:
                    logging.error(f"Error finding review buttons: {e}")
                    take_screenshot(koubei_page, f"review_buttons_error_{car_name_out}.png")

                koubei_page.close()

            new_page.close()

            save_progress(car_name_out, 'completed')

        except Exception as e:
            logging.error(f"Error processing car card {car_name_out}: {e}")
            take_screenshot(new_page, f"car_card_error_{car_name_out}.png")

    page.close()
    context.close()
    browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
