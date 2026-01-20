from sqlalchemy import Column, Integer, String, JSON, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# 定義資料庫連線 (從環境變數讀取)
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "secret_password")
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "aoi_db")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
# 定義 "Inspection" 資料表
class InspectionResult(Base):
    __tablename__ = "inspection_results"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, index=True)      # Celery 的 Task ID
    filename = Column(String)                 # 原始檔名
    storage_path = Column(String)             # MinIO 路徑
    inference_result = Column(JSON)           # YOLO 偵測到的座標與類別
    created_at = Column(DateTime, default=datetime.utcnow)
# 自動建表 (簡單起見，直接在這裡執行)
def init_db():
    Base.metadata.create_all(bind=engine)