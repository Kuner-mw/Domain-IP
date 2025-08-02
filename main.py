from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import logging
import time
from datetime import datetime, timezone

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
                return []

            # 获取渲染后的HTML
            html_content = page.content()
            browser.close()

            # 解析HTML
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
                        if ip_address not in {"0.0.0.0", "20.205.243.166", "20.200.245.247", "20.27.177.113"} and re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip_address):
                            ip_addresses.add(ip_address)


            return list(ip_addresses)

    except Exception as e:
        logging.error(f"查询出错: {e}")
        return []

def read_domains():
    try:
        with open('domains.txt', 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    except Exception as e:
        logging.error(f"读取domains.txt失败: {e}")
        return []

def save_results(results):
    try:
        with open('hosts_results.txt', 'w', encoding='utf-8') as f:
            # 写入头部信息
            f.write("# GitHub 相关域名最新 IP 地址\n")
            f.write(f"# 最后更新于: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n")
            
            # 写入解析结果
            for domain, ips in results:
                if ips:
                    # 为每个域名的每个IP创建一行
                    for ip in ips:
                        f.write(f"{domain} {ip}\n")
                else:
                    f.write(f"# {domain} - 未能获取IP地址\n")
            
            # 添加统计信息
            total_domains = len(results)
            successful_domains = sum(1 for _, ips in results if ips)
            total_ips = sum(len(ips) for _, ips in results if ips)
            f.write(f"\n# 统计信息:\n")
            f.write(f"# 总域名数: {total_domains}\n")
            f.write(f"# 成功解析域名数: {successful_domains}\n")
            f.write(f"# 总IP数: {total_ips}\n")
            
    except Exception as e:
        logging.error(f"保存结果到hosts_results.txt失败: {e}")

def main():
    domains = read_domains()
    if not domains:
        logging.error("没有找到要查询的域名")
        return

    results = []
    failed_domains = []
    total = len(domains)
    
    # 第一轮查询
    for i, domain in enumerate(domains, 1):
        logging.info(f"第一轮查询 ({i}/{total}): {domain}")
        ips = get_dns_records_with_playwright(domain)
        if ips:
            logging.info(f"成功获取到 {domain} 的IP地址: {', '.join(ips)}")
            results.append((domain, ips))
        else:
            logging.warning(f"未能获取到 {domain} 的IP地址，将在第二轮重试")
            failed_domains.append(domain)
        
        # 每次查询后延时2秒
        time.sleep(2)
    
    # 第二轮重试失败的域名
    if failed_domains:
        logging.info(f"开始第二轮查询，共有 {len(failed_domains)} 个域名需要重试")
        retry_total = len(failed_domains)
        
        for i, domain in enumerate(failed_domains, 1):
            logging.info(f"第二轮查询 ({i}/{retry_total}): {domain}")
            ips = get_dns_records_with_playwright(domain)
            if ips:
                logging.info(f"重试成功：{domain} 的IP地址: {', '.join(ips)}")
                results.append((domain, ips))
            else:
                logging.warning(f"重试失败：仍未能获取到 {domain} 的IP地址")
                results.append((domain, []))
            
            # 每次查询后延时2秒
            time.sleep(2)
    
    # 按域名排序结果
    results.sort(key=lambda x: x[0])
    
    save_results(results)
    logging.info("所有域名处理完成，结果已保存到 hosts_results.txt")

if __name__ == "__main__":
    main()
