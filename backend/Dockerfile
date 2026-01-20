# 使用輕量級的 Python 映像檔
FROM python:3.10-slim

# 設定工作目錄
WORKDIR /app

# 更新 apt-get 並安裝必要的系統依賴
# 對於 Debian 12 (trixie)，使用新的套件名稱
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libglx0 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 先升級 pip 到最新版本
RUN pip install --upgrade pip

# 先複製 requirements 以利用 Docker Cache 機制加速建置
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製所有程式碼
COPY . .

# 啟動 FastAPI
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
