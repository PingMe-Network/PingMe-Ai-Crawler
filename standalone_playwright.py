import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def scrape_tea4life():
    with sync_playwright() as p:
        print("Đang khởi động trình duyệt ảo Chromium...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        url = "https://www.tea4life.click/"
        print(f"Đang truy cập {url} và chờ trang web render xong SPA...")
        
        # Truy cập và chờ trạng thái mạng tĩnh (JS đã load xong)
        page.goto(url, wait_until="networkidle")
        
        # Lấy HTML cuối cùng đã được Playwright render xong
        html = page.content()
        print("Đã lấy được HTML hoàn chỉnh, đang làm sạch...")
        
        # Đưa HTML cho BeautifulSoup làm sạch
        soup = BeautifulSoup(html, 'html.parser')
        
        # Xóa các thẻ chứa rác
        for tag in soup(["script", "style", "noscript", "meta", "header", "footer"]):
            tag.extract()
            
        # Lấy text sạch
        raw_text = soup.get_text(separator=' ', strip=True)
        
        data = {
            'url': url,
            'raw_text': raw_text
        }
        
        # Ghi ra file json
        with open('playwright_output.json', 'w', encoding='utf-8') as f:
            json.dump([data], f, ensure_ascii=False, indent=4)
            
        print("\n=== KẾT QUẢ CÀO ĐƯỢC ===")
        print(json.dumps(data, ensure_ascii=False, indent=4))
        print("========================\n")
        print("Đã lưu kết quả thành công vào file playwright_output.json!")
        
        browser.close()

if __name__ == "__main__":
    scrape_tea4life()
