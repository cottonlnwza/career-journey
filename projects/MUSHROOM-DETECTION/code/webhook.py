import time
import requests
from flask import Flask, request
from pymongo import MongoClient
from datetime import datetime, timedelta
from dateutil.parser import parse
import threading
import pytz

LINE_ACCESS_TOKEN = "oArvAFMbbzxZc/RqU37b1Zyz3hmkeaWqSxXJAN7m7tZouyxJ3RSrVDa8ot4pazJpZ+Rme2fbpvzU9PcXc9FLZPikeThLUqkOWqPD5bIuQyrKMPLCwp5w6VbNK6k/XfPSGcGz9iXcRODQJ1UQNDvotgdB04t89/1O/w1cDnyilFU="
MONGO_URI = "mongodb+srv://chatanutupth:Mos-111299@cpeproject.nsc4gfn.mongodb.net/?retryWrites=true&w=majority&appName=CPEproject"
DB_NAME = "mushroom_db"
COLLECTION_NAME = "mushroom_data"

app = Flask(__name__)
client = MongoClient(MONGO_URI)
collection = client[DB_NAME][COLLECTION_NAME]

QUICK_REPLY_ITEMS = [
    {"type": "action", "action": {"type": "message", "label": "สถานะเห็ด", "text": "สถานะเห็ด"}},
    {"type": "action", "action": {"type": "message", "label": "อุณหภูมิ", "text": "อุณหภูมิ"}},
    {"type": "action", "action": {"type": "message", "label": "ความชื้น", "text": "ความชื้น"}},
    {"type": "action", "action": {"type": "message", "label": "ช่วยเหลือ", "text": "ช่วยเหลือ"}},
]

thai_tz = pytz.timezone("Asia/Bangkok")

def send_line_reply(reply_token, text):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    data = {
        "replyToken": reply_token,
        "messages": [{
            "type": "text",
            "text": text,
            "quickReply": {"items": QUICK_REPLY_ITEMS}
        }]
    }
    requests.post(url, json=data, headers=headers)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    for event in data.get("events", []):
        if event.get("type") == "message":
            user_text = event["message"]["text"].strip().lower()
            reply_token = event["replyToken"]

            if user_text == "สถานะเห็ด":
                handle_status(reply_token)
            elif user_text in ["อุณหภูมิ", "ความชื้น"]:
                handle_latest_env(reply_token, user_text)
            elif user_text in ["อุณหภูมิย้อนหลัง", "ความชื้นย้อนหลัง"]:
                handle_env_history(reply_token, user_text)
            elif user_text == "ช่วยเหลือ":
                send_line_reply(reply_token, "☎️ ติดต่อสอบถามได้ที่: 0948741544")
            else:
                send_line_reply(reply_token, (
                    "คำสั่งที่สามารถใช้ได้:\n"
                    "- สถานะเห็ด\n"
                    "- อุณหภูมิ\n"
                    "- ความชื้น\n"
                    "- ช่วยเหลือ"
                ))
    return "OK", 200

def handle_status(reply_token):
    timestamps = collection.distinct("timestamp")
    if len(timestamps) < 2:
        send_line_reply(reply_token, "❌ ไม่มีข้อมูลเห็ดเพียงพอ")
        return

    timestamps_dt = sorted([parse(ts).astimezone(thai_tz) for ts in timestamps], reverse=True)
    target_ts = timestamps_dt[1]
    start_time = target_ts - timedelta(milliseconds=100)
    end_time = target_ts + timedelta(milliseconds=100)

    latest_docs = list(collection.find({
        "timestamp": {"$gte": start_time.isoformat(), "$lte": end_time.isoformat()}
    }))

    if not latest_docs:
        send_line_reply(reply_token, "❌ ไม่พบข้อมูลเห็ดในช่วงเวลาที่กำหนด")
        return

    mature_count = sum(1 for doc in latest_docs if doc.get("maturity_status", "").lower() == "mature")
    immature_count = len(latest_docs) - mature_count
    total = mature_count + immature_count

    if total == 0:
        reply_text = "❌ ไม่พบข้อมูลสถานะเห็ด"
    elif mature_count == total:
        reply_text = f"🍄 พร้อมเก็บทุกดอก\n⏰ เวลา: {target_ts.strftime('%Y-%m-%d %H:%M:%S')}"
    else:
        reply_text = (
            f"🍄 พร้อมเก็บ: {mature_count} ดอก\n"
            f"⏳ ยังไม่พร้อม: {immature_count} ดอก\n"
            f"⏰ เวลา: {target_ts.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    send_line_reply(reply_token, reply_text)

def handle_latest_env(reply_token, user_text):
    latest_doc = collection.find_one(sort=[("timestamp", -1)])
    if not latest_doc:
        send_line_reply(reply_token, "❌ ไม่มีข้อมูลล่าสุด")
        return

    ts_str = latest_doc["timestamp"]
    ts = parse(ts_str).astimezone(thai_tz)
    docs = list(collection.find({"timestamp": ts_str}))
    if not docs:
        send_line_reply(reply_token, "❌ ไม่มีข้อมูลล่าสุด")
        return

    avg_temp = sum(float(doc.get("temperature_c", 0)) for doc in docs) / len(docs)
    avg_humidity = sum(float(doc.get("humidity_percent", 0)) for doc in docs) / len(docs)

    if user_text == "อุณหภูมิ":
        reply_text = f"🌡️ อุณหภูมิเฉลี่ย ({ts.strftime('%Y-%m-%d %H:%M:%S')}): {avg_temp:.2f}°C"
    else:
        reply_text = f"💦 ความชื้นเฉลี่ย ({ts.strftime('%Y-%m-%d %H:%M:%S')}): {avg_humidity:.2f}%"

    send_line_reply(reply_token, reply_text)

def handle_env_history(reply_token, user_text):
    now = datetime.now(thai_tz)
    three_days_ago = now - timedelta(days=3)

    docs = list(collection.find({
        "timestamp": {"$gte": three_days_ago.isoformat(), "$lte": now.isoformat()}
    }))
    if not docs:
        send_line_reply(reply_token, f"❌ ไม่มีข้อมูล{user_text}ย้อนหลัง 3 วัน")
        return

    if user_text == "อุณหภูมิย้อนหลัง":
        values = [float(doc.get("temperature_c", 0)) for doc in docs]
        label = "อุณหภูมิ (°C)"
    else:
        values = [float(doc.get("humidity_percent", 0)) for doc in docs]
        label = "ความชื้น (%)"

    avg_val = sum(values) / len(values)
    max_val = max(values)
    min_val = min(values)

    reply_text = (
        f"📊 {label}ย้อนหลัง 3 วัน\n"
        f"เฉลี่ย: {avg_val:.2f}\n"
        f"สูงสุด: {max_val:.2f}\n"
        f"ต่ำสุด: {min_val:.2f}"
    )
    send_line_reply(reply_token, reply_text)

TEMP_HIGH_THRESHOLD = 35.0
TEMP_LOW_THRESHOLD = 15.0
HUMIDITY_HIGH_THRESHOLD = 80.0
HUMIDITY_LOW_THRESHOLD = 50.0
ALERT_INTERVAL = 600

last_alert_time = datetime.min.replace(tzinfo=thai_tz)
alerted_status = {
    "temp_high": False,
    "temp_low": False,
    "humidity_high": False,
    "humidity_low": False
}

def send_line_broadcast(text):
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    payload = {
        "messages": [{"type": "text", "text": text}]
    }
    requests.post(url, headers=headers, json=payload)

def check_environment():
    global last_alert_time, alerted_status
    MAX_DATA_AGE_MINUTES = 5

    while True:
        try:
            doc = collection.find_one(sort=[("timestamp", -1)])
            if not doc:
                print("❌ No data in DB")
                time.sleep(10)
                continue

            ts = parse(doc["timestamp"]).astimezone(thai_tz)
            now = datetime.now(thai_tz)

            print(f"Now: {now}, DB timestamp: {ts}")

            if (now - ts).total_seconds() > MAX_DATA_AGE_MINUTES * 60:
                print(f"ℹ️ ข้อมูลเก่าเกินไป ข้ามการแจ้งเตือน: now={now}, ts={ts}")
                time.sleep(10)
                continue

            temp = float(doc.get("temperature_c", 0))
            humidity = float(doc.get("humidity_percent", 0))

            print(f"Temp: {temp}, Humidity: {humidity}")
            print("Alert status:", alerted_status)

            alerts = []

            if temp > TEMP_HIGH_THRESHOLD:
                if not alerted_status["temp_high"]:
                    alerts.append(f"อุณหภูมิสูงเกิน {TEMP_HIGH_THRESHOLD}°C: {temp}°C")
                    alerted_status["temp_high"] = True
                    alerted_status["temp_low"] = False
            else:
                alerted_status["temp_high"] = False

            if temp < TEMP_LOW_THRESHOLD:
                if not alerted_status["temp_low"]:
                    alerts.append(f"อุณหภูมิต่ำกว่า {TEMP_LOW_THRESHOLD}°C: {temp}°C")
                    alerted_status["temp_low"] = True
                    alerted_status["temp_high"] = False
            else:
                alerted_status["temp_low"] = False

            if humidity > HUMIDITY_HIGH_THRESHOLD:
                if not alerted_status["humidity_high"]:
                    alerts.append(f"ความชื้นสูงเกิน {HUMIDITY_HIGH_THRESHOLD}%: {humidity}%")
                    alerted_status["humidity_high"] = True
                    alerted_status["humidity_low"] = False
            else:
                alerted_status["humidity_high"] = False

            if humidity < HUMIDITY_LOW_THRESHOLD:
                if not alerted_status["humidity_low"]:
                    alerts.append(f"ความชื้นต่ำกว่า {HUMIDITY_LOW_THRESHOLD}%: {humidity}%")
                    alerted_status["humidity_low"] = True
                    alerted_status["humidity_high"] = False
            else:
                alerted_status["humidity_low"] = False

            if alerts:
                msg = "⚠️ แจ้งเตือนสภาพแวดล้อมไม่เหมาะสม\n\n" + "\n\n".join(alerts) + f"\n\n⏰ เวลา: {ts.strftime('%Y-%m-%d %H:%M:%S')}"
                print("ส่งแจ้งเตือน:", msg)
                send_line_broadcast(msg)
                last_alert_time = ts
            else:
                print("ไม่มีการแจ้งเตือน")

        except Exception as e:
            print("❌ Error:", e)

        time.sleep(0.5)



if __name__ == "__main__":
    t = threading.Thread(target=check_environment, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5050)
