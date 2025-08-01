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

def read_domains(filename):
    """读取域名文件"""
    try:
        with open(filename, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"读取域名文件出错: {e}")
        return []

def write_hosts(filename, results):
    """写入 hosts 格式文件"""
    try:
        with open(filename, 'w') as f:
            # 写入头部注释
            f.write("# GitHub 相关域名最新 IP 地址 (Hosts 格式)\n")
            utc_time = datetime.now(timezone.utc).strftime("%c UTC")
            f.write(f"# 最后更新于: {utc_time}\n\n")
            
            # 写入hosts记录
            for domain, ips in results:
                if ips:  # 如果有IP地址
                    # 取第一个IP地址作为hosts记录
                    f.write(f"{ips[0]} {domain}\n")
                else:
                    # 如果没有找到IP，添加注释
                    f.write(f"# {domain} - 未找到IP地址\n")
    except Exception as e:
        print(f"写入hosts文件出错: {e}")

def main():
    # 读取域名列表
    domains = read_domains('domains.txt')
    results = []
    
    # 查询每个域名的IP
    for domain in domains:
        print(f"\n处理域名: {domain}")
        ips = get_dns_records_with_playwright(domain)
        results.append((domain, ips))
        # 添加延时以避免请求过于频繁
        time.sleep(2)
    
    # 写入结果
    write_hosts('hosts_results.txt', results)
    print("\n完成! 结果已写入 hosts_results.txt")

if __name__ == "__main__":
    main()
