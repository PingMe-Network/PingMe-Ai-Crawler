import json
import threading
from flask import Blueprint, request, jsonify
from crawler.scraper import scrape_url
from ai.openai_service import ask_ai_to_build_widget
from database.models import SessionLocal, WebCrawl, ChatRoom, ChatMessage

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route("/rooms", methods=["POST"])
def create_room():
    """API 1: Tạo phòng chat và bắt đầu cào ngầm 100 trang"""
    data = request.json
    url = data.get("url")
    if not url:
        return jsonify({"error": "Thiếu URL"}), 400
        
    db = SessionLocal()
    try:
        crawl = WebCrawl(url=url, status="crawling", pages_crawled=0, total_pages=10)
        db.add(crawl)
        db.commit()
        db.refresh(crawl)
        
        room = ChatRoom(web_crawl_id=crawl.id)
        db.add(room)
        db.commit()
        db.refresh(room)
        
        # Bắn ra một Luồng (Thread) chạy ngầm để cào 100 trang
        thread = threading.Thread(target=scrape_url, args=(url, crawl.id))
        thread.daemon = True
        thread.start()
        
        return jsonify({"room_id": room.id, "message": "Đang cào dữ liệu ngầm..."})
    finally:
        db.close()

@api_bp.route("/rooms/<int:room_id>/status", methods=["GET"])
def get_room_status(room_id):
    """API Check tiến độ cào 100 trang"""
    db = SessionLocal()
    try:
        room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
        if not room:
            return jsonify({"error": "Không tìm thấy"}), 404
        
        crawl = room.web_crawl
        return jsonify({
            "status": crawl.status,
            "pages_crawled": crawl.pages_crawled,
            "total_pages": crawl.total_pages
        })
    finally:
        db.close()

@api_bp.route("/rooms/<int:room_id>/chat", methods=["POST"])
def chat(room_id):
    """API 2: Chat với AI (Sử dụng RAG)"""
    data = request.json
    query = data.get("query")
    if not query:
        return jsonify({"error": "Thiếu nội dung câu hỏi"}), 400
        
    db = SessionLocal()
    try:
        room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
        if not room:
            return jsonify({"error": "Không tìm thấy phòng chat"}), 404
            
        if room.web_crawl.status != "success":
            return jsonify({"error": "Spider vẫn đang cào dữ liệu, vui lòng đợi..."}), 400
            
        # Lưu câu hỏi của User
        user_msg = ChatMessage(room_id=room.id, role="user", content=query)
        db.add(user_msg)
        db.commit()
        
        # Nhờ AI tạo Widget bằng RAG (Vector DB)
        result_json = ask_ai_to_build_widget(room.web_crawl.id, query)
        
        # Lưu câu trả lời của AI
        ai_msg = ChatMessage(room_id=room.id, role="assistant", content=json.dumps(result_json))
        db.add(ai_msg)
        db.commit()
        
        return jsonify({"widget": result_json})
    finally:
        db.close()

@api_bp.route("/rooms/<int:room_id>/recrawl", methods=["POST"])
def recrawl(room_id):
    """API 3: Bắt Spider cào lại 100 trang mới nhất"""
    db = SessionLocal()
    try:
        room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
        if not room:
            return jsonify({"error": "Không tìm thấy phòng chat"}), 404
            
        crawl = room.web_crawl
        crawl.status = "crawling"
        crawl.pages_crawled = 0
        
        # Xóa các chunk cũ
        for chunk in crawl.chunks:
            db.delete(chunk)
            
        db.commit()
        
        # Bắn luồng cào lại
        thread = threading.Thread(target=scrape_url, args=(crawl.url, crawl.id))
        thread.daemon = True
        thread.start()
        
        return jsonify({"message": "Đang tiến hành cào lại hệ thống mạng nhện!"})
    finally:
        db.close()
