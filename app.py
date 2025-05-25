from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    ImageMessage, VideoMessage, LocationMessage, StickerMessage,
    ImageSendMessage, VideoSendMessage
)
import google.generativeai as genai
import requests
import re

# === 1. 設定金鑰 ===
LINE_CHANNEL_ACCESS_TOKEN = 'iJyoIvaltzHmU8SraEy29I+7GBOTbuHKgBKCVzHX39MQvurbOBEciWd+pu0B2fmujrHW+tGW6HCUD198093OAOQFqH41r9kk9K3fz1x6HPZAIb9IKo/VqPF/b3i3bR2Euvpgc27unU7ISqCMspcdnAdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = '2bfcc68a3888040f95322ed391ed8213'
GEMINI_API_KEY = 'AIzaSyDzqsFXzMxHZ2ep8UOFE7-6abKtvOhQc7E'
TRANSLATE_API_URL = 'https://api.mymemory.translated.net/get'

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

# === 翻譯輔助函式 ===
def translate_text(text):
    # 偵測語言是英文或中文
    if re.search(r'[\u4e00-\u9fff]', text):
        # 中文翻英文
        langpair = 'zh-TW|en'
    else:
        # 英文翻中文
        langpair = 'en|zh-TW'

    params = {
        'q': text,
        'langpair': langpair
    }
    try:
        res = requests.get(TRANSLATE_API_URL, params=params)
        return res.json()['responseData']['translatedText']
    except Exception as e:
        print("[Translate Error]", e)
        return "(翻譯失敗)"

# === 7. 處理文字訊息 ===
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    try:
        user_msg = event.message.text
        messages = []
        for record in history_log[-10:]:
            messages.append(f"使用者：{record['user']}")
            messages.append(f"機器人：{record['bot']}")
        messages.append(f"使用者：{user_msg}")

        response = model.generate_content("\n".join(messages))
        reply = response.text.strip() if hasattr(response, 'text') else "(無回應)"
        translation = translate_text(user_msg)

        full_reply = f"🤖 Gemini 回覆：\n{reply}\n\n🌐 你的訊息翻譯：\n{translation}"

        if not reply:
            full_reply = "（Gemini 沒有回應 😅）"
    except Exception as e:
        print("[Gemini Error]", e)
        full_reply = f"❌ 發生錯誤，請稍後再試\n[錯誤訊息] {e}"

    history_log.append({"user": user_msg, "bot": reply})

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=full_reply)
    )

# === 8. 處理圖片訊息 ===
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    image_url = "https://your-server.com/static/default.jpg"
    line_bot_api.reply_message(
        event.reply_token,
        ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)
    )

# === 9. 處理影片訊息 ===
@handler.add(MessageEvent, message=VideoMessage)
def handle_video(event):
    video_url = "https://your-server.com/static/sample.mp4"
    line_bot_api.reply_message(
        event.reply_token,
        VideoSendMessage(original_content_url=video_url, preview_image_url=video_url)
    )

# === 10. 處理位置訊息 ===
@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    address = event.message.address or ""
    reply = f"你傳送的位置是：{event.message.title}\n地址：{address}"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

# === 11. 處理貼圖訊息 ===
@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker(event):
    reply = "你傳送了一個貼圖 😄"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == '__main__':
    app.run(port=5000)
