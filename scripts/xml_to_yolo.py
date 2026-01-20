# use this script to unzip archive.zip in Google Colab
# 1. 強制修復路徑問題 (解決 shell-init 錯誤)
import os
try:
    os.chdir('/content')
    print("✅ 已將工作目錄重置為: /content")
except Exception as e:
    print(f"⚠️ 無法重置目錄: {e}")
# 2. 安裝 YOLO (如果你還沒裝)
# !pip install ultralytics
from ultralytics import YOLO
# 3. 除錯：列出當前目錄下的檔案 (確認 archive.zip 真的在)
print("\n📂 當前目錄下的檔案:")
# !ls -lh
# 4. 執行解壓縮
zip_file = 'archive.zip'
dataset_dir = './datasets'
if os.path.exists(zip_file):
    print(f"\nFound {zip_file}. Unzipping to {dataset_dir}...")
    # -o 代表 overwrite (覆蓋不詢問), -q 代表安靜模式
    # !unzip -o -q {zip_file} -d {dataset_dir}
    print("✅ Unzipping complete.")
    # 檢查解壓縮後的結構
    if os.path.exists(dataset_dir):
        print(f"解壓縮後的資料夾內容 ({dataset_dir}):")
        print(os.listdir(dataset_dir))
else:
    print(f"\n❌ Error: {zip_file} not found in /content/.")
    print("請確認：")
    print("1. 你是否已經將 archive.zip 拖曳到左側的檔案欄？")
    print("2. 上傳進度條是否已經跑完？(Colab 上傳大檔有時會慢)")

# change xml annotations to yolo format for NEU-DET dataset 
import os
import glob
import xml.etree.ElementTree as ET
import shutil
import random
from tqdm import tqdm
# 設定區 
# 1. 定義 NEU-DET 的類別名稱 (必須依照順序，這很重要)
CLASSES = ['crazing', 'inclusion', 'patches', 'pitted_surface', 'rolled-in_scale', 'scratches']
# 2. 原始資料的路徑 (請修改為你解壓縮後的根目錄)
# 假設你解壓縮在 /content/datasets/neu_det，程式會自動遞迴搜尋裡面的 XML 和圖片
SOURCE_ROOT = '/content/datasets/NEU-DET'
# 3. 輸出目標路徑 (我們會把轉換好的資料放在這裡)
OUTPUT_ROOT = '/content/datasets/neu_det_yolo'
# 4. 切分比例 (Train : Valid)
TRAIN_RATIO = 0.8
def convert_box(size, box):
    """ 將 XML 的 (xmin, xmax, ymin, ymax) 轉換為 YOLO 的 (x, y, w, h) """
    dw = 1. / size[0]
    dh = 1. / size[1]
    x = (box[0] + box[1]) / 2.0
    y = (box[2] + box[3]) / 2.0
    w = box[1] - box[0]
    h = box[3] - box[2]
    return (x * dw, y * dh, w * dw, h * dh)
def convert_annotation(xml_file, output_path):
    """ 讀取一個 XML 並轉存為 TXT """
    tree = ET.parse(xml_file)
    root = tree.getroot()
    size = root.find('size')
    w = int(size.find('width').text)
    h = int(size.find('height').text)
    # 某些資料集的 size 是 0 (壞資料)，防呆處理
    if w == 0 or h == 0:
        return False
    out_file = open(output_path, 'w')
    has_obj = False
    for obj in root.iter('object'):
        difficult = obj.find('difficult').text
        cls = obj.find('name').text
        if cls not in CLASSES or int(difficult) == 1:
            continue
        cls_id = CLASSES.index(cls)
        xmlbox = obj.find('bndbox')
        b = (float(xmlbox.find('xmin').text), float(xmlbox.find('xmax').text), float(xmlbox.find('ymin').text), float(xmlbox.find('ymax').text))
        bb = convert_box((w, h), b)
        out_file.write(f"{cls_id} {bb[0]:.6f} {bb[1]:.6f} {bb[2]:.6f} {bb[3]:.6f}\n")
        has_obj = True
    out_file.close()
    return has_obj
# 主程式邏輯
print("🚀 開始 ETL 資料轉換流程...")
# 建立輸出資料夾結構
for split in ['train', 'valid']:
    os.makedirs(os.path.join(OUTPUT_ROOT, split, 'images'), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_ROOT, split, 'labels'), exist_ok=True)
# 搜尋所有 XML 檔案
xml_files = glob.glob(os.path.join(SOURCE_ROOT, '**/*.xml'), recursive=True)
print(f"🔍 找到 {len(xml_files)} 個 XML 標註檔")
# 隨機打亂
random.shuffle(xml_files)
# 切分資料
split_index = int(len(xml_files) * TRAIN_RATIO)
train_files = xml_files[:split_index]
valid_files = xml_files[split_index:]
print(f"📊 訓練集: {len(train_files)} 張, 驗證集: {len(valid_files)} 張")
def process_files(files_list, split_name):
    for xml_path in tqdm(files_list, desc=f"Processing {split_name}"):
        # 1. 找出對應的圖片路徑
        # NEU-DET 的圖片通常跟 xml 同名，只是副檔名是 .jpg 或 .BMP
        img_path_jpg = xml_path.replace('.xml', '.jpg')
        img_path_bmp = xml_path.replace('.xml', '.BMP') # 有些資料集是 BMP
        img_path_jpeg = xml_path.replace('.xml', '.jpeg')
        # 檢查哪個圖片存在
        if os.path.exists(img_path_jpg):
            src_img = img_path_jpg
            ext = '.jpg'
        elif os.path.exists(img_path_bmp):
            src_img = img_path_bmp
            ext = '.bmp'
        elif os.path.exists(img_path_jpeg):
            src_img = img_path_jpeg
            ext = '.jpeg'
        else:
            # 如果 xml 和圖片分開在不同資料夾 (例如 XML在 annotations, 圖片在 images)
            # 這裡做一個簡單的路徑替換嘗試
            base_name = os.path.basename(xml_path).replace('.xml', '')
            # 嘗試搜尋圖片
            possible_imgs = glob.glob(os.path.join(SOURCE_ROOT, '**', f"{base_name}.*"), recursive=True)
            # 過濾掉 xml 本身
            possible_imgs = [p for p in possible_imgs if not p.endswith('.xml')]
            if len(possible_imgs) > 0:
                src_img = possible_imgs[0]
                ext = os.path.splitext(src_img)[1]
            else:
                print(f"⚠️ 找不到圖片: {xml_path}")
                continue
        # 2. 定義輸出路徑
        file_name = os.path.basename(xml_path).replace('.xml', '')
        dst_img_path = os.path.join(OUTPUT_ROOT, split_name, 'images', f"{file_name}{ext}")
        dst_txt_path = os.path.join(OUTPUT_ROOT, split_name, 'labels', f"{file_name}.txt")
        # 3. 轉換 XML -> TXT
        if convert_annotation(xml_path, dst_txt_path):
            # 4. 只有當標註成功轉換，才複製圖片
            shutil.copy(src_img, dst_img_path)
process_files(train_files, 'train')
process_files(valid_files, 'valid')
print(f"\n✅ 轉換完成！新資料集位於: {OUTPUT_ROOT}")

# 產生 data.yaml 檔案供 YOLO 訓練使用
import yaml
yaml_content = {
    'path': '/content/datasets/neu_det_yolo', # 指向剛剛轉換好的新目錄
    'train': 'train/images',
    'val': 'valid/images',
    'names': {
        0: 'crazing',
        1: 'inclusion',
        2: 'patches',
        3: 'pitted_surface',
        4: 'rolled-in_scale',
        5: 'scratches'
    }
}
with open('/content/datasets/neu_det_yolo/data.yaml', 'w') as f:
    yaml.dump(yaml_content, f)
print("✅ data.yaml 設定完成")

# train yolo model on neu_det dataset
from ultralytics import YOLO
# 載入 Medium 模型
model = YOLO('yolov8m.pt')
print("🚀 開始正式訓練...")
results = model.train(
    data='/content/datasets/neu_det_yolo/data.yaml', # 使用新生成的 yaml
    epochs=50,
    imgsz=640,
    batch=16,
    patience=10,
    name='sentinel_aoi_final',
    augment=True
)