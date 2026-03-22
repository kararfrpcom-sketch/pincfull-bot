import logging
import requests
import datetime
import string
import random
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# --- CONFIG ---
BOT_TOKEN = "8746851791:AAFiYcUNitDjGfqG8_WMc70gLMaDQEUwlJk"
DB_URL = "https://pincfull-default-rtdb.firebaseio.com"
ADMIN_ID = 5917515784 # Your official ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- UTILS ---
def gen_code():
    return "PINC-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

from telegram import ReplyKeyboardMarkup, KeyboardButton

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ هذا البوت مخصص للإدارة فقط.")
        return
    
    keyboard = [
        [KeyboardButton("➕ إضافة مشترك"), KeyboardButton("👥 المشتركين")],
        [KeyboardButton("🔍 بحث عن مشترك")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("👋 أهلاً بك سيدي المدير في لوحة تحكم PincFull Pro.\nاستخدم الأزرار أدناه للتحكم:", reply_markup=reply_markup)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    text = update.message.text
    state = context.user_data.get('state')

    # Menu Actions
    if text == "➕ إضافة مشترك":
        await update.message.reply_text("🆔 حسناً، أرسل الآن **رقم الايدي (ID)** الخاص بالزبون:")
        context.user_data['state'] = 'WAITING_ID'
        return
    
    elif text == "👥 المشتركين":
        users = requests.get(f"{DB_URL}/users.json").json() or {}
        if not users:
            await update.message.reply_text("📭 لا يوجد مشتركون حالياً.")
            return
        msg = "👥 *إدارة جميع المشتركين (v19.0):*\n\n"
        for uid, data in users.items():
            st = data.get('status', 'active')
            if st == "pending": icon = "⏳ قيد التفعيل"
            elif st == "blocked": icon = "🚫 محظور"
            else:
                expiry = datetime.datetime.strptime(data['end_date'], "%Y-%m-%d %H:%M:%S")
                icon = "✅ نشط" if expiry > datetime.datetime.now() else "⌛ منتهي"
            
            msg += f"👤 *{data['name']}* (`{uid}`)\nالحالة: {icon}\nالتحكم: /manage_{uid}\n\n"
        await update.message.reply_text(msg, parse_mode='Markdown')
        return

    # State Flow
    if state == 'WAITING_ID':
        if not text.isdigit():
            await update.message.reply_text("⚠️ خطأ، يرجى إرسال رقم الايدي فقط:")
            return
        context.user_data['temp_id'] = text
        await update.message.reply_text(f"👤 ممتاز، معرف الزبون هو `{text}`\nالآن أرسل **اسم الزبون**:")
        context.user_data['state'] = 'WAITING_NAME'
        
    elif state == 'WAITING_NAME':
        name = text.strip()
        tid = context.user_data.get('temp_id')
        
        code = gen_code()
        start_date = datetime.datetime.now()
        end_date = start_date + datetime.timedelta(days=30)
        
        # 1. Save Pre-Locked Code
        requests.put(f"{DB_URL}/codes/{code}.json", json={
            "name": name, 
            "status": "unused", 
            "target_id": tid, # LOCKING
            "created_at": str(start_date)
        })
        
        # 2. Create Immediate User Record (CRM Visibility)
        requests.put(f"{DB_URL}/users/{tid}.json", json={
            "name": name,
            "status": "pending",
            "start_date": str(start_date),
            "end_date": str(end_date), # Estimated
            "code": code
        })
        
        # Prepare Package
        msg = (
            f"💎 *تم تفعيل اشتراكك في PincFull Pro الاستثنائي* 💎\n\n"
            f"👤 *اسم المشترك:* `{name}`\n"
            f"🆔 *معرف الدخول:* `{tid}`\n"
            f"🔑 *كود التفعيل (بوت + موقع):*\n`{code}`\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📅 *تاريخ البدء:* `{start_date.strftime('%Y-%m-%d')}`\n"
            f"⌛ *تاريخ الانتهاء:* `{end_date.strftime('%Y-%m-%d')}`\n"
            f"⏰ *المدة المتبقية:* `30 يوم`\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"🤖 *رابط بوت الفحص:* @panic2_bot\n"
            f"🌐 *رابط الموقع الرسمي:* https://pincfull.web.app\n\n"
            f"💡 *ملاحظة:* الكود يعمل على جهازك فقط ولا يمكن مشاركته."
        )
        await update.message.reply_text("✅ تم إنشاء المشترك بنجاح في النظام (قيد التفعيل). إليك الرسالة:")
        await update.message.reply_text(msg, parse_mode='Markdown')
        context.user_data['state'] = None
        context.user_data['temp_id'] = None

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "btn_list":
        # Reuse logic
        users = requests.get(f"{DB_URL}/users.json").json() or {}
        if not users:
            await query.edit_message_text("📭 لا يوجد مشتركون حالياً.")
            return
        msg = "👥 *قائمة المشتركين الحالية:*\n\n"
        for uid, data in users.items():
            status = "✅ نشط" if datetime.datetime.strptime(data['end_date'], "%Y-%m-%d %H:%M:%S") > datetime.datetime.now() else "⌛ منتهي"
            msg += f"👤 *{data['name']}* ({uid})\n📅 ينتهي: `{data['end_date'].split(' ')[0]}`\n{status}\n/manage_{uid}\n\n"
        await query.edit_message_text(msg, parse_mode='Markdown')

    elif query.data.startswith("action_"):
        _, action, tid = query.data.split("_")
        await handle_user_action(query, action, tid)

async def handle_user_action(query, action, tid):
    user = requests.get(f"{DB_URL}/users/{tid}.json").json()
    if not user: return
    end_date = datetime.datetime.strptime(user['end_date'], "%Y-%m-%d %H:%M:%S")
    
    if action == "ext":
        new_end = end_date + datetime.timedelta(days=30)
        requests.patch(f"{DB_URL}/users/{tid}.json", json={"end_date": new_end.strftime("%Y-%m-%d %H:%M:%S")})
        await query.edit_message_text(f"✅ تم تمديد اشتراك {user['name']} لمدة 30 يوم إضافية.")
    elif action == "perm":
        requests.patch(f"{DB_URL}/users/{tid}.json", json={"end_date": "2099-01-01 00:00:00"})
        await query.edit_message_text(f"♾️ تم جعل اشتراك {user['name']} دائم (مدى الحياة).")
    elif action == "stop":
        requests.patch(f"{DB_URL}/users/{tid}.json", json={"end_date": "2020-01-01 00:00:00"})
        await query.edit_message_text(f"🚫 تم إيقاف اشتراك {user['name']} فوراً.")

async def manage_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    parts = update.message.text.split("_")
    if len(parts) < 2: return
    tid = parts[1]
    user = requests.get(f"{DB_URL}/users/{tid}.json").json()
    if not user:
        await update.message.reply_text("❌ لم يتم العثور على المشترك.")
        return
    text = (
        f"⚙️ *إدارة المشترك:* {user['name']}\n"
        f"🆔 المعرف: `{tid}`\n"
        f"الحالة: `{user.get('status', 'active')}`\n"
        f"📅 الانتهاء: `{user['end_date']}`\n"
        f"━━━━━━━━━━━━━━"
    )
    keyboard = [
        [InlineKeyboardButton("➕ تمديد 30 يوم", callback_data=f"action_ext_{tid}")],
        [InlineKeyboardButton("♾️ جعل الاشتراك دائم", callback_data=f"action_perm_{tid}")],
        [InlineKeyboardButton("🚫 حظر هذا المستخدم", callback_data=f"action_block_{tid}")],
        [InlineKeyboardButton("🗑️ حذف الاشتراك", callback_data=f"action_stop_{tid}")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# Add handle_user_action with block logic
async def handle_user_action(query, action, tid):
    user = requests.get(f"{DB_URL}/users/{tid}.json").json()
    if not user: return
    
    if action == "block":
        requests.patch(f"{DB_URL}/users/{tid}.json", json={"status": "blocked"})
        await query.edit_message_text(f"🚫 تم حظر `{user['name']}` بنجاح.")
        return

    end_date = datetime.datetime.strptime(user['end_date'], "%Y-%m-%d %H:%M:%S")
    if action == "ext":
        new_end = end_date + datetime.timedelta(days=30)
        requests.patch(f"{DB_URL}/users/{tid}.json", json={"end_date": new_end.strftime("%Y-%m-%d %H:%M:%S"), "status": "active"})
        await query.edit_message_text(f"✅ تم تمديد `{user['name']}` لـ 30 يوم إضافية.")
    elif action == "perm":
        requests.patch(f"{DB_URL}/users/{tid}.json", json={"end_date": "2099-01-01 00:00:00", "status": "active"})
        await query.edit_message_text(f"♾️ تم جعل اشتراك `{user['name']}` دائم.")
    elif action == "stop":
        requests.delete(f"{DB_URL}/users/{tid}.json")
        await query.edit_message_text(f"🗑️ تم حذف بيانات `{user['name']}` بالكامل.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.Regex(r'^/manage_\d+$'), manage_cmd))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    logging.info("Admin Pro Bot v18.5 is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
