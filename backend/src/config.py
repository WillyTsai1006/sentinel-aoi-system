from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 定義專案名稱
    PROJECT_NAME: str = "Sentinel-AOI"
    # MinIO 設定 (會自動讀取環境變數 MINIO_USER 等)
    MINIO_ENDPOINT: str
    MINIO_USER: str
    MINIO_PASSWORD: str
    MINIO_BUCKET_NAME: str = "raw-images"
    class Config:
        # 指定 .env 檔案位置 (相對於執行目錄)
        env_file = ".env"
# 實例化設定物件
settings = Settings()