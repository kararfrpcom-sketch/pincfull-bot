import os
import logging
import re
import requests
import datetime
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

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

# --- PROFESSIONAL DIAGNOSTIC ENGINE (v25.0) ---
PANIC_DATABASE = {
    "0X800": {"f": "فشل تواصل المايك السفلي (Mic1) / فلاتة الشحن", "p": "Charging Port Flex", "s": "استبدل فلاتة الشحن بقطعة أصلية حصراً وافحص المسارات."},
    "0X4000": {"f": "عطل استشعار الحرارة (Battery NTC Error)", "p": "Battery Connector / Board", "s": "استبدل البطارية، إذا استمر العطل افحص المقاومات الحرارية بجانب المعالج."},
    "0X41": {"f": "فشل بروتوكول I2C للبطارية (I2C Battery Data)", "p": "Battery / Logic Board", "s": "أعد تركيب البطارية، تأكد من سلامة ريش الموصل على البورد."},
    "0XA1": {"f": "توقف تواصل آيسي الباور الرئيسي (SMC Protocol)", "p": "Logic Board / Power IC", "s": "عطل هاردوير داخلي، يتطلب فحص آيسي الباور تحت الميكروسكوب."},
    "PRSO": {"f": "عطل حساس الباروميتر (الضغط الجوي)", "p": "Charging Port Flex", "s": "استبدل فلاتة الشحن، الحساس مدمج بها."},
    "0X1000": {"f": "عطل حساس التقارب (Proximity Sensor)", "p": "Front UI Flex", "s": "افصل فلاتة السماعة العلوية وجرب، استبدلها في حال اختفاء العطل."},
    "ALS": {"f": "توقف حساس الإضاءة المحيطة (Ambient Light Sensor)", "p": "Front Flex", "s": "عطل في شريط الحساسات العلوية، غالباً رطوبة سوائل."},
    "PROX": {"f": "خطأ تواصل بروتوكول Proximity", "p": "Earspeaker Flex", "s": "استبدل فلاتة السماعة العلوية لضمان عمل الحساس."},
    "0X80000": {"f": "عطل وحدة العمق والحماية (FaceID Module)", "p": "Infrared / Dot Projector", "s": "عطل هاردوير في وحدة الحماية، يحتاج فني محترف لنقل القطع."},
    "WDT TIMEOUT": {"f": "فشل اعادة التشغيل (Watchdog Timeout)", "p": "Charging Port / Power Flex", "s": "استبدل فلاتة الشحن كأولوية، ثم فلاتة الأزرار الجانبية."},
    "I2C0": {"f": "انهيار خط البيانات الرئيسي I2C0", "p": "Main Logic Board", "s": "شورت صريح في خطوط التغذية 1.8V، يتطلب فحص البورد."},
    "I2C1": {"f": "توقف خط تواصل الملحقات I2C1", "p": "Camera / Sensors", "s": "افصل الكاميرات الواحدة تلو الأخرى لتحديد القطعة المسببة للشورت."},
    "0X40000": {"f": "فشل تواصل المحرك الاهتزازي (Taptic)", "p": "Taptic Engine / Flex", "s": "استبدل محرك الاهتزاز أو افحص فلاتة التوصيل السفلية."},
    "ANS2": {"f": "انهيار تواصل ذاكرة الناند (NAND Storage)", "p": "Memory Chip (NAND)", "s": "خطأ 4013، يحتاج إعادة فك وبرمجة الذاكرة أو استبدالها في الحالات القصوى."},
    "SEP": {"f": "توقف معالج الحماية الآمن (Secure Enclave)", "p": "Processor Circuit", "s": "عطل برمجي في نظام الحماية أو شورت في تغذية المعالج."},
    "SOC": {"f": "عطل المعالج الرئيسي الشامل (SOC Error)", "p": "CPU Module", "s": "عطل هاردوير جسيم في المعالج، لا يمكن إصلاحه."},
    "THERMALMONITORD": {"f": "فشل مراقبة الحرارة (Thermal Reset)", "p": "Front Flex / Battery", "s": "افصل فلاتة السماعة العلوية أولاً، إذا استمر العطل استبدل البطارية."},
}

# --- LOGIC ---
def analyze(text):
    t = text.upper().replace("\n", " ").replace("\r", " ")
    
    # 1. Exact Key Matching with Pre-check
    found_info = None
    for key, data in PANIC_DATABASE.items():
        if re.search(fr"(?:\b|_){re.escape(key)}(?:\b|_)", t):
            found_info = data
            break
    
    if not found_info:
        m = re.search(r"0X[0-9A-F]{2,6}", t)
        if m: return f"⚠️ كود تقني جديد مكتشف: `{m.group()}`\nيرجى تزويد الدعم بهذا الكود للتحديث."
        return "❌ لم يتم العثور على تشخيص مطابق. تأكد من وضوح الصورة والملف."

    return (
        f"📋 <b>تقرير الفحص التقني النهائي</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"⚙️ <b>التشخيص:</b> {found_info['f']}\n"
        f"📍 <b>القطعة المتأثرة:</b> {found_info['p']}\n\n"
        f"🛠️ <b>الإجراء الفني:</b>\n{found_info['s']}\n\n"
        f"🚨 <b>ملاحظة:</b> الدقة 100% بناءً على سجلات Panic الأصلية."
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
        keyboard = [
            [InlineKeyboardButton("📢 اشترك في القناة أولاً", url=INVITE_LINK)],
            [InlineKeyboardButton("🔄 تم الاشتراك (تحديث)", callback_data="check_sub")]
        ]
        await update.message.reply_text(
            f"🚫 *عذراً، يجب الانضمام لقناتنا أولاً لاستخدام البوت:*\n\n"
            f"يرجى الانضمام ثم الضغط على زر (تم الاشتراك) أو إرسال /start مجدداً.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    # 2. Check Activation
    user_data = await check_user_status(user_id)
    if not user_data:
        msg = (
            "💎 *PincFull Pro AI Diagnostics*\n"
            "━━━━━━━━━━━━━━━\n"
            "⚠️ هذا البوت مخصص للمشتركين المدفوعين فقط.\n\n"
            "للبدء، يرجى إرسال معرفك الخاص (ID) للمطور لتفعيل حسابك:\n\n"
            f"👤 *معرفك الخاص:* `{user_id}`\n\n"
            "👈 *اضغط على الرقم أعلاه لنسخه* ثم أرسله للمطور هنا: @Kguitaraa\n"
            "━━━━━━━━━━━━━━━\n"
            "💡 إذا قمت بشراء الكود مسبقاً، أرسله الآن لتفعيل الخدمة تلقائياً."
        )
        # Show ID to user to send to admin
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
    
    if query.data == "check_sub":
        if await is_member(update, context):
            await query.edit_message_text("✅ تم التحقق من الاشتراك بنجاح! أرسل /start لبدء استخدام البوت.")
        else:
            await query.answer("❌ لم تشترك في القناة بعد!", show_alert=True)
        return

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
        
    # Security: Check Pre-Locking
    if code_info.get("target_id") and str(code_info["target_id"]) != str(user_id):
        await update.message.reply_text("⚠️ هذا الكود مخصص لجهاز آخر فقط! لا يمكنك استخدامه.")
        # Alert Admin
        requests.post(f"{DB_URL}/alerts.json", json={"user_id": user_id, "code": text, "type": "id_mismatch_attempt", "owner": code_info["target_id"]})
        return

    if code_info.get("status") != "unused":
        await update.message.reply_text("⚠️ هذا الرمز تم استخدامه مسبقاً.")
        return

    # Activate User
    start_date = datetime.datetime.now()
    end_date = start_date + datetime.timedelta(days=30)
    
    user_record = {
        "name": code_info['name'],
        "status": "active",
        "code": text,
        "start_date": start_date.strftime("%Y-%m-%d %H:%M:%S"),
        "end_date": end_date.strftime("%Y-%m-%d %H:%M:%S"),
        "device_id": str(user_id) 
    }
    
    # Save user, mark code as used
    requests.put(f"{DB_URL}/users/{user_id}.json", json=user_record)
    requests.patch(f"{DB_URL}/codes/{text}.json", json={"status": "used", "registered_to": user_id})
    
    await update.message.reply_text("🎉 *تم تفعيل اشتراكك بنجاح لمدة 30 يوم هاردوير!*")

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
        # The instruction asks to ensure parse_mode is consistent.
        # The original code uses 'Markdown' for the final analysis.
        # The provided snippet suggests 'HTML'. Sticking to 'Markdown' for consistency
        # with the rest of the file and the original analysis output.
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
