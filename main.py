from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import time

def get_dns_records_with_playwright(host):
    """
    使用 Playwright 模拟浏览器行为，从站长工具页面抓取DNS解析记录。

    Args:
        host (str): 要查询的域名或IP地址。

    Returns:
        list: 一个包含所有查找到的IP地址的列表。
        str: 如果抓取失败，则返回错误消息。
    """
    try:
        # 使用 sync_playwright 启动浏览器上下文
        with sync_playwright() as p:
            print(f"正在启动浏览器并访问: https://tool.chinaz.com/dns/{host}")
            # 启动 Chromium 浏览器，设置 headless=False 为非无头模式
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            # 访问 URL
            page.goto(f"https://tool.chinaz.com/dns/{host}")

            # 增加一个刷新逻辑：在访问后2秒内如果没有结果则刷新一次
            try:
                print("等待IP地址表格首次加载...")
                # 首次等待2秒，如果表格未出现，则刷新
                page.wait_for_selector('table.item-table', timeout=2000)
                print("IP地址表格已加载。")
            except Exception:
                print("2秒内未加载完成，正在刷新页面...")
                page.reload()
                print("页面已刷新。")
            
            # 刷新后，等待 IP 地址表格加载完成，最长等待30秒
            print("等待IP地址表格加载...")
            page.wait_for_selector('table.item-table', timeout=30000)
            print("IP地址表格已加载。")

            # 获取页面渲染后的完整 HTML 内容
            html_content = page.content()
            browser.close() # 关闭浏览器

            # 使用 BeautifulSoup 解析 HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            ip_addresses = set()  # 使用集合来自动去重
            
            # 查找所有包含IP地址的表格。
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
        return f"发生错误: {e}"

# 示例用法
if __name__ == "__main__":
    host = 'github.com'
    print(f"正在使用 Playwright 模拟浏览器查询域名: {host} 的DNS解析记录...")
    result = get_dns_records_with_playwright(host)
    if isinstance(result, list):
        print("查询到的IP地址:")
        for ip in result:
            print(f"- {ip}")
    else:
        print(f"查询失败: {result}")
