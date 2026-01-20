from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.main import app

client = TestClient(app)
# --- 修改 Mock 目標 ---
@patch("src.main.get_storage_client")  # Mock 獲取 Client 的函數
@patch("src.main.celery_app.send_task") # 注意：這裡根據你的實作，可能是 celery_app.send_task 或 task.delay
def test_upload_and_detect(mock_send_task, mock_get_storage_client):
    # 1. 設定 Mock Storage 行為
    mock_storage_instance = MagicMock()
    mock_storage_instance.upload_file.return_value = "bucket/test-image.jpg"
    # 讓 get_storage_client 回傳我們做好的 mock instance
    mock_get_storage_client.return_value = mock_storage_instance
    # 2. 設定 Mock Celery 行為
    mock_task_obj = MagicMock()
    mock_task_obj.id = "test-task-id-123"
    mock_send_task.return_value = mock_task_obj
    # 3. 執行測試
    files = {"file": ("test.jpg", b"fake image content", "image/jpeg")}
    response = client.post("/api/v1/detect", files=files)
    # 4. 驗證結果
    assert response.status_code == 200
    assert response.json() == {"task_id": "test-task-id-123", "status": "processing"}
    # 驗證是否正確呼叫
    mock_get_storage_client.assert_called() # 確認有呼叫 getter
    mock_storage_instance.upload_file.assert_called_once()