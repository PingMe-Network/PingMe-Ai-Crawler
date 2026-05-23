from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import urllib.parse
import time
from ai.vector_store import embed_and_store_chunks

def scrape_url(start_url: str, crawl_id: int):
    from database.models import SessionLocal, WebCrawl, ChatRoom
    db = SessionLocal()
    
    try:
        room = db.query(ChatRoom).filter(ChatRoom.web_crawl_id == crawl_id).first()
        crawl = db.query(WebCrawl).filter(WebCrawl.id == crawl_id).first()
        crawl.status = "crawling"
        db.commit()
        
        max_clicks = crawl.total_pages or 10

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(start_url, wait_until="networkidle", timeout=60000)
            
            # Cuộn xuống cuối để load ảnh
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
            
            def extract_and_save():
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                
                for tag in soup(['script', 'style', 'nav', 'footer', 'noscript']):
                    tag.decompose()
                    
                # Trích xuất ảnh
                for img in soup.find_all('img'):
                    src = img.get('src') or img.get('data-src')
                    alt = img.get('alt', '')
                    if src:
                        src_lower = src.lower()
                        if not src_lower.endswith('.svg') and 'logo' not in src_lower and 'icon' not in src_lower and 'emoji' not in src_lower:
                            abs_url = urllib.parse.urljoin(start_url, src)
                            img.replace_with(f" [Ảnh sản phẩm: {alt} - {abs_url}] ")
                            
                text = soup.get_text(separator='\n')
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                clean_text = '\n'.join(lines)
                
                if clean_text:
                    from ai.vector_store import embed_and_store_chunks
                    embed_and_store_chunks(clean_text, start_url, crawl.id)
            
            # 1. Trích xuất trang mặc định ban đầu
            print(f"Crawling default state: {start_url}")
            extract_and_save()
            crawl.pages_crawled = 1
            db.commit()
            
            # 2. Tìm các phần tử Clickable (Tab, Category, Xem thêm)
            # 
            js_script = """
            () => {
                const selectors = [];
                const elements = document.querySelectorAll('*');
                // Từ khóa cấm click để tránh bị văng khỏi trang hoặc mua nhầm
                const forbidden = ['mua', 'cart', 'giỏ', 'buy', 'login', 'đăng nhập', 'xóa', 'thanh toán', 'đặt hàng', 'order', 'thêm'];
                
                let count = 0;
                for (let el of elements) {
                    const style = window.getComputedStyle(el);
                    const isClickable = style.cursor === 'pointer' || el.tagName.toLowerCase() === 'button' || el.getAttribute('role') === 'tab';
                    
                    if (isClickable && el.offsetParent !== null) {
                        const text = el.innerText ? el.innerText.toLowerCase() : '';
                        let isSafe = true;
                        
                        if (!text || text.length > 50) isSafe = false;
                        
                        for (let word of forbidden) {
                            if (text.includes(word)) {
                                isSafe = false;
                                break;
                            }
                        }
                        
                        if (isSafe) {
                            if (!el.id) {
                                el.id = 'spa-click-target-' + count;
                            }
                            selectors.push('#' + el.id);
                            count++;
                        }
                    }
                }
                return selectors;
            }
            """
            safe_selectors = page.evaluate(js_script)
            print(f"Found {len(safe_selectors)} safe buttons to click on SPA.")
            
            # 3. Lần lượt click và trích xuất
            clicks_done = 1
            for selector in safe_selectors:
                if clicks_done >= max_clicks:
                    break
                try:
                    print(f"Trying to click element: {selector}")
                    page.evaluate(f"document.querySelector('{selector}').click()")
                    page.wait_for_timeout(2000) # Đợi SPA render
                    
                    extract_and_save()
                    clicks_done += 1
                    
                    crawl.pages_crawled = clicks_done
                    db.commit()
                except Exception as e:
                    print(f"Error clicking element: {e}")
                    continue
            
            browser.close()
            crawl.status = "success"
            db.commit()
            print("SPA Crawl completed!")
            
    except Exception as e:
        print(f"SPA Crawl Error: {e}")
        db.rollback()
        crawl = db.query(WebCrawl).filter(WebCrawl.id == crawl_id).first()
        if crawl:
            crawl.status = "failed"
            db.commit()
    finally:
        db.close()
