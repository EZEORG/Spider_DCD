import asyncio
import pandas as pd
from lxml import html
from playwright.async_api import async_playwright

async def scrape_reviews(page):
    reviews = []
    while True:
        await page.wait_for_selector('//li[contains(@class,"jump")]//a')
        review_links = await page.query_selector_all('//li[contains(@class,"jump")]//a')

        for link in review_links:
            await link.click()
            await page.wait_for_selector('//div[contains(@class,"title-name")]//a')
            content = await page.content()
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

            await page.go_back()

        next_button = await page.query_selector('//a[contains(@class,"next")]')
        if next_button:
            await next_button.click()
        else:
            break

    return reviews

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto('https://www.autohome.com.cn/price/#pvareaid=6861598')

        await page.wait_for_selector('//li[contains(@class,"group")]')
        car_cards = await page.query_selector_all('//li[contains(@class,"group")]')

        for index, card in enumerate(car_cards):
            await card.click()
            
            # 检查并关闭可能弹出的弹窗
            try:
                await page.wait_for_selector('//span[contains(@class,"close")]', timeout=5000)
                await page.click('//span[contains(@class,"close")]')
            except:
                pass
            
            await page.wait_for_selector('//div[@id="navTop"]//a[text()="口碑"]')
            await page.click('//div[@id="navTop"]//a[text()="口碑"]')

            reviews = await scrape_reviews(page)
            df = pd.DataFrame(reviews)
            df.to_csv(f'car_{index}_reviews.csv', index=False, encoding='utf-8-sig')

            await page.go_back()
            await page.go_back()

        await browser.close()

asyncio.run(main())
