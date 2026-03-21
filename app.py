import os
import logging
import re
from flask import Flask, request

BOT_TOKEN = "8786102103:AAGiwHNQHid3nWjUgxV0TvYja4tpCAjf8FM"

# ===== قاعدة بيانات الأعطال =====
PANIC_DATABASE = {
    "PRS0": {"f": "حساس الضغط بفلاتة الشحن معطل", "p": "فلاتة الشحن", "s": "استبدل فلاتة الشحن"},
    "MIC1": {"f": "الميكروفون السفلي معطل", "p": "فلاتة الشحن", "s": "استبدل فلاتة الشحن"},
    "MIC2": {"f": "ميكروفون الضجيج العلوي معطل", "p": "شريط الكاميرا الأمامية أو شريط الباور", "s": "استبدل شريط الكاميرا الأمامية أو شريط الباور"},
    "TG0B": {"f": "حساس حرارة البطارية معطل", "p": "البطارية", "s": "استبدل البطارية بأصلية"},
    "TG0V": {"f": "حساس جهد البطارية معطل", "p": "آيسي الشحن", "s": "افحص آيسي الشحن وموصل البطارية"},
    "TG0P": {"f": "حساس حرارة أمامي معطل", "p": "شريط الكاميرا الأمامية", "s": "استبدل شريط الكاميرا الأمامية"},
    "WDT TIMEOUT": {"f": "النظام توقف — ريستارت كل 3 دقائق", "p": "فلاتة الشحن", "s": "استبدل فلاتة الشحن — إذا تكرر سوي ريستور"},
    "ANS2": {"f": "عطل الذاكرة الداخلية — NAND", "p": "NAND Flash", "s": "سوي ريستور — خطأ 4013 = ذاكرة تالفة تحتاج شبلنة"},
    "SEP": {"f": "معالج الأمان FaceID معطل", "p": "فلاتة سماعة الأذن", "s": "افصل فلاتة سماعة الأذن وجرب"},
    "SOC": {"f": "خطأ المعالج الرئيسي", "p": "المعالج", "s": "افحص ملفات التغذية — قد يحتاج شبلنة"},
    "SMC PANIC": {"f": "عطل إدارة الطاقة — ريستارت كل 3 دقائق", "p": "آيسي الباور", "s": "اقرأ كود HEX لتحديد القطعة"},
    "SMC ASSERTION": {"f": "فشل تأكيد SMC", "p": "دوائر الطاقة", "s": "اقرأ كود HEX المصاحب"},
    "AOP PANIC": {"f": "معالج الخلفية معطل", "p": "شريط الباور أو الصوت", "s": "افصل فلاتة سماعة الأذن أو شريط الباور"},
    "AOP NMI": {"f": "مقاطعة طاقة AOP", "p": "شريط الباور", "s": "افصل شريط الباور"},
    "SLEEP/WAKE": {"f": "تعليق السكون — الجهاز ما يرد", "p": "شريط الباور", "s": "استبدل شريط الباور"},
    "SMC BOSCH": {"f": "خلل قناة الصوت — غالباً رطوبة", "p": "فلاتة الشحن", "s": "نظف اللوحة — استبدل فلاتة الشحن"},
    "0X20": {"f": "SMC 0x20 — دائرة الشحن", "p": "آيسي الشحن", "s": "افحص آيسي الشحن"},
    "0X40": {"f": "SMC 0x40 — آيسي قياس البطارية", "p": "البطارية", "s": "جرب بطارية أصلية"},
    "0X41": {"f": "SMC 0x41 — بيانات البطارية", "p": "البطارية", "s": "استبدل البطارية بأصلية"},
    "0XA1": {"f": "SMC 0xa1 — حساس البطارية", "p": "البطارية", "s": "استبدل البطارية بأصلية"},
    "0X400": {"f": "SMC 0x400 — الجيروسكوب", "p": "حساس الجيروسكوب", "s": "افحص مسار الجيروسكوب"},
    "0X800": {"f": "SMC 0x800 — حساس فلاتة الشحن ★ الأشيع", "p": "فلاتة الشحن", "s": "استبدل فلاتة الشحن فوراً"},
    "0X1000": {"f": "SMC 0x1000 — حساس التقارب", "p": "شريط الكاميرا الأمامية", "s": "افصل شريط الكاميرا وجرب"},
    "0X4000": {"f": "SMC 0x4000 — حساس حرارة البطارية", "p": "البطارية", "s": "استبدل البطارية بأصلية"},
    "0X20000": {"f": "SMC 0x20000 — جيروسكوب/ساندويتش (14 Pro)", "p": "بورد الساندويتش", "s": "افحص بورد الساندويتش"},
    "0X40000": {"f": "SMC 0x40000 — منفذ الشحن (14+)", "p": "فلاتة الشحن", "s": "استبدل فلاتة الشحن"},
    "0X80000": {"f": "SMC 0x80000 — فلاتة التقارب", "p": "فلاتة حساس التقارب", "s": "استبدل فلاتة حساس التقارب"},
    "0X100000": {"f": "SMC 0x100000 — زر الباور", "p": "شريط الباور", "s": "استبدل شريط الباور"},
    "I2C0": {"f": "ناقل بيانات الشحن معطل", "p": "فلاتة الشحن / آيسي الشحن", "s": "استبدل فلاتة الشحن"},
    "I2C1": {"f": "ناقل بيانات الكاميرا معطل", "p": "الكاميرا الخلفية / شريط الباور", "s": "افصل الكاميرات — افصل شريط الباور"},
    "I2C2": {"f": "ناقل بيانات الصوت معطل", "p": "الهزاز / آيسي الصوت", "s": "افصل الهزاز وجرب"},
    "I2C3": {"f": "ناقل بيانات الشاشة معطل", "p": "شريط الكاميرا الأمامية / الشاشة", "s": "جرب شاشة ثانية"},
}


def analyze(text):
    t = text.upper().replace("\n", " ").replace("\r", " ")
    t = " ".join(t.split())
    keys = sorted(PANIC_DATABASE.keys(), key=len, reverse=True)
    results = [{"code": k, **PANIC_DATABASE[k]} for k in keys if k in t]
    if not results:
        m = re.search(r"0X[0-9A-F]{2,6}", t)
        if m:
            return f"⚠️ كود غير معروف: `{m.group()}`\nتواصل مع المطور لإضافته."
        return "❌ *فشل التحليل*\n\nلم يتم اكتشاف أكواد معروفة.\nتأكد من نسخ النص من ملف panic-full."
    report = f"🔍 *نتيجة الفحص — {len(results)} عطل:*\n\n"
    for r in results:
        report += f"🔴 *العطل:* {r['f']}\n🔧 *القطعة:* {r['p']}\n✅ *الحل:* {r['s']}\n─────────────\n"
    report += "\n_PincFull Pro | Dev: kararAhmed_"
    return report


# ===== Flask + Telegram Webhook =====
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

import requests

API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(chat_id, text):
    requests.post(f"{API}/sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    })


def handle_update(data):
    try:
        msg = data.get("message", {})
        chat_id = msg.get("chat", {}).get("id")
        if not chat_id:
            return

        # /start command
        text = msg.get("text", "")
        if text == "/start":
            send_message(chat_id,
                "💎 *PincFull Pro Analyzer 24/7*\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "مرحباً! البوت يعمل 24/7.\n\n"
                "*طريقة الفحص:*\n"
                "1️⃣ أرسل ملف .ips\n"
                "2️⃣ أو اكتب كود مثل 0x800\n"
                "3️⃣ أو الصق نص الـ Panic كاملاً\n\n"
                "🌐 الموقع: pincfull.web.app\n"
                "👨‍💻 *Dev: kararAhmed*"
            )
            return

        # Text message
        if text and not text.startswith("/"):
            result = analyze(text)
            send_message(chat_id, result)
            return

        # Document / file
        doc = msg.get("document")
        if doc:
            file_id = doc.get("file_id")
            # Get file path
            r = requests.get(f"{API}/getFile?file_id={file_id}").json()
            file_path = r.get("result", {}).get("file_path", "")
            if file_path:
                file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                content = requests.get(file_url).text
                result = analyze(content)
                send_message(chat_id, result)
            return

    except Exception as e:
        logging.error(f"Error: {e}")


@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    handle_update(data)
    return "ok"


@app.route("/")
def index():
    return "PincFull Pro Bot is Running! 🚀"


@app.route("/setup")
def setup_webhook():
    """Call this once to set the webhook URL"""
    url = request.host_url.rstrip("/") + f"/webhook/{BOT_TOKEN}"
    r = requests.get(f"{API}/setWebhook?url={url}")
    return f"Webhook set: {r.json()}"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
