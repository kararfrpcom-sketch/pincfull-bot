import os
import logging
import re
import requests
import datetime
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIG ---
BOT_TOKEN = "8786102103:AAGiwHNQHid3nWjUgxV0TvYja4tpCAjf8FM"
CHANNEL_USERNAME = "@Ai_pro26" # Admin channel for sub check
INVITE_LINK = "https://t.me/+TnTEQjUhUfozOTMy"
DB_URL = "https://pincfull-default-rtdb.firebaseio.com"
ADMIN_ID = 5917515784 # Your official ID
BOT_USERNAME = "@panic2_bot"
CHANNEL_USERNAME = "@Ai_pro26"
OCR_API_KEY = "K82110196288957"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- ADVANCED iFixit DATABASE (v16) ---
PANIC_DATABASE = {
    # --- POWER & CHARGING ---
    "0X800": {"f": "عطل المايك السفلي / فلاتة الشحن", "p": "Charging Port Flex", "s": "استبدل فلاتة الشحن كاملة بقطعة أصلية."},
    "0X4000": {"f": "عطل حساس حرارة البطارية (NTC)", "p": "Battery Unit / Connector", "s": "استبدل البطارية وافحص ريش الموصل على البورد."},
    "0X41": {"f": "فشل تواصل بيانات البطارية (I2C)", "p": "Battery Connector", "s": "أعد تركيب البطارية أو استبدلها بقطعة أصلية."},
    "0XA1": {"f": "عطل تواصل مع آيسي الباور (SMC)", "p": "Main Logic Board", "s": "عطل داخلي في المعالج أو آيسي الباور، يحتاج فحص احترافي."},
    "PRSO": {"f": "عطل حساس الباروميتر (الضغط الجوي)", "p": "Charging Port Flex", "s": "استبدل فلاتة الشحن فوراً."},
    
    # --- SENSORS & FACE ID ---
    "0X1000": {"f": "عطل حساس التقارب والضوء (Proxy)", "p": "Front Ear Speaker Flex", "s": "افصل فلاتة السماعة وجرب، إذا اختفى العطل استبدلها."},
    "ALS": {"f": "توقف حساس الإضاءة المحيطة", "p": "Front Flex / FaceID", "s": "افحص فلاتة الحساسات العلوية، غالباً تعرضت لرطوبة."},
    "PROX": {"f": "عطل في حساس التقارب (Proximity)", "p": "Earspeaker Flex", "s": "استبدل شريط السماعة العلوية."},
    "0X80000": {"f": "عطل حساس FaceID والعمق", "p": "Dot Projector / Infrared Cam", "s": "عطل حساس هاردوير، يحتاج نقله لبرمجة قطعة ثانية."},
    
    # --- LOGIC & PERIPHERALS ---
    "WDT TIMEOUT": {"f": "فشل حساس مفقود (Watchdog Restart)", "p": "Power/Charging/Volume Flex", "s": "استبدل فلاتة الشحن أولاً، ثم فلاتة الباور/الأزرار."},
    "I2C0": {"f": "خطأ في ناقل البيانات الرئيسي I2C0", "p": "Logic Board Circuit", "s": "شورت في خط 1.8V، يحتاج ميكروسكوب للفحص."},
    "I2C1": {"f": "توقف تواصل الكاميرا/الحساسات", "p": "Camera Connector", "s": "افصل الكاميرات الواحدة تلو الأخرى وجرب."},
    "0X40000": {"f": "فشل تواصل Taptic Engine (الهزاز)", "p": "Taptic Engine Flex", "s": "استبدل محرك الاهتزاز أو فلاتة الشحن."},
    
    # --- CPU & STORAGE ---
    "ANS2": {"f": "فشل ذاكرة الناند (NAND Storage)", "p": "Internal Memory Chip", "s": "خطأ 4013، يحتاج إعادة برمجة الذاكرة أو استبدالها."},
    "SEP": {"f": "توقف معالج الحماية (Secure Enclave)", "p": "CPU / Logic Board", "s": "عطل برمجي جسيم أو شورت في تغذية المعالج."},
    "SOC": {"f": "عطل المعالج الرئيسي (Processor)", "p": "Main CPU", "s": "عطل هاردوير جسيم، لا يمكن إصلاحه إلا بنقل البورد."},
    
    # --- THERMAL ---
    "THERMALMONITORD": {"f": "ارتفاع حرارة مفاجئ / حساس معطل", "p": "FaceID or Battery Flex", "s": "افصل فلاتة السماعة العلوية أولاً للتجربة."},
}

# --- LOGIC ---
def analyze(text):
    t = text.upper().replace("\n", " ").replace("\r", " ")
    keys = sorted(PANIC_DATABASE.keys(), key=len, reverse=True)
    results = [PANIC_DATABASE[k] for k in keys if k in t]
    
    if not results:
        m = re.search(r"0X[0-9A-F]{2,6}", t)
        if m: return f"⚠️ كود غير مسجل: `{m.group()}`\nيرجى التواصل مع المطور للتحديث."
        return "❌ لم يتم التعرف على العطل. يرجى إرسال ملف IPS أو صورة واضحة."

    # Return only the best single hit for 100% accuracy
    res = results[0]
    return (
        f"📋 *نتائج فحص الجهاز ومشاكله*\n"
        f"━━━━━━━━━━━━━━\n"
        f"📍 *المكان:* {res['p']}\n"
        f"💡 *الإجراء:* {res['s']}\n\n"
        f"⚠️ *التشخيص:* {res['f']}"
    )

async def check_user_status(user_id) -> dict:
    """Returns user record if active, else None"""
    res = requests.get(f"{DB_URL}/users/{user_id}.json").json()
    if not res: return None
    
    # Check expiry
    expiry = datetime.datetime.strptime(res['end_date'], "%Y-%m-%d %H:%M:%S")
    if datetime.datetime.now() > expiry:
        return {"status": "expired"}
        
    return res

async def is_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status not in ['left', 'kicked']
    except: return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    # 1. Check Mandatory Sub
    if not await is_member(update, context):
        await update.message.reply_text(f"🚫 *يجب الاشتراك في القناة أولاً:*\n{INVITE_LINK}\n\nبعد الاشتراك، اضغط /start", parse_mode='Markdown')
        return

    # 2. Check Activation
    user_data = await check_user_status(user_id)
    if not user_data:
        msg = (
            "⚠️ *أهلاً بك في PincFull Pro v16*\n\n"
            "هذا البوت مخصص للمشتركين فقط. لتفعيل حسابك، يرجى اتباع الخطوات:\n"
            f"1️⃣ اشترك في القناة: {INVITE_LINK}\n"
            "2️⃣ تواصل معي لشراء كود التفعيل: @Kguitaraa\n"
            f"3️⃣ أرسل لي معرفك الخاص: `{user_id}`\n\n"
            "⚠️ *ملاحظة:* إذا قمت بشراء الكود، أرسله هنا فوراً بالتنسيق `PINC-XXXX`"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')
        return
    
    if user_data.get("status") == "expired":
        await update.message.reply_text("⌛ *عذراً، انتهت مدة اشتراكك (30 يوم).*\nيرجى التواصل مع المطور للتجديد.")
        return

    # User is active
    msg = (
        f"💎 *PincFull Pro AI Suite*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 *المشترك:* `{user_data['name']}`\n"
        f"📅 *البداية:* `{user_data['start_date'].split(' ')[0]}`\n"
        f"⌛ *النهاية:* `{user_data['end_date'].split(' ')[0]}`\n"
        f"━━━━━━━━━━━━━━━\n\n"
        "📱 *جاهز للفحص:* أرسل صورة المخطط أو ملف Panic Log الآن."
    )
    await update.message.reply_text(msg, parse_mode='Markdown', disable_web_page_preview=True)

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Admin Bypass
    is_admin = (user_id == ADMIN_ID)
    user_data = {"name": "ADMIN", "status": "active"} if is_admin else await check_user_status(user_id)
    
    if not is_admin and (not user_data or user_data.get("status") == "expired"):
        await update.message.reply_text("🚫 لا تملك اشتراكاً فعالاً لشغل الجهاز. يرجى تزويد البوت بكود التفعيل أولاً.")
        return

    # Store message for callback
    context.user_data['pending_msg'] = update.message
    
    # Show Model Selection
    keyboard = [
        [InlineKeyboardButton("iPhone X / XS / XR", callback_data="mod_x"), InlineKeyboardButton("iPhone 11 Series", callback_data="mod_11")],
        [InlineKeyboardButton("iPhone 12 Series", callback_data="mod_12"), InlineKeyboardButton("iPhone 13 Series", callback_data="mod_13")],
        [InlineKeyboardButton("iPhone 14 Series", callback_data="mod_14"), InlineKeyboardButton("iPhone 15 Series", callback_data="mod_15")],
        [InlineKeyboardButton("iPhone 16 Series (Pro/Max)", callback_data="mod_16")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📱 *يرجى اختيار نوع الجهاز المراد فحصه:*", reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    model_name = query.data.replace("mod_", "iPhone ")
    msg = context.user_data.get('pending_msg')
    if not msg: return

    edit_msg = await query.edit_message_text(f"⏳ *جاري فحص جهاز {model_name} ومشاكله بعناية...*", parse_mode='Markdown')
    
    extracted_text = ""
    try:
        if msg.photo:
            photo_file = await msg.photo[-1].get_file()
            img_path = "temp_scan.jpg"
            await photo_file.download_to_drive(img_path)
            with open(img_path, 'rb') as f:
                res = requests.post("https://api.ocr.space/parse/image", data={'apikey': OCR_API_KEY, 'OCREngine': '2'}, files={'file': f}, timeout=20)
            if os.path.exists(img_path): os.remove(img_path)
            dat = res.json()
            extracted_text = dat["ParsedResults"][0]["ParsedText"] if dat.get("ParsedResults") else ""
        elif msg.document:
            doc_file = await msg.document.get_file()
            res = requests.get(doc_file.file_path, timeout=15)
            extracted_text = res.text
        elif msg.text:
            extracted_text = msg.text

        final_text = (msg.caption or "") + " " + extracted_text
        if not extracted_text.strip():
            await edit_msg.edit_text("⚠️ لم يتم العثور على بيانات واضحة للفحص. تأكد من وضوح الملف.")
            return

        analysis = analyze(final_text)
        await edit_msg.edit_text(f"📱 *الجهاز المختبر:* {model_name}\n\n{analysis}", parse_mode='Markdown')

    except Exception as e:
        await edit_msg.edit_text("❌ حدث خطأ تقني أثناء الفحص. حاول مجدداً بنسخة نصية.")

async def get_my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 معرفك الخاص للفحص هو: `{update.effective_user.id}`", parse_mode='Markdown')

async def handle_activation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip().upper()
    
    if not text.startswith("PINC-"): return
    
    # Check if code exists
    code_info = requests.get(f"{DB_URL}/codes/{text}.json").json()
    if not code_info:
        await update.message.reply_text("❌ رمز التفعيل غير صحيح.")
        return
        
    if code_info.get("status") != "unused":
        # Alert Admin about potential fraud
        requests.post(f"{DB_URL}/alerts.json", json={"user_id": user_id, "code": text, "type": "shared_code_attempt"})
        await update.message.reply_text("⚠️ هذا الرمز قيد الاستخدام من قبل جهاز آخر! تم إرسال تنبيه للمطور.")
        return

    # Activate User
    start_date = datetime.datetime.now()
    end_date = start_date + datetime.timedelta(days=30)
    
    user_record = {
        "name": code_info['name'],
        "code": text,
        "start_date": start_date.strftime("%Y-%m-%d %H:%M:%S"),
        "end_date": end_date.strftime("%Y-%m-%d %H:%M:%S"),
        "device_id": str(user_id) # Locked to this Telegram ID
    }
    
    # Save user, mark code as used
    requests.put(f"{DB_URL}/users/{user_id}.json", json=user_record)
    requests.patch(f"{DB_URL}/codes/{text}.json", json={"status": "used", "registered_to": user_id})
    
    await update.message.reply_text("🎉 *تم تفعيل اشتراكك بنجاح لمدة 30 يوم!*\nاستخدم /start لعرض التفاصيل.")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Admin Bypass
    if user_id == ADMIN_ID:
        user_data = {"name": "ADMIN (Master)", "status": "active"}
    else:
        user_data = await check_user_status(user_id)
        if not user_data or user_data.get("status") == "expired":
            await update.message.reply_text("🚫 لا تملك اشتراكاً فعالاً. أرسل رمز التفعيل أولاً.")
            return

    msg = await update.message.reply_text("⏳ جاري التحليل بالذكاء الصناعي...")
    
    extracted_text = ""
    
    try:
        if update.message.photo:
            # Download Photo for better OCR reliability
            photo_file = await update.message.photo[-1].get_file()
            img_path = "temp_ocr.jpg"
            await photo_file.download_to_drive(img_path)
            
            with open(img_path, 'rb') as f:
                payload = {'apikey': OCR_API_KEY, 'OCREngine': '2', 'isOverlayRequired': False}
                files = {'file': f}
                res = requests.post("https://api.ocr.space/parse/image", data=payload, files=files, timeout=20)
            
            # Clean up
            if os.path.exists(img_path): os.remove(img_path)
            
            dat = res.json()
            if dat.get("ParsedResults"):
                extracted_text = dat["ParsedResults"][0]["ParsedText"]
            else:
                await msg.edit_text("❌ فشلت قراءة الصورة. تأكد من جودة الصورة وأن الكود واضح.")
                return

        elif update.message.document:
            # Read Text File directly from URL (Small files)
            doc_file = await update.message.document.get_file()
            res = requests.get(doc_file.file_path, timeout=15)
            extracted_text = res.text

        elif update.message.text:
            extracted_text = update.message.text

        # Analyze
        final_text = (update.message.caption or "") + " " + extracted_text
        if not extracted_text.strip() and not (update.message.caption or "").strip():
             await msg.edit_text("⚠️ لم يتم العثور على أي نص في الصورة.")
             return

        analysis = analyze(final_text)
        await msg.edit_text(analysis, parse_mode='Markdown')

    except Exception as e:
        logging.error(f"Media Error: {e}")
        await msg.edit_text("❌ حدث خطأ أثناء التحليل. حاول مرة أخرى.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", get_my_id))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^PINC-'), handle_activation))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL | (filters.TEXT & (~filters.COMMAND)), handle_media))
    logging.info("PincFull Pro Diagnostic Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
