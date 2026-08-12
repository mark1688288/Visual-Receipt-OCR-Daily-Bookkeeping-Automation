# 使用輕量級的 Python 映像檔
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 複製並安裝依賴項目
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製所有程式碼到容器中
COPY . .

# 設定 Port 8080 (Cloud Run 預設 Port)
ENV PORT=8080

# 使用 gunicorn 啟動 Flask
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app