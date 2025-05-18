# app.py
from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import google.generativeai as genai

# === 1. 設定金鑰 ===
LINE_CHANNEL_ACCESS_TOKEN = 'iJyoIvaltzHmU8SraEy29I+7GBOTbuHKgBKCVzHX39MQvurbOBEciWd+pu0B2fmujrHW+tGW6HCUD198093OAOQFqH41r9kk9K3fz1x6HPZAIb9IKo/VqPF/b3i3bR2Euvpgc27unU7ISqCMspcdnAdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = '2bfcc68a3888040f95322ed391ed8213'
GEMINI_API_KEY = 'AIzaSyDzqsFXzMxHZ2ep8UOFE7-6abKtvOhQc7E'

# === 2. 初始化 ===
app = Flask(__name__)
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash-latest")

# === 3. 對話歷史紀錄 ===
history_log = []

# === 4. 預設首頁 ===
@app.route("/")
def home():
    return "LINE + Gemini bot is running."

# === 5. RESTful API ===
@app.route("/history", methods=['GET'])
def get_history():
    return jsonify(history_log)

@app.route("/history", methods=['DELETE'])
def delete_history():
    history_log.clear()
    return jsonify({"message": "歷史紀錄已清除"})

# === 6. webhook 處理 ===
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    except Exception as e:
        print("[Callback Error]", e)
        abort(500)
    return 'OK'

# === 7. Gemini 對話邏輯 ===
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        user_msg = event.message.text
        response = model.generate_content(user_msg)
        reply = response.text.strip() if hasattr(response, 'text') else "(無回應)"

        if not reply:
            reply = "（Gemini 沒有回應 😅）"

    except Exception as e:
        print("[Gemini Error]", e)
        reply = f"❌ 發生錯誤，請稍後再試\n[錯誤訊息] {e}"

    # 儲存對話紀錄
    history_log.append({"user": user_msg, "bot": reply})

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == '__main__':
    app.run(port=5000)
