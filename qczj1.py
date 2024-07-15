import time
import pandas as pd
from lxml import html
from playwright.sync_api import sync_playwright

def scrape_reviews(page):
    reviews = []
    while True:
        page.wait_for_selector('//li[contains(@class,"jump")]//a')
        review_links = page.query_selector_all('//li[contains(@class,"jump")]//a')

        for link in review_links:
            link.click()
            page.wait_for_selector('//div[contains(@class,"title-name")]//a')
            content = page.content()
            tree = html.fromstring(content)

            car_name = tree.xpath('//div[contains(@class,"title-name")]//a//text()')[0]
            user_ids = tree.xpath('//a[contains(@id,"nickname")]//text()')
            comments = tree.xpath('//p[@class="kb-item-msg"]/text()')
            items = tree.xpath('//p[@class="kb-item-msg"]/preceding-sibling::h1//text()')

            for user_id in user_ids:
                review_dict = {'Car Name': car_name, 'User ID': user_id}
                for item, comment in zip(items, comments):
                    review_dict[item] = comment
                reviews.append(review_dict)

            page.go_back()

        next_button = page.query_selector('//a[contains(@class,"next")]')
        if next_button:
            next_button.click()
        else:
            break

    return reviews

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto('https://www.autohome.com.cn/price/#pvareaid=6861598')

        page.wait_for_selector('//li[contains(@class,"group")]')
        car_cards = page.query_selector_all('//li[contains(@class,"group")]')

        for index, card in enumerate(car_cards):
            print(f"Clicking car card {index}")
            card.click()
            time.sleep(5)  # Wait longer for any potential modal to appear
            
            # 检查并关闭可能弹出的弹窗
            try:
                page.wait_for_selector('//span[contains(@class,"close")]', timeout=5000)
                page.click('//span[contains(@class,"close")]')
                print("Closed a popup")
            except Exception as e:
                print("No popup found or error:", e)
            
            try:
                page.wait_for_selector('div#navTop a:has-text("口碑")', timeout=10000)
                page.click('div#navTop a:has-text("口碑")')
                print("Clicked '口碑' button")
            except Exception as e:
                print("Failed to click '口碑' button:", e)
                continue

            reviews = scrape_reviews(page)
            df = pd.DataFrame(reviews)
            df.to_csv(f'car_{index}_reviews.csv', index=False, encoding='utf-8-sig')

            page.go_back()
            page.go_back()

        browser.close()

if __name__ == "__main__":
    main()
