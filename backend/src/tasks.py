from celery import Task
from .celery_app import celery_app
from .services.storage import get_storage_client
from .models import SessionLocal, InspectionResult, init_db
from ultralytics import YOLO
import cv2
import numpy as np
import json
import os
import time
from datetime import datetime, timedelta
# 1. 添加 PyTorch 2.6 兼容性處理
import torch.serialization
from ultralytics.nn.tasks import DetectionModel
# 添加安全全局變量
torch.serialization.add_safe_globals([DetectionModel])
# 初始化 DB (確保 Table 存在)
init_db()
MODEL_PATH = "weights/best.pt"  # 相對路徑
# 檢查模型是否存在，如果不存在就退回通用模型 (防呆)
if not os.path.exists(MODEL_PATH):
    print(f"⚠️ 找不到 {MODEL_PATH}，使用預設 yolov8n.pt")
    model = YOLO('yolov8n.pt')
else:
    print(f"🔥 載入客製化 AOI 模型: {MODEL_PATH}")
    model = YOLO(MODEL_PATH)
# 預熱模型
print("🔥 預熱 YOLO 模型...")
try:
    dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
    _ = model(dummy_img, conf=0.25, verbose=False, imgsz=640)
    print("✅ 模型預熱完成")
except Exception as e:
    print(f"⚠️ 模型預熱失敗: {e}")

@celery_app.task(name="detect_task", bind=True, time_limit=60)
def detect_image_task(self, file_name: str, storage_path: str, created_at_ts: float):
    storage_client = get_storage_client()
    if not storage_client:
        # 處理重試或錯誤
        raise Exception("MinIO connection failed")
    # 1. 背壓檢查 (Backpressure Check)
    # 如果這張圖已經在 Queue 裡排隊超過 5 秒，就算算出來也沒意義了，直接丟棄
    now = datetime.utcnow().timestamp()
    latency = now - created_at_ts
    if latency > 5.0: # 容忍延遲閾值：5秒
        print(f"⚠️ [Drop Frame] 圖片逾時 {latency:.2f}s，直接丟棄: {file_name}")
        return {"status": "dropped", "reason": "timeout"}
    print(f"🚀 [Worker] 開始處理: {file_name} (排隊延遲: {latency:.2f}s)")
    print(f"📋 參數 - file_name: {file_name}, storage_path: {storage_path}")
    # 1. 從 MinIO 取得圖片
    try:
        # 簡單解析 bucket 和 object
        if "/" not in storage_path:
            return {"status": "error", "reason": f"無效的 storage_path: {storage_path}"}
        bucket_name, object_name = storage_path.split("/", 1)
        print(f"📦 解析結果: bucket={bucket_name}, object={object_name}")
        # 測試連接
        try:
            exists = storage_client.bucket_exists(bucket_name)
            print(f"🔍 Bucket 存在: {exists}")
            if not exists:
                return {"status": "error", "reason": f"Bucket 不存在: {bucket_name}"}
        except Exception as e:
            print(f"❌ Bucket 檢查失敗: {e}")
            return {"status": "error", "reason": f"Bucket 檢查失敗: {str(e)}"}
        # 下載對象
        print(f"⬇️ 開始下載...")
        response = storage_client.get_object(bucket_name, object_name)
        print(f"✅ 獲取響應成功")
        # 讀取數據
        data = response.read()
        print(f"📊 讀取數據大小: {len(data)} 字節")
        # 轉換
        file_bytes = np.frombuffer(data, dtype=np.uint8)
        print(f"🔄 轉換為 numpy array")
        # 關閉響應
        response.close()
        response.release_conn()
        print(f"🔒 響應已關閉")
        # 解碼圖片
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is None:
            print(f"❌ 圖片解碼失敗")
            return {"status": "error", "reason": "圖片解碼失敗"}
        print(f"🖼️ 圖片解碼成功: {img.shape}")
    except Exception as e:
        print(f"❌ MinIO 操作失敗: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "reason": str(e)}
    # 3. YOLO 推理
    print(f"🤖 開始 YOLO 推理...")
    try:
        # 優化推理參數
        results = model(
            img, 
            conf=0.25,
            imgsz=640,  # 固定輸入尺寸
            device='cpu',  # 明確使用 CPU
            verbose=False,  # 關閉詳細輸出
            max_det=10,  # 最多檢測 10 個物體
            half=False  # CPU 不支持半精度
        )
        print(f"✅ YOLO 推理完成，耗時: {results[0].speed}")  # 顯示推理時間
        detections = []
        for r in results:
            for box in r.boxes:
                xyxy = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                label = model.names[cls]
                detections.append({
                    "label": label,
                    "confidence": conf,
                    "bbox": xyxy
                })
        print(f"🔍 發現 {len(detections)} 個物件")
    except Exception as e:
        print(f"❌ YOLO 推理失敗: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "reason": f"YOLO 推理失敗: {str(e)}"}
    # 4. 寫入資料庫
    print(f"💾 寫入資料庫...")
    db = SessionLocal()
    try:
        record = InspectionResult(
            task_id=self.request.id,
            filename=file_name,
            storage_path=storage_path,
            inference_result=json.dumps(detections, ensure_ascii=False)
        )
        db.add(record)
        db.commit()
        print(f"✅ 資料已寫入 DB, ID: {record.id}")
    except Exception as e:
        print(f"❌ DB 寫入失敗: {e}")
        db.rollback()
    finally:
        db.close()
    print(f"🎉 任務完成")
    return {"status": "success", "detections": detections}
