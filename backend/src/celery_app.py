from celery import Celery
import os

# 讀取環境變數 (與 config.py 邏輯類似，但這裡簡單處理以避免循環引用)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# 初始化 Celery 實例
celery_app = Celery(
    "sentinel_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# 設定 Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Taipei",
    enable_utc=True,
)