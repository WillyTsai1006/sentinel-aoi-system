import requests
import time
import os
import random
from concurrent.futures import ThreadPoolExecutor
# 設定 API 位置
API_URL = "http://localhost:8000/api/v1/detect"
# 設定圖片來源 (請改成你電腦上的 NEU-DET valid 資料夾路徑)
IMAGE_FOLDER = "./datasets/NEU-DET/valid/images"
def send_frame(img_path):
    """發送單張圖片"""
    try:
        start_time = time.time()
        file_name = os.path.basename(img_path)
        with open(img_path, 'rb') as f:
            files = {'file': (file_name, f, 'image/jpeg')}
            # 模擬相機發送
            response = requests.post(API_URL, files=files)
        latency = time.time() - start_time
        print(f"📸 Sent: {file_name} | Status: {response.status_code} | Time: {latency:.3f}s")
        return response.json()
    except Exception as e:
        print(f"❌ Error sending {file_name}: {e}")

def run_simulation(fps=5):
    """
    模擬產線運作
    fps: 每秒發送幾張圖
    """
    images = [os.path.join(IMAGE_FOLDER, f) for f in os.listdir(IMAGE_FOLDER) if f.endswith(('.jpg', '.bmp'))]
    if not images:
        print("❌ 找不到圖片，請檢查路徑")
        return
    print(f"🚀 啟動相機模擬器 (Target FPS: {fps})... 按 Ctrl+C 停止")
    # 使用 ThreadPool 來並發發送，模擬高併發場景
    delay = 1.0 / fps
    with ThreadPoolExecutor(max_workers=4) as executor:
        while True:
            # 隨機挑一張圖模擬產線經過的產品
            target_img = random.choice(images)
            # 非同步發送請求 (不會卡住等回應)
            executor.submit(send_frame, target_img)
            # 控制發送頻率
            time.sleep(delay)

if __name__ == "__main__":
    # 你可以調整這裡的 FPS 來測試系統極限
    # 試試看 FPS=20，你的 Redis Queue 就會開始堆積，然後觸發 Drop Frame
    run_simulation(fps=2)