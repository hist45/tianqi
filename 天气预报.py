import os
import csv
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from lxml import etree
import requests


def getWeather(url, max_retries=3, use_selenium=True):
    """获取指定URL的天气数据，可选择使用Selenium或requests"""
    weather_info = []

    if use_selenium:
        # 使用Selenium方式
        return getWeatherWithSelenium(url, max_retries)
    else:
        # 使用requests方式
        return getWeatherWithRequests(url, max_retries)


def getWeatherWithSelenium(url, max_retries=3):
    """使用Edge浏览器获取指定URL的天气数据"""
    weather_info = []

    # 配置Edge浏览器
    edge_options = Options()
    edge_options.add_argument("--headless")  # 无头模式，可根据需要注释掉以查看浏览器操作
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--window-size=1920,1080")
    edge_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36")

    # 初始化Edge浏览器
    service = Service(EdgeChromiumDriverManager().install())
    driver = webdriver.Edge(service=service, options=edge_options)

    for attempt in range(max_retries):
        try:
            print(f"正在爬取: {url} (尝试 {attempt + 1}/{max_retries})")

            # 打开网页
            driver.get(url)

            # 等待页面加载
            time.sleep(35)  # 延长页面加载等待时间到25秒

            # 尝试点击"查看更多"按钮（如果存在）
            try:
                more_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, '/html/body/div[7]/div[1]/div[4]/ul/div'))
                )
                more_button.click()
                print("点击了'查看更多'按钮")
                time.sleep(3)  # 等待更多数据加载
            except Exception as e:
                print(f"未找到查看更多按钮或点击失败: {e}")

            # 获取页面源码
            page_source = driver.page_source
            resp_html = etree.HTML(page_source)
            resp_list = resp_html.xpath("//ul[@class='thrui']/li")

            if not resp_list:
                # 尝试备选XPath选择器
                print("标准XPath未找到数据，尝试备选选择器...")
                resp_list = resp_html.xpath("//div[contains(@class, 'weather-table')]/ul/li")

            if not resp_list:
                print(f"警告：未能从{url}获取任何数据")
                driver.quit()
                return weather_info

            print(f"从{url}获取到{len(resp_list)}条记录")

            for li in resp_list:
                day_data = {}
                # 提取日期
                date_text = li.xpath("./div[1]/text()")
                if date_text:
                    date = date_text[0].split(' ')[0]
                    day_data['date'] = date
                else:
                    continue  # 跳过无日期记录

                # 提取气温
                high = li.xpath("./div[2]/text()")[0].replace("°C", "") if li.xpath("./div[2]/text()") else ""
                low = li.xpath("./div[3]/text()")[0].replace("°C", "") if li.xpath("./div[3]/text()") else ""
                weather = li.xpath("./div[4]/text()")[0] if li.xpath("./div[4]/text()") else ""
                wind = li.xpath("./div[5]/text()")[0].strip() if li.xpath("./div[5]/text()") else ""

                day_data.update({
                    'high_temp': high,
                    'low_temp': low,
                    'weather': weather,
                    'wind_direction': wind
                })
                weather_info.append(day_data)

            # 成功获取数据，退出重试循环
            break

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = random.uniform(5, 10)  # 随机等待时间，避免请求过于规律
                print(f"爬取{url}时出错 ({e})，{wait_time:.2f}秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"爬取{url}失败 (最大重试次数已达)")

    # 关闭浏览器
    driver.quit()
    return weather_info


def getWeatherWithRequests(url, max_retries=3):
    """使用requests获取指定URL的天气数据"""
    weather_info = []
    headers = {
        'Cookie': 'UserId=17492113410185356; Hm_lvt_7c50c7060f1f743bccf8c150a646e90a=1749211341; '
                  'HMACCCOUNT=54F2FF78AEECB908; Hm_lvt_5326a74bb3e3143580750a123a85e7a1=1749211410; '
                  'Hm_lpvt_5326a74bb3e3143580750a123a85e7a1=1749212779; '
                  'Hm_lpvt_7c50c7060f1f743bccf8c150a646e90a=1749212779',
        'referer': 'https://lishi.tianqi.com/sanya/201201.html',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    # 构建POST请求数据
    post_data = {
        'city': 'sanya',
        'yearmonth': url.split('/')[-1].replace('.html', ''),  # 提取年月信息
        'action': 'getHistoryData',
        't': str(int(time.time() * 1000))  # 添加时间戳，防止缓存
    }

    for attempt in range(max_retries):
        try:
            print(f"正在爬取: {url} (尝试 {attempt + 1}/{max_retries})")

            # 使用POST请求
            response = requests.post(url, headers=headers, data=post_data, timeout=10)
            response.raise_for_status()

            resp_html = etree.HTML(response.text)
            resp_list = resp_html.xpath("//ul[@class='thrui']/li")

            if not resp_list:
                # 尝试备选XPath选择器
                print("标准XPath未找到数据，尝试备选选择器...")
                resp_list = resp_html.xpath("//div[contains(@class, 'weather-table')]/ul/li")

            if not resp_list:
                print(f"警告：未能从{url}获取任何数据")
                return weather_info

            print(f"从{url}获取到{len(resp_list)}条记录")

            for li in resp_list:
                day_data = {}
                # 提取日期
                date_text = li.xpath("./div[1]/text()")
                if date_text:
                    date = date_text[0].split(' ')[0]
                    day_data['date'] = date
                else:
                    continue  # 跳过无日期记录

                # 提取气温
                high = li.xpath("./div[2]/text()")[0].replace("°C", "") if li.xpath("./div[2]/text()") else ""
                low = li.xpath("./div[3]/text()")[0].replace("°C", "") if li.xpath("./div[3]/text()") else ""
                weather = li.xpath("./div[4]/text()")[0] if li.xpath("./div[4]/text()") else ""
                wind = li.xpath("./div[5]/text()")[0].strip() if li.xpath("./div[5]/text()") else ""

                day_data.update({
                    'high_temp': high,
                    'low_temp': low,
                    'weather': weather,
                    'wind_direction': wind
                })
                weather_info.append(day_data)

            # 成功获取数据，退出重试循环
            break

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = random.uniform(2, 5)  # 随机等待时间，避免请求过于规律
                print(f"爬取{url}时出错 ({e})，{wait_time:.2f}秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"爬取{url}失败 (最大重试次数已达)")

    return weather_info


def save_annual_data(annual_data, filename):
    """保存全年数据到CSV"""
    try:
        # 验证数据完整性
        if not annual_data:
            print("错误：没有数据可保存!")
            return

        # 按日期排序
        annual_data.sort(key=lambda x: x.get('date', '9999-99-99'))

        # 保存数据
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['日期', '最高气温', '最低气温', '天气', '风向'])
            for day in annual_data:
                writer.writerow([
                    day.get('date', ''),
                    day.get('high_temp', ''),
                    day.get('low_temp', ''),
                    day.get('weather', ''),
                    day.get('wind_direction', '')
                ])

        # 统计每月数据量
        month_counts = {}
        for day in annual_data:
            date = day.get('date', '')
            if date:
                month = date[:7]  # YYYY-MM
                month_counts[month] = month_counts.get(month, 0) + 1

        print(f"数据已保存至{filename}，共{len(annual_data)}条记录")
        print("每月数据量统计:")
        for month in sorted(month_counts.keys()):
            print(f"  {month}: {month_counts[month]}天")

    except Exception as e:
        print(f"保存文件时出错: {e}")


def main():
    """主函数"""
    city = "sanya"
    year = 2012
    csv_file = f"{city}_{year}_weather.csv"

    print(f"开始爬取{year}年{city}天气数据...")

    # 检查是否已存在数据文件
    if os.path.exists(csv_file):
        print(f"发现已有数据文件: {csv_file}")
        choice = input("是否重新爬取? (y/n): ").lower()
        if choice != 'y':
            print("使用已有数据")
            return

    annual_data = []

    # 爬取全年12个月的数据
    for month in range(1, 13):
        month_str = f"{month:02d}"
        url = f"http://lishi.tianqi.com/{city}/{year}{month_str}.html"

        print(f"\n爬取{year}年{month}月数据: {url}")
        # 默认使用Selenium方式，如需使用requests，将use_selenium改为False
        month_data = getWeather(url, use_selenium=True)

        # 检查是否成功获取该月数据
        if not month_data:
            print(f"警告：未能获取{year}年{month}月数据，尝试备用URL...")
            # 尝试备用URL格式
            alt_url = f"http://lishi.tianqi.com/{city}/{year}/{month_str}.html"
            month_data = getWeather(alt_url, use_selenium=True)

        annual_data.extend(month_data)

        # 显示当前进度
        print(f"已爬取{len(month_data)}条{year}年{month}月数据")

        # 防止请求过于频繁
        wait_time = random.uniform(3, 6)  # 随机等待时间
        print(f"等待{wait_time:.2f}秒后继续...")
        time.sleep(wait_time)

    # 保存全年数据
    save_annual_data(annual_data, csv_file)

    print(f"\n{year}年{city}天气数据爬取完成!")
    print(f"数据已保存至: {csv_file}")


if __name__ == "__main__":
    main()
