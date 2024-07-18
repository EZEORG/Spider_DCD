from playwright.sync_api import sync_playwright
import re
import time
from pathlib import Path

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

def run(playwright, max_scrolls=10):
    base_output_dir = 'dcd_data'
    create_directory(base_output_dir)

    # 自定义HTTP头
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
    
    page.goto("https://www.dongchedi.com/auto/library/x-x-x-x-x-x-x-x-x-x-x")

    # 等待页面加载完成
    page.wait_for_timeout(3000)

    car_data = set()
    scroll_count = 0

    output_file = Path(base_output_dir) / "car_cards.txt"

    while scroll_count < max_scrolls:
        # 获取当前页面所有车的卡片元素
        car_cards = page.query_selector_all('//div[contains(@class,"car-list_card")]')
        print(f"Found {len(car_cards)} car cards on scroll {scroll_count + 1}.")

        # 批量提取车卡片元素信息并添加到集合中避免重复
        new_car_data = {car_card: car_card.inner_text() for car_card in car_cards if car_card.inner_text() not in car_data}
        car_data.update(new_car_data.values())

        for index, car_card in enumerate(new_car_data.keys(), start=1):
            try:
                # 点击“参数”按钮
                param_button = car_card.query_selector('//a[contains(text(),"参数")]')
                if param_button:
                    with context.expect_page() as new_page_info:
                        param_button.click()

                    new_page = new_page_info.value
                    new_page.wait_for_load_state("networkidle")
                    time.sleep(2)
                    content = new_page.content()

                    print(f"参数页面内容已抓取")

                    new_page.close()

            except Exception as e:
                print(f"抓取 car {index} 信息时出错：{e}")

        # 将新车卡片信息保存到txt文件中
        with open(output_file, 'a', encoding='utf-8') as f:
            for car_info in new_car_data.values():
                f.write(car_info + '\n')

        # 滚动页面以加载更多的汽车卡片
        last_height = page.evaluate("document.body.scrollHeight")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)  # 等待页面加载
        new_height = page.evaluate("document.body.scrollHeight")

        # 检查页面高度是否发生变化，如果没有变化则停止滚动
        if new_height == last_height:
            break
        
        scroll_count += 1

    print(f"车卡片信息已保存到 {output_file}")

    browser.close()

with sync_playwright() as playwright:
    run(playwright, max_scrolls=10)
