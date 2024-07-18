from playwright.sync_api import sync_playwright
import re
import time
from pathlib import Path
import csv
from lxml import html

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

def run(playwright):
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

    car_data = {}
    scroll_count = 0
    max_scrolls = 2

    while scroll_count < max_scrolls:
        # 获取当前页面所有车的卡片元素
        car_cards = page.query_selector_all('//div[contains(@class,"car-list_card")]')
        print(f"Found {len(car_cards)} car cards on scroll {scroll_count + 1}.")

        # 提取车卡片元素信息并添加到集合中避免重复
        for car_card in car_cards:
            car_name = car_card.query_selector('//a[contains(@class,"card_name")]').inner_text().strip()
            if car_name not in car_data:
                car_data[car_name] = car_card

        # 滚动页面以加载更多的汽车卡片
        last_height = page.evaluate("document.body.scrollHeight")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)  # 等待页面加载
        new_height = page.evaluate("document.body.scrollHeight")

        # 检查页面高度是否发生变化，如果没有变化则停止滚动
        if new_height == last_height:
            break
        
        scroll_count += 1

    # 点击每个车的参数按钮并抓取数据
    for car_name, car_card in car_data.items():
        try:
            car_name_out = car_name
            # 点击“参数”按钮
            param_button = car_card.query_selector('//a[contains(text(),"参数")]')
            if param_button:
                with context.expect_page() as new_page_info:
                    param_button.click()

                new_page = new_page_info.value
                new_page.wait_for_load_state("networkidle")
                time.sleep(2)
                content = new_page.content()
                dom = html.fromstring(content)

                # 获取所有车名
                car_names = dom.xpath('//a[contains(@class,"cell_car")]/text()')
                car_name_texts = [name.strip() for name in car_names]

                # 获取属性名
                attribute_names = dom.xpath('//label/text()')
                attribute_names = [attr.strip() for attr in attribute_names]

                # 初始化数据结构
                car_data_dict = {name: {attr: '' for attr in attribute_names} for name in car_name_texts}

                # 获取价格信息
                prices = dom.xpath('//div[contains(@class,"official-price")]/text()')
                price_texts = [price.strip() for price in prices]

                # 将价格信息填充到“官方指导价”列中
                for i, car_name in enumerate(car_name_texts):
                    if i < len(price_texts):
                        car_data_dict[car_name]['官方指导价'] = price_texts[i]

                # 获取属性值
                xpath_value = '//div[@data-row-anchor]/parent::*/div[contains(@class,"table_row") and not(contains(@class,"title"))]'
                value_elements = dom.xpath(xpath_value)
                for elem in value_elements:
                    # 遍历嵌套元素中的每一行
                    nested_elem = elem.xpath('./div[contains(@class,"nest")]')
                    if nested_elem:
                        nested_rows = elem.xpath('.//div[contains(@class,"table_row")]')
                        for row_index, row in enumerate(nested_rows):
                            # 遍历每个车名对应的列
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

                # 保存为CSV文件
                csv_file_path = Path(base_output_dir) / sanitize_filename(f'{car_name_out}.csv')
                with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
                    writer = csv.DictWriter(csv_file, fieldnames=['车名'] + attribute_names)
                    writer.writeheader()
                    for car in car_name_texts:
                        row = {'车名': car}
                        row.update(car_data_dict[car])
                        writer.writerow(row)

                print(f"数据已保存到 {csv_file_path}")

                new_page.close()

        except Exception as e:
            print(f"抓取 {car_name} 信息时出错：{e}")

    page.wait_for_timeout(3000)
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
