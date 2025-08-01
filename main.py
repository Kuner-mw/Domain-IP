from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime

def get_dns_records_with_playwright(host):
    """
    使用 Playwright 模拟浏览器行为，从站长工具页面抓取DNS解析记录。
    """
    error_msg = None
    try:
        with sync_playwright() as p:
            print(f"正在查询域名: {host}")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 访问DNS查询页面
            page.goto(f"https://tool.chinaz.com/dns/{host}")

            try:
                # 首次等待2秒
                page.wait_for_selector('table.item-table', timeout=2000)
            except Exception:
                print(f"刷新页面: {host}")
                page.reload()
                try:
                    # 刷新后再等待30秒
                    page.wait_for_selector('table.item-table', timeout=8000)
                except Exception as e:
                    error_msg = f"加载超时或页面错误: {str(e)}"
                    raise

            # 获取页面内容
            html_content = page.content()
            
            # 关闭浏览器
            browser.close()

            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            ip_addresses = set()
            
            # 查找所有IP表格
            ip_tables = soup.find_all('table', class_='item-table')
            
            if not ip_tables:
                error_msg = "未找到DNS解析结果表格"
                return [], error_msg
            
            # 提取IP地址
            for ip_table in ip_tables:
                ip_info_paragraphs = ip_table.find_all('p', class_=['fl', 'tl'])
                for p_tag in ip_info_paragraphs:
                    link = p_tag.find('a')
                    if link:
                        ip_address = link.get_text(strip=True)
                        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip_address):
                            ip_addresses.add(ip_address)
            
            if not ip_addresses:
                error_msg = "未能从表格中提取到任何IP地址"
                return [], error_msg
            
            return list(ip_addresses), None

    except Exception as e:
        error_msg = error_msg or f"发生错误: {str(e)}"
        return [], error_msg

def read_domains(filename):
    """读取域名文件"""
    try:
        with open(filename, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"读取域名文件出错: {e}")
        return []

def write_hosts(filename, results):
    """写入hosts格式文件"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            # 写入头部注释
            f.write("# GitHub 相关域名最新 IP 地址 (Hosts 格式)\n")
            current_time = "2025-08-01 07:08:02"  # 使用当前UTC时间
            f.write(f"# 最后更新于: {current_time} UTC\n\n")
            
            # 写入成功的记录
            for domain, ips, error in results:
                if ips:
                    f.write(f"{ips[0]} {domain}\n")
            
            # 写入失败的记录作为注释
            f.write("\n# 以下域名解析失败:\n")
            for domain, ips, error in results:
                if not ips:
                    f.write(f"# {domain} - {error}\n")

    except Exception as e:
        print(f"写入hosts文件出错: {e}")

def main():
    domains = read_domains('domains.txt')
    results = []
    total = len(domains)
    
    print(f"开始处理 {total} 个域名...")
    
    for i, domain in enumerate(domains, 1):
        print(f"\n[{i}/{total}] 处理域名: {domain}")
        ips, error = get_dns_records_with_playwright(domain)
        results.append((domain, ips, error))
        if ips:
            print(f"找到IP: {', '.join(ips)}")
        else:
            print(f"查询失败: {error}")
        
        # 添加延迟避免请求过快
        time.sleep(2)
    
    write_hosts('hosts_results.txt', results)
    print("\n完成! 结果已写入 hosts_results.txt")

    # 打印统计信息
    success_count = sum(1 for _, ips, _ in results if ips)
    print(f"\n统计信息:")
    print(f"总域名数: {total}")
    print(f"成功解析: {success_count}")
    print(f"解析失败: {total - success_count}")

if __name__ == "__main__":
    main()
