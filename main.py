from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime, timezone
import sys
import os

def setup_logging():
    """Configure logging to output to both file and console"""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('dns_lookup.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def get_dns_records_with_playwright(host, logger):
    """
    使用 Playwright 模拟浏览器行为，从站长工具页面抓取DNS解析记录。
    """
    try:
        with sync_playwright() as p:
            logger.info(f"正在查询域名: {host}")
            
            # 在GitHub Actions环境中使用特定的浏览器启动参数
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            
            page = browser.new_page()
            
            page.goto(f"https://tool.chinaz.com/dns/{host}")

            try:
                page.wait_for_selector('table.item-table', timeout=5000)
            except Exception:
                logger.info(f"需要刷新页面: {host}")
                page.reload()
                page.wait_for_selector('table.item-table', timeout=30000)
            
            html_content = page.content()
            browser.close()

            soup = BeautifulSoup(html_content, 'html.parser')
            ip_addresses = set()
            
            ip_tables = soup.find_all('table', class_='item-table')
            
            if not ip_tables:
                logger.warning(f"未找到 {host} 的DNS记录")
                return []
            
            for ip_table in ip_tables:
                ip_info_paragraphs = ip_table.find_all('p', class_=['fl', 'tl'])
                
                for p_tag in ip_info_paragraphs:
                    link = p_tag.find('a')
                    if link:
                        ip_address = link.get_text(strip=True)
                        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip_address):
                            ip_addresses.add(ip_address)
            
            if ip_addresses:
                logger.info(f"成功获取 {host} 的IP地址: {', '.join(ip_addresses)}")
            else:
                logger.warning(f"未能提取 {host} 的IP地址")
            
            return list(ip_addresses)

    except Exception as e:
        logger.error(f"查询 {host} 时发生错误: {str(e)}", exc_info=True)
        return []

def process_domains(logger):
    """处理域名列表并生成hosts文件"""
    try:
        # 确保工作目录正确（在GitHub Actions中特别重要）
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        # 读取domains.txt文件
        logger.info("正在读取 domains.txt")
        with open('domains.txt', 'r') as f:
            domains = [line.strip() for line in f if line.strip()]
        
        logger.info(f"成功读取 {len(domains)} 个域名")

        # 准备hosts_results.txt的头部内容
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        header = f"""# GitHub 相关域名最新 IP 地址 (Hosts 格式)
# 最后更新于: {current_time}

"""

        # 创建/覆盖hosts_results.txt文件
        logger.info("开始写入 hosts_results.txt")
        with open('hosts_results.txt', 'w') as f:
            f.write(header)

            # 处理每个域名
            for index, domain in enumerate(domains, 1):
                logger.info(f"正在处理 [{index}/{len(domains)}] {domain}")
                ips = get_dns_records_with_playwright(domain, logger)
                
                # 如果找到IP地址，写入文件
                if ips:
                    for ip in ips:
                        f.write(f"{ip} {domain}\n")
                
                # 添加短暂延迟以避免请求过于频繁
                if index < len(domains):  # 最后一个域名后不需要延迟
                    time.sleep(3)

        logger.info("所有域名处理完成")

    except Exception as e:
        logger.error(f"处理过程中发生错误: {str(e)}", exc_info=True)
        raise

def main():
    """主函数"""
    logger = setup_logging()
    logger.info("开始执行DNS查询任务")
    
    try:
        process_domains(logger)
        logger.info("任务完成")
        return 0
    except Exception as e:
        logger.error(f"任务失败: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
