from playwright.sync_api import sync_playwright
import re
import time
from pathlib import Path
import csv
import json
import logging
from lxml import html
from datetime import datetime
from logging import handlers

def create_directory(path):
    directory = Path(path)
    if not directory.exists():
        directory.mkdir(parents=True)
        logger.info(f"目录 {path} 已创建")
    else:
        logger.info(f"目录 {path} 已存在")

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', '_', filename)

def load_processed_cars(json_file):
    if Path(json_file).exists():
        with open(json_file, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    return set()

def save_processed_cars(json_file, car_names):
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(list(car_names), f, ensure_ascii=False, indent=4)

def setup_logging():
    global logger
    logger = logging.getLogger('car_scraper')
    logger.setLevel(logging.INFO)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 创建文件处理器
    log_dir = Path('dcd_data') / 'logs'
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

def generate_report(processed_cars, failed_cars):
    report_dir = Path('dcd_data') / 'reports'
    create_directory(report_dir)
    report_filename = report_dir / f"report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"

    with open(report_filename, 'w', encoding='utf-8') as report_file:
        report_file.write("车辆数据抓取报告\n")
        report_file.write("====================\n")
        report_file.write(f"总共抓取到的车辆数量: {len(processed_cars)}\n")
        report_file.write(f"抓取失败的车辆数量: {len(failed_cars)}\n")
        report_file.write("\n成功抓取的车辆列表:\n")
        for car in processed_cars:
            report_file.write(f" - {car}\n")
        report_file.write("\n抓取失败的车辆列表:\n")
        for car in failed_cars:
            report_file.write(f" - {car}\n")

    logger.info(f"报告已生成：{report_filename}")

def run(playwright):
    setup_logging()

    base_output_dir = 'dcd_data'
    create_directory(base_output_dir)

    processed_cars_file = Path(base_output_dir) / 'processed_cars.json'
    processed_cars = load_processed_cars(processed_cars_file)

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
    
    page.goto("https://www.dongchedi.com/auto/library/x-x-x-x-x-x-x-x-x-x-x")

    car_data = {}
    previous_height = 0
    max_retries = 3
    retries = 0
    failed_cars = []

    while True:
        car_cards = page.query_selector_all('//div[contains(@class,"car-list_card")]')
        logger.info(f"Found {len(car_cards)} car cards.")

        new_cards = 0
        for car_card in car_cards:
            car_name = car_card.query_selector('//a[contains(@class,"card_name")]').inner_text().strip()
            if car_name not in car_data and car_name not in processed_cars:
                car_data[car_name] = car_card
                new_cards += 1

        if new_cards > 0:
            logger.info(f"{new_cards} new car cards found, starting to scrape...")

            for car_name, car_card in car_data.items():
                if car_name in processed_cars:
                    continue

                try:
                    car_name_out = car_name
                    param_button = car_card.query_selector('//a[contains(text(),"参数")]')
                    if param_button:
                        with context.expect_page() as new_page_info:
                            param_button.click()

                        new_page = new_page_info.value
                        new_page.wait_for_load_state("networkidle")
                        time.sleep(2)
                        content = new_page.content()
                        dom = html.fromstring(content)

                        car_names = dom.xpath('//a[contains(@class,"cell_car")]/text()')
                        car_name_texts = [name.strip() for name in car_names]

                        attribute_names = dom.xpath('//label/text()')
                        attribute_names = [attr.strip() for attr in attribute_names]

                        car_data_dict = {name: {attr: '' for attr in attribute_names} for name in car_name_texts}

                        prices = dom.xpath('//div[contains(@class,"official-price")]/text()')
                        price_texts = [price.strip() for price in prices]

                        for i, car_name in enumerate(car_name_texts):
                            if i < len(price_texts):
                                car_data_dict[car_name]['官方指导价'] = price_texts[i]

                        xpath_value = '//div[@data-row-anchor]/parent::*/div[contains(@class,"table_row") and not(contains(@class,"title"))]'
                        value_elements = dom.xpath(xpath_value)
                        for elem in value_elements:
                            nested_elem = elem.xpath('./div[contains(@class,"nest")]')
                            if nested_elem:
                                nested_rows = elem.xpath('.//div[contains(@class,"table_row")]')
                                for row_index, row in enumerate(nested_rows):
                                    for col_index in range(len(car_name_texts)):
                                        index_texts = row.xpath(f'.//div[contains(@style,"index:{col_index + 1}")]//text()')
                                        index_texts = [text.strip() for text in index_texts if text.strip()]
                                        if index_texts:
                                            attribute_value = " ".join(index_texts)
                                            car_data_dict[car_name_texts[col_index]][attribute_names[value_elements.index(elem)]] = attribute_value
                            else:
                                cell_normal_elements = elem.xpath('.//div[contains(@class,"cell_normal")]')
                                for i, cell in enumerate(cell_normal_elements):
                                    if cell.xpath('.//img'):
                                        text = 'NULL'
                                    else:
                                        text = cell.text_content().strip()
                                    if text:
                                        car_data_dict[car_name_texts[i]][attribute_names[value_elements.index(elem)]] = text

                        csv_file_path = Path(base_output_dir) / sanitize_filename(f'{car_name_out}_参数.csv')
                        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
                            writer = csv.DictWriter(csv_file, fieldnames=['车名'] + attribute_names)
                            writer.writeheader()
                            for car in car_name_texts:
                                row = {'车名': car}
                                row.update(car_data_dict[car])
                                writer.writerow(row)

                        logger.info(f"数据已保存到 {csv_file_path}")

                        # 记录抓取成功的车名
                        processed_cars.add(car_name_out)
                        save_processed_cars(processed_cars_file, processed_cars)

                        new_page.close()

                except Exception as e:
                    logger.error(f"抓取 {car_name} 信息时出错：{e}")
                    failed_cars.append(car_name)

            if failed_cars:
                logger.warning(f"以下车辆的数据抓取失败：{', '.join(failed_cars)}")

        last_height = page.evaluate("document.body.scrollHeight")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        new_height = page.evaluate("document.body.scrollHeight")

        if new_height == last_height:
            retries += 1
            if retries >= max_retries:
                logger.info("No more new content to load. Stopping scrolling.")
                break
        else:
            retries = 0

    generate_report(processed_cars, failed_cars)

    page.wait_for_timeout(1000)
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
