from fastapi import FastAPI, UploadFile, File, HTTPException
from .services.storage import get_storage_client
from .config import settings
import uuid
from .tasks import detect_image_task  # 新增: 匯入任務函式
from celery.result import AsyncResult
from .celery_app import celery_app
from .models import SessionLocal, InspectionResult
import json
import time
from prometheus_fastapi_instrumentator import Instrumentator # 新增
# 新增 import init_db
from .models import init_db
# 新增 lifespan 處理啟動事件
@asynccontextmanager
async def lifespan(app: FastAPI):
    # [啟動時執行]
    try:
        # 嘗試連線資料庫並建立 Table
        print("Initializing database...")
        init_db()
        print("Database initialized successfully.")
    except Exception as e:
        # 如果是測試環境沒 DB，捕捉錯誤印出警告，不要讓 App 崩潰
        print(f"WARNING: Database initialization failed (Ignored for tests): {e}")
    yield  # 應用程式開始運作
    # [關閉時執行] (目前不需要做什麼)
    pass
# 在 FastAPI 初始化時加入 lifespan
app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
# 初始化 Prometheus 監控
# 這會自動建立一個 /metrics 接口，收集所有 API 的 Latency 和 Status Code
Instrumentator().instrument(app).expose(app)

@app.get("/")
def health_check():
    return {"status": "ok", "service": "Sentinel-AOI Backend"}

@app.post("/api/v1/detect")
async def upload_and_detect(file: UploadFile = File(...)):
    """
    模擬產線接口：
    1. 接收圖片
    2. 上傳至 MinIO
    3. (下一階段) 發送任務給 AI
    """
    # 1. 取得 Storage Client (延遲初始化)
    storage_client = get_storage_client()
    # 2. 檢查連線狀態 (如果是 None 代表 MinIO 連線失敗)
    if storage_client is None:
        raise HTTPException(status_code=503, detail="Storage service is unavailable")
    try:
        # 讀取檔案內容
        file_content = await file.read()
        # 產生唯一檔名 (避免檔名衝突) , 例如: 550e8400-e29b-41d4-a716-446655440000.jpg
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        # 上傳到 MinIO
        # 使用取得的 instance 呼叫方法
        storage_path = storage_client.upload_file(file_content, unique_filename, file.content_type)
        # 發送非同步任務到 Celery 
        # .delay() 會將任務丟進 Redis 就立刻回傳，不會卡住
        task = detect_image_task.delay(unique_filename, storage_path, time.time())
        return {
            "status": "received",
            "task_id": task.id,  # 回傳任務 ID 供前端查詢
            "filename": unique_filename,
            "message": "Image queued for processing"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# 查詢任務狀態與結果
@app.get("/api/v1/results/{task_id}")
def get_result(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    # 狀態 1: 處理中
    if not task_result.ready():
        return {"status": "processing"}
    # 狀態 2: 處理成功
    if task_result.successful():
        # 從資料庫撈取詳細資料 (比 Celery return 的更完整)
        db = SessionLocal()
        record = db.query(InspectionResult).filter(InspectionResult.task_id == task_id).first()
        db.close()
        if record:
            return {
                "status": "completed",
                "result": json.loads(record.inference_result) if isinstance(record.inference_result, str) else record.inference_result,
                "filename": record.filename
            }
        else:
            # Fallback: 如果 DB 還沒寫入完成，先回傳 Celery 的結果
            return {
                "status": "completed",
                "result": task_result.result.get("detections", [])
            }
    # 狀態 3: 失敗
    return {"status": "failed", "error": str(task_result.result)}
