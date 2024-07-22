# -*- coding: utf-8 -*-
from playwright.async_api import async_playwright
import re
import asyncio
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
    cleaned_text = re.sub(r'\d+', '', text).replace('\n', '').strip()
    return cleaned_text

def write_to_csv(file_path, data, mode='a', fieldnames=None):
    with open(file_path, mode, newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if mode == 'w':
            writer.writeheader()
        writer.writerow(data)

async def take_screenshot(page, filename):
    screenshot_path = Path("screenshots")
    create_directory(screenshot_path)
    filepath = screenshot_path / sanitize_filename(filename)
    await page.screenshot(path=filepath)
    print(f"Screenshot saved to {filepath}")

async def run(playwright):
    base_output_dir = 'autohome_reviews'
    create_directory(base_output_dir)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate, br"
    }

    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    async def handle_request(route, request):
        await route.continue_(headers={**request.headers, **headers})
    
    await page.route("**/*", handle_request)
    await page.goto("https://www.autohome.com.cn/price/#pvareaid=6861598")

    car_data = {}
    scroll_count = 0
    max_scrolls = 2

    while scroll_count < max_scrolls:
        try:
            car_cards = await page.query_selector_all('//li[contains(@class,"group")]')
            print(f"Found {len(car_cards)} car cards on scroll {scroll_count + 1}.")

            for car_card in car_cards:
                car_name = (await car_card.query_selector('//a[contains(@class,"text")]')).inner_text().strip()
                if car_name not in car_data:
                    car_data[car_name] = car_card

            last_height = await page.evaluate("document.body.scrollHeight")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            new_height = await page.evaluate("document.body.scrollHeight")

            if new_height == last_height:
                break

            scroll_count += 1

        except Exception as e:
            print(f"Scrolling error: {e}")
            await take_screenshot(page, f"scroll_error_{scroll_count}.png")

    for car_name, car_card in car_data.items():
        try:
            car_name_out = car_name
            async with context.expect_page() as new_page_info:
                await car_card.click()

            new_page = await new_page_info.value
            await new_page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)

            await new_page.mouse.click(100, 100)
            await asyncio.sleep(1)

            koubei_button = await new_page.query_selector('//li/a[text()="口碑"]')
            if koubei_button:
                async with context.expect_page() as koubei_page_info:
                    await koubei_button.click()

                koubei_page = await koubei_page_info.value
                await koubei_page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)

                csv_file_path = Path(base_output_dir) / sanitize_filename(f'{car_name_out}_评价.csv')

                while True:
                    try:
                        review_buttons = await koubei_page.query_selector_all('//a[contains(text(),"查看完整口碑")]')
                        print(f"Found {len(review_buttons)} reviews on this page.")

                        for review_button in review_buttons:
                            try:
                                async with context.expect_page() as review_page_info:
                                    await review_button.click()

                                review_page = await review_page_info.value
                                await review_page.wait_for_load_state("networkidle")
                                await asyncio.sleep(2)

                                car_name_elem = await review_page.query_selector('//div[contains(@class,"title-name")]//a')
                                if car_name_elem:
                                    car_name = (await car_name_elem.text_content()).strip()
                                    print(f"Fetching reviews for car: {car_name}")
                                else:
                                    print("未能找到车名")
                                    await take_screenshot(review_page, "car_name_not_found.png")
                                    continue

                                reviewer_id_elem = await review_page.query_selector('//a[contains(@id,"nickname")]')
                                if reviewer_id_elem:
                                    reviewer_id = (await reviewer_id_elem.text_content()).strip()
                                else:
                                    reviewer_id = "未知用户"
                                    print("未能找到评价人的ID")

                                review_items = await review_page.query_selector_all('//p[@class="kb-item-msg"]')
                                review_titles = await review_page.query_selector_all('//p[@class="kb-item-msg"]/preceding-sibling::h1')

                                review_data = {'车名': car_name, '用户ID': reviewer_id}
                                for title, item in zip(review_titles, review_items):
                                    cleaned_title = clean_text((await title.text_content()).strip())
                                    review_data[cleaned_title] = (await item.text_content()).strip()

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

                                    for field in extra_fields:
                                        review_data.pop(field, None)

                                    for field in missing_fields:
                                        review_data[field] = ''

                                    write_to_csv(csv_file_path, review_data, mode='a', fieldnames=existing_fields)

                                print(f"数据已保存到 {csv_file_path}")

                                await review_page.close()

                            except Exception as e:
                                print(f"抓取 {car_name_out} 的评价时出错：{e}")
                                await take_screenshot(review_page, f"review_error_{car_name_out}.png")
                                
                        next_button = await koubei_page.query_selector('//a[contains(@class,"next")]')
                        if next_button:
                            await next_button.click()
                            await koubei_page.wait_for_load_state("networkidle")
                            await asyncio.sleep(2)
                        else:
                            break

                    except Exception as e:
                        print(f"Error while processing reviews for {car_name_out}: {e}")
                        await take_screenshot(koubei_page, f"koubei_page_error_{car_name_out}.png")

                await koubei_page.close()

            else:
                print(f"未能找到 {car_name_out} 的口碑按钮")

        except Exception as e:
            print(f"抓取 {car_name_out} 信息时出错：{e}")
            await take_screenshot(page, f"car_page_error_{car_name_out}.png")

    await asyncio.sleep(1)
    await browser.close()

async def main():
    async with async_playwright() as playwright:
        await run(playwright)

asyncio.run(main())
