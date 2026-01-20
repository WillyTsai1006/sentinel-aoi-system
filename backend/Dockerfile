# ==========================================
# Stage 1: Builder (負責編譯與安裝依賴)
# ==========================================
# 修改點：將 'as' 改為大寫 'AS'
FROM python:3.10-slim AS builder

# 設定工作目錄
WORKDIR /app

# 1. 安裝系統編譯工具
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. 建立 Python 虛擬環境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 3. 安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ==========================================
# Stage 2: Runner (最終執行的精簡環境)
# ==========================================
# 修改點：將 'as' 改為大寫 'AS'
FROM python:3.10-slim AS runner

WORKDIR /app

# 1. 安裝 "執行時期" 僅需的系統函式庫
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# 2. 從 Builder 階段複製整個虛擬環境
COPY --from=builder /opt/venv /opt/venv

# 3. 設定環境變數
ENV PATH="/opt/venv/bin:$PATH"

# 4. 複製專案程式碼
COPY . .

# 5. 設定啟動指令
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]