import os
import json
from flask import Flask, request, jsonify
import google.auth
from googleapiclient.discovery import build
import gspread

# 匯入最新的 google-genai SDK
from google import genai
from google.genai import types

app = Flask(__name__)

# 1. 初始化 GCP 憑證與 ADC (在 Cloud Run 上會自動取得運行的 Service Account 憑證)
scopes = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/cloud-platform"
]
credentials, project_id = google.auth.default(scopes=scopes)

# 2. 初始化最新的 Google GenAI Client (連線至 Vertex AI global 端點)
client = genai.Client(
    vertexai=True,
    project=project_id,
    location="global"
)

# 從環境變數讀取 Master 試算表 ID
MASTER_SPREADSHEET_ID = os.environ.get("MASTER_SPREADSHEET_ID")

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "Petty Cash API is running!"}), 200

@app.route("/process-receipt", methods=["POST"])
def process_receipt():
    try:
        if not MASTER_SPREADSHEET_ID:
            return jsonify({"status": "error", "message": "Cloud Run 未設定 MASTER_SPREADSHEET_ID 環境變數。"}), 500

        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "Missing 'file' field in form data"}), 400
        
        file = request.files['file']
        image_bytes = file.read()
        
        if not image_bytes:
            return jsonify({"status": "error", "message": "Uploaded file is empty"}), 400

        # 取得上傳檔案的 Mime Type，若無則預設為 image/jpeg
        mime_type = file.mimetype if file.mimetype else "image/jpeg"

        # 3. 使用新版 types.Part.from_bytes 處理圖片資料
        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type=mime_type
        )

        prompt = """
        你是一位專精於視覺化帳單分析並統計當日流水帳的會計師。
        請精準識別此帳單中的所有明細，並輸出以下標準 JSON 格式：
        {
          "store_name": "店鋪名稱",
          "date": "DD-MM-YYYY",
          "receipt_ref": "發票或單號",
          "payment_method": "付款方式",
          "items": [
            {
              "item_name": "物品名稱",
              "quantity": 1,
              "unit_price": 0.0,
              "discount": 0.0,
              "amount": 0.0
            }
          ],
          "receipt_subtotal": 0.0
        }
        注意：請務必確保日期格式為 日-月-年 (例如: 10-08-2026)。
        """

        # 4. 呼叫 gemini-3-flash-preview 並使用 GenerateContentConfig 指定 JSON 輸出
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[image_part, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        # 解析 JSON
        data = json.loads(response.text)
        date_str = data["date"]

        # 連結 Google Sheets
        gc = gspread.authorize(credentials)
        
        # A. 直接開啟你預先分享好嘅 Master 試算表
        try:
            spreadsheet = gc.open_by_key(MASTER_SPREADSHEET_ID)
        except Exception as e:
            return jsonify({
                "status": "error", 
                "message": f"無法開啟 Master 試算表，請確保 MASTER_SPREADSHEET_ID 正確，且已將該試算表 Share 畀 Service Account。錯誤詳情: {str(e)}"
            }), 400

        # B. 尋找或建立「當日日期」嘅分頁 (Worksheet / Tab)
        try:
            # 試試看可唔可以開啟當日分頁
            sheet = spreadsheet.worksheet(date_str)
            is_new_sheet = False
        except gspread.exceptions.WorksheetNotFound:
            # 如果當日分頁唔存在，就新建一個分頁 (唔會觸發 Drive 建立檔案，所以 0GB 配額唔會報錯)
            sheet = spreadsheet.add_worksheet(title=date_str, rows=100, cols=10)
            is_new_sheet = True

        if is_new_sheet:
            # 新分頁初始化表頭
            sheet.append_row(["日期", "店舖/單號", "項目名稱", "數量", "單價 ($)", "折扣 ($)", "項目金額 ($)", "付款方式"])
            sheet.append_row(["", "", "", "", "", "當日流水帳 Subtotal", 0, ""])

        # C. 喺 Subtotal 之前插入新項目
        all_values = sheet.get_all_values()
        subtotal_row_idx = len(all_values)

        new_rows = []
        for item in data['items']:
            new_rows.append([
                data['date'],
                f"{data['store_name']}\n({data['receipt_ref']})",
                item['item_name'],
                item['quantity'],
                item['unit_price'],
                item['discount'],
                item['amount'],
                data['payment_method']
            ])

        sheet.insert_rows(new_rows, row=subtotal_row_idx)

        # 自動更新流水帳 Subtotal `=SUM(G2:G[N])`
        new_subtotal_row_idx = subtotal_row_idx + len(new_rows)
        sheet.update_cell(
            new_subtotal_row_idx, 
            7, 
            f"=SUM(G2:G{new_subtotal_row_idx - 1})"
        )

        return jsonify({"status": "success", "data": data}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))