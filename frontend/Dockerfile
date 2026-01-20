FROM python:3.10-slim

WORKDIR /app

# 安裝 streamlit 和 requests, pillow (畫圖用)
RUN pip install streamlit requests pillow

COPY . .

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]