from fastapi.testclient import TestClient
from src.main import app
from unittest.mock import patch
import io

client = TestClient(app)

def test_health_check():
    """測試根目錄是否回應 200"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Sentinel-AOI Backend"}
# 我們需要 Mock 掉 Celery 和 MinIO，因為測試環境可能沒有 Docker
@patch("src.main.detect_image_task.delay")
@patch("src.main.storage_client.upload_file")
def test_upload_image(mock_upload, mock_celery_delay):
    """測試圖片上傳接口"""
    # 1. 模擬依賴服務的行為
    mock_upload.return_value = "raw-images/test.jpg"
    mock_celery_delay.return_value.id = "test-task-id-123"
    # 2. 準備一張假圖片
    file_content = b"fake image content"
    files = {"file": ("test.jpg", io.BytesIO(file_content), "image/jpeg")}
    # 3. 發送請求
    response = client.post("/api/v1/detect", files=files)
    # 4. 驗證結果 (Assert)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert data["task_id"] == "test-task-id-123"
    # 確保真的有呼叫上傳和發送任務
    mock_upload.assert_called_once()
    mock_celery_delay.assert_called_once()