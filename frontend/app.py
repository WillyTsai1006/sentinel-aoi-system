import streamlit as st
import requests
import time
from PIL import Image, ImageDraw
import io

# 設定後端 API URL (Docker 內部通訊用 service name，但在瀏覽器端要用 localhost)
# 注意: Streamlit 是在 Container 裡跑，Request 是由 Container 發出的，所以要用 http://backend:8000
API_URL = "http://backend:8000/api/v1"
st.set_page_config(page_title="Sentinel AOI Dashboard", layout="wide")
st.title("🏭 Sentinel-AOI 工業瑕疵檢測平台")
st.markdown("---")
# 側邊欄：系統狀態
with st.sidebar:
    st.header("系統狀態")
    st.success("✅ API Gateway: Online")
    st.success("✅ AI Worker: Online")
    st.info("📦 Database: PostgreSQL")
    st.warning("🤖 Model: YOLOv8-Custom")
# 主畫面分兩欄
col1, col2 = st.columns(2)
with col1:
    st.subheader("1. 產線影像輸入")
    uploaded_file = st.file_uploader("上傳檢測圖片", type=['jpg', 'png', 'jpeg'])
if uploaded_file is not None:
    # 顯示原圖
    image = Image.open(uploaded_file)
    with col1:
        st.image(image, caption="原始影像", width=400)
    # 按鈕觸發檢測
    if st.button("🚀 開始檢測 (Start Inspection)"):
        with st.spinner('正在上傳並排入隊列...'):
            # 1. 發送圖片給 API
            try:
                # 需將指標歸零重新讀取
                uploaded_file.seek(0)
                files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
                response = requests.post(f"{API_URL}/detect", files=files)
                if response.status_code == 200:
                    task_data = response.json()
                    task_id = task_data['task_id']
                    st.toast(f"任務已接收! ID: {task_id}", icon="✅")
                else:
                    st.error(f"上傳失敗: {response.text}")
                    st.stop()
            except Exception as e:
                st.error(f"連線錯誤: {e}")
                st.stop()
        # 2. 輪詢 (Polling) 結果
        with col2:
            st.subheader("2. AI 檢測結果")
            status_placeholder = st.empty()
            # 簡單的 Polling 機制
            for _ in range(20): # 最多等 20 次
                status_res = requests.get(f"{API_URL}/results/{task_id}")
                status_data = status_res.json()
                if status_data["status"] == "completed":
                    status_placeholder.success("✨ 檢測完成!")
                    # 3. 繪製 Bounding Box
                    draw = ImageDraw.Draw(image)
                    detections = status_data["result"]                    
                    # 用不同顏色標示
                    # NEU-DET 常見瑕疵
                    count = len(detections)
                    st.metric("瑕疵數量", f"{count} 個", delta=f"{count} Defects", delta_color="inverse")
                    for det in detections:
                        bbox = det["bbox"] # [x1, y1, x2, y2]
                        conf = det["confidence"]
                        label = det["label"]                       
                        # 畫紅框
                        draw.rectangle(bbox, outline="red", width=3)
                        # 畫標籤背景
                        draw.rectangle([bbox[0], bbox[1]-20, bbox[0]+100, bbox[1]], fill="red")
                        # 寫字
                        draw.text((bbox[0]+5, bbox[1]-15), f"{label} {conf:.2f}", fill="white")                    
                    st.image(image, caption="AI 標註結果", width=500)
                    st.json(detections) # 顯示原始數據方便 Debug
                    break
                elif status_data["status"] == "failed":
                    status_placeholder.error("檢測失敗")
                    break
                else:
                    status_placeholder.info("⏳ AI 正在思考中... (Processing)")
                    time.sleep(1) # 等1秒再問一次