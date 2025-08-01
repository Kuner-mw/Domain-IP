from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime, timezone

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
        with sync_playwright() as p:
            print(f"正在查询域名: {host}")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(f"https://tool.chinaz.com/dns/{host}")

            try:
                page.wait_for_selector('table.item-table', timeout=2000)
            except Exception:
                print(f"刷新页面: {host}")
                page.reload()
            
            page.wait_for_selector('table.item-table', timeout=30000)
            html_content = page.content()
            browser.close()

            soup = BeautifulSoup(html_content, 'html.parser')
            ip_addresses = set()
            
            ip_tables = soup.find_all('table', class_='item-table')
            
            if not ip_tables:
                return []
            
            for ip_table in ip_tables:
                ip_info_paragraphs = ip_table.find_all('p', class_=['fl', 'tl'])
                
                for p_tag in ip_info_paragraphs:
                    link = p_tag.find('a')
                    if link:
                        ip_address = link.get_text(strip=True)
                        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip_address):
                            ip_addresses.add(ip_address)
            
            return list(ip_addresses)

    except Exception as e:
        print(f"查询 {host} 时发生错误: {e}")
        return []

def process_domains():
    # 读取domains.txt文件
    try:
        with open('domains.txt', 'r') as f:
            domains = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"读取domains.txt失败: {e}")
        return

    # 准备hosts_results.txt的头部内容
    current_time = datetime.now(timezone.utc).strftime("%a %b %d %H:%M:%S UTC %Y")
    header = f"""# GitHub 相关域名最新 IP 地址 (Hosts 格式)
# 最后更新于: {current_time}

"""

    # 创建/覆盖hosts_results.txt文件
    with open('hosts_results.txt', 'w') as f:
        f.write(header)

        # 处理每个域名
        for domain in domains:
            print(f"\n正在处理域名: {domain}")
            ips = get_dns_records_with_playwright(domain)
            
            # 如果找到IP地址，写入文件
            if ips:
                for ip in ips:
                    f.write(f"{ip} {domain}\n")
                print(f"成功: {domain} -> {', '.join(ips)}")
            else:
                print(f"警告: 未能找到 {domain} 的IP地址")
            
            # 添加短暂延迟以避免请求过于频繁
            time.sleep(2)

if __name__ == "__main__":
    print("开始处理域名列表...")
    process_domains()
    print("\n处理完成，结果已写入 hosts_results.txt")
