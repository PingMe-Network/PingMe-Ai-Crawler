FROM mcr.microsoft.com/playwright/python:v1.43.0-jammy

# Thiết lập thư mục làm việc
WORKDIR /app

# Copy file requirements và cài đặt thư viện
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Đảm bảo Playwright đã cài đặt xong trình duyệt Chromium
RUN python -m playwright install chromium

# Copy toàn bộ mã nguồn vào Container
COPY . .

# Mở cổng 8000
EXPOSE 8000

# Chạy server
CMD ["python", "main.py"]
