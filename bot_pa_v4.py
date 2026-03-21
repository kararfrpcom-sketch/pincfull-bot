import os
import logging
import re
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8786102103:AAGiwHNQHid3nWjUgxV0TvYja4tpCAjf8FM"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

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
        return "❌ *فشل التحليل*\n\nلم يتم اكتشاف أكواد معروفة.\nتأكد من وضوح النص أو الصورة."
        
    report = f"🔍 *نتيجة الفحص — {len(results)} عطل:*\n\n"
    for r in results:
        report += f"🔴 *العطل:* {r['f']}\n🔧 *القطعة:* {r['p']}\n✅ *الحل:* {r['s']}\n─────────────\n"
    report += "\n_PincFull Pro | Dev: kararAhmed_"
    return report

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "💎 *PincFull Pro Analyzer 24/7*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "أرسل **صورة** لسجل البانيك واستلم الحل بثواني! الميزة الذكية تعمل الآن بدون استهلاك الخادم.\n\n"
        "أو أرسل ملف `.ips` أو انسخ البانيك والصقه هنا.\n\n"
        "🌐 *موقع الويب:* pincfull.web.app\n"
        "👨‍💻 *Dev: kararAhmed*",
        parse_mode='Markdown'
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("📸 تم استلام الصورة... جاري الفحص عبر الذكاء الاصطناعي...")
    photo = update.message.photo[-1] # أعلى دقة
    
    file_path = f"tmp_{photo.file_id}.jpg"
    try:
        # تنزيل الصورة مؤقتاً
        file = await context.bot.get_file(photo.file_id)
        await file.download_to_drive(file_path)
        
        # إرسال الصورة مباشرة للمحرك
        api_url = "https://api.ocr.space/parse/image"
        payload = {'apikey': 'K82110196288957', 'language': 'eng', 'OCREngine': '2'} # المحرك الثاني أفضل للصور
        with open(file_path, 'rb') as f:
            response = requests.post(api_url, data=payload, files={'file': f}).json()
        
        if response.get("IsErroredOnProcessing"):
            err = response.get("ErrorMessage", ["Unknown"])[0]
            await msg.edit_text(f"❌ فشل الفحص من الخادم السحابي.\\nالسبب: {err}")
            return
            
        text = ""
        for result in response.get("ParsedResults", []):
            text += result.get("ParsedText", "") + " "
            
        if len(text.strip()) < 5:
            await msg.edit_text("⚠️ لم يتم التعرف على النص بدقة!\\nتأكد أن الصورة واضحة وليست مظلمة أو مهزوزة.")
            return
            
        analysis = analyze(text)
        await msg.edit_text(analysis, parse_mode='Markdown')
        
    except Exception as e:
        await msg.edit_text(f"❌ خطأ أثناء الفحص: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    document = update.message.document
    msg = await update.message.reply_text("⏳ جاري تحليل الملف...")
    file_path = f"tmp_{document.file_id}"
    try:
        file = await context.bot.get_file(document.file_id)
        await file.download_to_drive(file_path)
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        result = analyze(content)
        await msg.edit_text(result, parse_mode='Markdown')
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if text.startswith('/'): return
    result = analyze(text)
    await update.message.reply_text(result, parse_mode='Markdown')

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    logging.info("PincFull Pro Polling Bot is running with Cloud OCR...")
    
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
