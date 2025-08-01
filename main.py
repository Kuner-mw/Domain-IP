from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_dns_records_with_playwright(host):
    try:
        with sync_playwright() as p:
            logging.info(f"正在启动无头浏览器并访问: https://tool.chinaz.com/dns/{host}")
            
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                locale="zh-CN",
                timezone_id="Asia/Shanghai"
            )
            page = context.new_page()

            # 注入反检测脚本
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            # 访问 URL
            page.goto(f"https://tool.chinaz.com/dns/{host}")
            page.wait_for_load_state('networkidle', timeout=10000)
            time.sleep(2)

            # 模拟滚动触发懒加载
            page.mouse.wheel(0, 1000)
            time.sleep(1)

            # 等待表格加载
            try:
                logging.info("等待表格加载，超时设置为 10 秒...")
                page.wait_for_selector('table.item-table', timeout=10000)
                logging.info("表格加载成功。")
            except Exception:
                page.screenshot(path="debug_failed_table.png", full_page=True)
                return "表格加载失败，已截图为 debug_failed_table.png"

            # 获取渲染后的HTML
            html_content = page.content()
            browser.close()

            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            ip_addresses = set()
            ip_tables = soup.find_all('table', class_='item-table')

            if not ip_tables:
                return "未能找到DNS解析结果表格，可能页面结构已更改或查询无结果。"

            for ip_table in ip_tables:
                ip_info_paragraphs = ip_table.find_all('p', class_=['fl', 'tl'])
                for p_tag in ip_info_paragraphs:
                    link = p_tag.find('a')
                    if link:
                        ip_address = link.get_text(strip=True)
                        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip_address):
                            ip_addresses.add(ip_address)

            if not ip_addresses:
                return "未能从表格中提取到任何IP地址。"
            return list(ip_addresses)

    except Exception as e:
        return f"发生严重错误: {e}"


# 示例用法
if __name__ == "__main__":
    host = 'api.github.com'
    logging.info(f"正在使用 Playwright 模拟浏览器查询域名: {host} 的DNS解析记录...")
    result = get_dns_records_with_playwright(host)
    if isinstance(result, list):
        logging.info("查询到的IP地址:")
        for ip in result:
            logging.info(f"- {ip}")
    else:
        logging.error(f"查询失败: {result}")
