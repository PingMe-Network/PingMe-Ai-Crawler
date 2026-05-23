import os
import json
from openai import OpenAI
from ai.vector_store import search_similar_chunks

def get_api_key():
    return os.getenv("OPENAI_API_KEY")

def ask_ai_to_build_widget(crawl_id: int, user_query: str) -> dict:
    """Đưa text tinh hoa từ Vector DB và yêu cầu của user cho OpenAI xử lý"""
    api_key = get_api_key()
    if not api_key:
        return {"error": "Chưa cấu hình OPENAI_API_KEY trong file .env"}
        
    client = OpenAI(api_key=api_key)
    
    # Kéo 20 đoạn văn liên quan nhất từ Postgres pgvector
    relevant_chunks = search_similar_chunks(user_query, crawl_id)
    
    prompt = f"""
    Bạn là một trợ lý AI. Dưới đây là các mảnh nội dung trích xuất từ website (liên quan nhất đến câu hỏi):
    ---
    {relevant_chunks}
    ---
    
    Dựa vào nội dung trên, hãy trả lời yêu cầu sau của người dùng và định dạng kết quả dưới dạng JSON Widget.
    Yêu cầu của người dùng: "{user_query}"
    
    YÊU CẦU BẮT BUỘC ĐỂ LỌC NHIỄU:
    1. BẠN PHẢI LỌC BỎ RÁC: Chỉ trích xuất các Sản Phẩm / Món Ăn THỰC SỰ. Tuyệt đối KHÔNG trích xuất các bài viết Blog, Tin tức, Sự kiện, hay đoạn quảng cáo chung chung.
    2. Nếu món ăn không có giá tiền rõ ràng, có thể đặt price là 0. Nhưng ưu tiên lấy các món có giá.
    3. Trường "image_url": Phải là link ảnh chụp sản phẩm thật. Bỏ qua tất cả các ảnh có đuôi .svg, ảnh logo, banner sự kiện, hoặc icon (như emoji).
    4. Trích xuất TẤT CẢ các sản phẩm hợp lệ mà bạn tìm thấy.
    
    Hãy trả về ĐÚNG MỘT khối JSON (không thêm markdown giải thích). Cấu trúc mẫu:
    {{
        "title": "Tên danh mục",
        "items": [
            {{
                "name": "Tên sản phẩm",
                "price": 30000,
                "description": "Mô tả ngắn gọn (nếu có)",
                "image_url": "Link ảnh tuyệt đối"
            }}
        ]
    }}
    Lưu ý quan trọng 1: Trường "price" PHẢI LÀ SỐ NGUYÊN (Integer), tuyệt đối không chứa dấu chấm phẩy hay chữ "đ" (VD: 30000).
    Lưu ý quan trọng 2: Nếu nội dung có cấu trúc [Ảnh sản phẩm: <alt> - <link>], hãy trích xuất cái <link> đó gán vào trường "image_url". Nếu không có ảnh thì để chuỗi rỗng "".
    """
    
    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "Bạn là chuyên gia trích xuất dữ liệu. Luôn trả về JSON nguyên gốc."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }, # Bắt buộc OpenAI trả về JSON
            temperature=0.2,
            max_tokens=4096
        )
        
        result_text = response.choices[0].message.content.strip()
        return json.loads(result_text)
        
    except json.JSONDecodeError:
        return {"error": "AI trả về không phải chuẩn JSON", "text": result_text}
    except Exception as e:
        return {"error": f"Lỗi khi gọi OpenAI: {str(e)}"}
