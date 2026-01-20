from minio import Minio
from minio.error import S3Error
import io
from ..config import settings

class StorageService:
    def __init__(self):
        # 初始化 MinIO 客戶端
        # 注意: secure=False 代表不使用 HTTPS (因為我們在內網/本機跑)
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_USER,
            secret_key=settings.MINIO_PASSWORD,
            secure=False
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """確認 Bucket 存在，不存在就建立 (企業級容錯)"""
        try:
            if not self.client.bucket_exists(settings.MINIO_BUCKET_NAME):
                self.client.make_bucket(settings.MINIO_BUCKET_NAME)
                print(f"Bucket '{settings.MINIO_BUCKET_NAME}' created.")
        except S3Error as e:
            print(f"MinIO Error: {e}")

    def upload_file(self, file_data: bytes, file_name: str, content_type: str) -> str:
        """上傳檔案並回傳檔案路徑"""
        try:
            # 將 bytes 轉為 file-like object
            data_stream = io.BytesIO(file_data)
            self.client.put_object(
                bucket_name=settings.MINIO_BUCKET_NAME,
                object_name=file_name,
                data=data_stream,
                length=len(file_data),
                content_type=content_type
            )
            return f"{settings.MINIO_BUCKET_NAME}/{file_name}"
        except S3Error as e:
            print(f"Upload Failed: {e}")
            raise e

# 定義一個全域變數來存放單例，但初始為 None
_storage_client_instance = None

def get_storage_client():
    """
    延遲初始化 StorageClient。
    只有在第一次被呼叫時才會嘗試連線 MinIO。
    """
    global _storage_client_instance
    if _storage_client_instance is None:
        try:
            _storage_client_instance = StorageService()
        except Exception as e:
            # 這裡捕捉錯誤是為了讓測試在沒有 MinIO 的環境下也能 import 成功
            # 但在實際運作中，呼叫端會拿到 None，需要處理
            print(f"Warning: Could not initialize MinIO client: {e}")
            return None
    return _storage_client_instance