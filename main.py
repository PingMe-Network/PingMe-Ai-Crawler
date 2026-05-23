from flask import Flask, send_from_directory
from dotenv import load_dotenv
from api.routes import api_bp

# Đảm bảo database được khởi tạo
from database.models import init_db
init_db()

# Khởi tạo ứng dụng Flask
app = Flask(__name__)

# Route để hiển thị giao diện Web (Frontend test)
@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')

# Đăng ký các Route từ thư mục api
app.register_blueprint(api_bp)

if __name__ == "__main__":
    load_dotenv()
    app.run(host="0.0.0.0", port=8000, debug=True)
