# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import re
import time
from pathlib import Path
import csv

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

def clean_text(text):
    # 去掉数字和换行符
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
    print(f"Screenshot saved to {filepath}")

def run(playwright):
    base_output_dir = 'autohome_reviews'
    create_directory(base_output_dir)

    # 自定义的HTTP头
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate, br"
    }

    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    # 设置请求拦截器
    def handle_request(route, request):
        route.continue_(headers={**request.headers, **headers})
    
    page.route("**/*", handle_request)
    
    page.goto("https://www.autohome.com.cn/price/#pvareaid=6861598")

    car_data = {}
    scroll_count = 0
    max_scrolls = 2

    while scroll_count < max_scrolls:
        try:
            # 获取当前页面所有车的卡片元素
            car_cards = page.query_selector_all('//li[contains(@class,"group")]')
            print(f"Found {len(car_cards)} car cards on scroll {scroll_count + 1}.")

            # 提取车卡片元素信息并添加到集合中避免重复
            for car_card in car_cards:
                car_name = car_card.query_selector('//a[contains(@class,"text")]').inner_text().strip()
                if car_name not in car_data:
                    car_data[car_name] = car_card

            # 滚动页面以加载更多的汽车卡片
            last_height = page.evaluate("document.body.scrollHeight")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            new_height = page.evaluate("document.body.scrollHeight")

            # 检查页面高度是否发生变化，如果没有变化则停止滚动
            if new_height == last_height:
                break

            scroll_count += 1

        except Exception as e:
            print(f"Scrolling error: {e}")
            take_screenshot(page, f"scroll_error_{scroll_count}.png")

    # 点击每个车的卡片并抓取数据
    for car_name, car_card in car_data.items():
        try:
            car_name_out = car_name  # 记录车名用于文件名
            # 点击卡片进入新页面
            with context.expect_page() as new_page_info:
                car_card.click()

            new_page = new_page_info.value
            new_page.wait_for_load_state("networkidle")
            time.sleep(5)

            # 等待5s，弹窗检测
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

                csv_file_path = Path(base_output_dir) / sanitize_filename(f'{car_name_out}_评价.csv')

                while True:
                    try:
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
                                    take_screenshot(review_page, "car_name_not_found.png")
                                    continue

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

                                if not csv_file_path.exists():
                                    fieldnames = list(review_data.keys())
                                    write_to_csv(csv_file_path, review_data, mode='w', fieldnames=fieldnames)
                                else:
                                    with open(csv_file_path, 'r', newline='', encoding='utf-8') as csv_file:
                                        reader = csv.DictReader(csv_file)
                                        existing_fields = reader.fieldnames

                                    current_fields = set(review_data.keys())
                                    missing_fields = set(existing_fields) - current_fields
                                    extra_fields = current_fields - set(existing_fields)

                                    # 忽略多出的字段
                                    for field in extra_fields:
                                        review_data.pop(field, None)

                                    # 填补缺失的字段
                                    for field in missing_fields:
                                        review_data[field] = ''

                                    write_to_csv(csv_file_path, review_data, mode='a', fieldnames=existing_fields)

                                print(f"数据已保存到 {csv_file_path}")

                                review_page.close()

                            except Exception as e:
                                print(f"抓取 {car_name_out} 的评价时出错：{e}")
                                take_screenshot(review_page, f"review_error_{car_name_out}.png")
                                
                        # 点击下一页按钮
                        next_button = koubei_page.query_selector('//a[contains(@class,"next")]')
                        if next_button:
                            next_button.click()
                            koubei_page.wait_for_load_state("networkidle")
                            time.sleep(2)
                        else:
                            break

                    except Exception as e:
                        print(f"Error while processing reviews for {car_name_out}: {e}")
                        take_screenshot(koubei_page, f"koubei_page_error_{car_name_out}.png")

                koubei_page.close()

            else:
                print(f"未能找到 {car_name_out} 的口碑按钮")

        except Exception as e:
            print(f"抓取 {car_name_out} 信息时出错：{e}")
            #take_screenshot(page, f"car_page_error_{car_name_out}.png")

    page.wait_for_timeout(1000)
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
