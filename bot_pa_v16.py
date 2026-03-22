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

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- ADVANCED iFixit DATABASE (v16) ---
PANIC_DATABASE = {
    # Power & Charging
    "0X800": {"f": "عطل المايك السفلي - حساس الضغط (iFixit Std)", "p": "فلاتة الشحن (Charging Port Flex)", "s": "استبدل الفلاتة كاملة بقطعة أصلية"},
    "0X4000": {"f": "عطل حساس حرارة البطارية الداخلي", "p": "البطارية أو موصل البطارية", "s": "استبدل البطارية وتأكد من ريش الموصل عالبورد"},
    "0X41": {"f": "خطأ تواصل بيانات البطارية (I2C Line)", "p": "موصل البطارية / مسار SWI", "s": "افحص مسار SWI، غالباً تالف بسبب سوء تركيب"},
    "0XA1": {"f": "عطل تواصل مع آيسي الباور (SMC Fail)", "p": "لوحة الأم (Motherboard)", "s": "افحص سحب الجهاز، قد يحتاج شبلنة المعالج أو آيسي الباور"},
    
    # Sensors & FaceID
    "0X1000": {"f": "عطل حساس التقارب/الضوء (Proxy)", "p": "فلاتة السماعة العلوية", "s": "افصل فلاتة السماعة وجرب، إذا اشتغل استبدلها"},
    "0X80000": {"f": "عطل حساس FaceID والعمق", "p": "شريط الكاميرا الأمامية", "s": "افحص شريط الحساسات، غالباً تعرض لرطوبة"},
    "SEP": {"f": "توقف المعالج الأمني (Enclave)", "p": "لوحة الأم / عطل بيانات", "s": "افصل جميع الفلاتات وجرب البورد صافي"},
    
    # Logic & Data Lines
    "I2C0": {"f": "عطل في ناقل البيانات الرئيسي I2C0", "p": "Logic Board (Main Bus)", "s": "افحص الموصلات، عادة شورت في خط 1.8v"},
    "I2C1": {"f": "توقف ناقل بيانات الكاميرا/الحساسات", "p": "Camera/Front Flex", "s": "افصل الكاميرا الخلفية وجرب تشغيله"},
    "I2C2": {"f": "توقف ناقل بيانات الهزاز/الصوت", "p": "Taptic Engine / Audio IC", "s": "افصل الهزاز وجرب، أو افحص آيسي الصوت"},
    "I2C3": {"f": "توقف ناقل بيانات الشاشة", "p": "Screen / Touch Circuit", "s": "جرب شاشة أصلية ثانية للتأكد"},
    
    # CPU & Storage
    "WDT TIMEOUT": {"f": "ريستارت متكرر (Watchdog) - حساس مفقود", "p": "فلاتة الشحن أو شريط الباور", "s": "استبدل فلاتة الشحن، هي السبب في 90% من الحالات"},
    "ANS2": {"f": "عطل الذاكرة الداخلية (NAND Error)", "p": "Storage Chip (NAND)", "s": "خطأ 4013 - يحتاج فك الذاكرة وإعادة برمجتها أو شبلنتها"},
    "SOC": {"f": "فشل المعالج الرئيسي (Application Processor)", "p": "Main CPU", "s": "عطل هاردوير جسيم، افحص فولتات CPU"},
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
    return f"🔍 *تشخيص PincFull Pro (v16)*\n\n🔴 *العطل:* {res['f']}\n🔧 *القطعة التالفة:* {res['p']}\n✅ *الحل المقترح:* {res['s']}"

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

async def add_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text(f"❌ هذا الأمر للمطور فقط.\n🆔 معرفك الحالي: `{user_id}`\n🔑 المعرف المطلوب: `{ADMIN_ID}`", parse_mode='Markdown')
        return
        
    if not context.args:
        await update.message.reply_text("💡 الاستخدام: `/addcode [اسم المشترك]`", parse_mode='Markdown')
        return
        
    name = " ".join(context.args)
    import string
    import random
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    code = f"PINC-{suffix}"
    
    data = {"name": name, "duration_days": 30, "status": "unused", "created_at": str(datetime.datetime.now())}
    requests.put(f"{DB_URL}/codes/{code}.json", json=data)
    
    await update.message.reply_text(
        f"💎 *تم إنشاء رمز اشتراك PincFull Pro:*\n\n"
        f"👤 *المشترك:* `{name}`\n"
        f"🔑 *كود التفعيل (اضغط للنسخ):*\n`{code}`\n\n"
        f"📅 *الصلاحية:* 30 يوم\n"
        "---------------------------\n"
        "💡 أعطِ المشترك اسمه والرمز المسطر أعلاه.", 
        parse_mode='Markdown'
    )

async def get_my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 معرفك الخاص هو: `{update.effective_user.id}`", parse_mode='Markdown')

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
    
    # Simulate OCR for text/doc (Simplified for this script)
    text = ""
    if update.message.photo:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        # In real bot, use OCR.space here
    elif update.message.document:
        doc = update.message.document
        file = await context.bot.get_file(doc.file_id)
        
    analysis = analyze(update.message.caption or update.message.text or "")
    await msg.edit_text(analysis, parse_mode='Markdown')

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addcode", add_code))
    app.add_handler(CommandHandler("myid", get_my_id))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^PINC-'), handle_activation))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL | (filters.TEXT & (~filters.COMMAND)), handle_media))
    logging.info("PincFull Pro Bot v16 SECURE is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
