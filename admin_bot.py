import logging
import requests
import datetime
import string
import random
import os
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# --- CONFIG ---
BOT_TOKEN = "8746851791:AAFiYcUNitDjGfqG8_WMc70gLMaDQEUwlJk"
DB_URL = "https://pincfull-default-rtdb.firebaseio.com"
ADMIN_ID = 5917515784 # Your official ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- UTILS ---
def gen_code():
    return "PINC-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ هذا البوت مخصص للإدارة فقط.")
        return
    
    keyboard = [
        [KeyboardButton("➕ إضافة مشترك"), KeyboardButton("👥 المشتركين")],
        [KeyboardButton("🔍 بحث عن مشترك"), KeyboardButton("🔔 التنبيهات")]
    ]
...
    elif text == "🔔 التنبيهات":
        try:
            alerts = requests.get(f"{DB_URL}/web_alerts.json").json() or {}
            if not alerts:
                await update.message.reply_text("📭 لا يوجد تنبيهات تفعيل حالياً.")
                return
            msg = "🔔 <b>تنبيهات الدخول للموقع:</b>\n\n"
            # Show last 5
            sorted_alerts = list(alerts.values())[-5:]
            for al in reversed(sorted_alerts):
                msg += f"👤 {al['user']} (<code>{al['id']}</code>)\n⏰ الوقت: {al['time'].split('.')[0]}\n\n"
            await update.message.reply_text(msg, parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")
        return
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
        try:
            users = requests.get(f"{DB_URL}/users.json").json() or {}
            if not users:
                await update.message.reply_text("📭 لا يوجد مشتركون حالياً.")
                return
            msg = "👥 *إدارة جميع المشتركين (v19.1):*\n\n"
            for uid, data in users.items():
                st = data.get('status', 'active')
                if st == "pending": icon = "⏳ قيد التفعيل"
                elif st == "blocked": icon = "🚫 محظور"
                else:
                    expiry_str = data.get('end_date', '2020-01-01 00:00:00')
                    expiry = datetime.datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
                    icon = "✅ نشط" if expiry > datetime.datetime.now() else "⌛ منتهي"
                
                msg += f"👤 *{data['name']}* (`{uid}`)\nالحالة: {icon}\nالتحكم: /manage_{uid}\n\n"
            await update.message.reply_text(msg, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ في جلب البيانات: {e}")
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
        try:
            name = html.escape(text.strip())
            tid = html.escape(context.user_data.get('temp_id'))
            
            code = gen_code()
            start_date = datetime.datetime.now()
            end_date = start_date + datetime.timedelta(days=30)
            
            # 1. Save Code
            requests.put(f"{DB_URL}/codes/{code}.json", json={
                "name": name, 
                "status": "unused", 
                "target_id": tid,
                "created_at": str(start_date)
            })
            
            # 2. Save User
            requests.put(f"{DB_URL}/users/{tid}.json", json={
                "name": name,
                "status": "pending",
                "start_date": str(start_date),
                "end_date": str(end_date),
                "code": code
            })
            
            # Message (HTML MODE)
            msg = (
                f"💎 <b>تم تفعيل اشتراكك في PincFull Pro الاستثنائي</b> 💎\n\n"
                f"👤 <b>اسم المشترك:</b> <code>{name}</code>\n"
                f"🆔 <b>معرف الدخول:</b> <code>{tid}</code>\n"
                f"🔑 <b>كود التفعيل (بوت + موقع):</b>\n<code>{code}</code>\n\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📅 <b>تاريخ البدء:</b> <code>{start_date.strftime('%Y-%m-%d')}</code>\n"
                f"⌛ <b>تاريخ الانتهاء:</b> <code>{end_date.strftime('%Y-%m-%d')}</code>\n\n"
                f"🤖 <b>رابط البوت:</b> @panic2_bot\n"
                f"🌐 <b>رابط الموقع:</b> https://pincfull.web.app"
            )
            await update.message.reply_text("✅ تم تسجيل المشترك بنجاح!")
            await update.message.reply_text(msg, parse_mode='HTML')
            context.user_data['state'] = None
        except Exception as e:
            await update.message.reply_text(f"❌ فشل التسجيل: {e}")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("action_"):
        _, action, tid = query.data.split("_")
        await handle_user_action(query, action, tid)

async def handle_user_action(query, action, tid):
    try:
        user = requests.get(f"{DB_URL}/users/{tid}.json").json()
        if not user:
            await query.edit_message_text("❌ لم يتم العثور على المستخدم في قاعدة البيانات.")
            return
            
        if action == "block":
            requests.patch(f"{DB_URL}/users/{tid}.json", json={"status": "blocked"})
            await query.edit_message_text(f"🚫 تم حظر `{user['name']}` بنجاح.")
        elif action == "ext":
            expiry_str = user.get('end_date', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            end_date = datetime.datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
            new_end = end_date + datetime.timedelta(days=30)
            requests.patch(f"{DB_URL}/users/{tid}.json", json={"end_date": new_end.strftime("%Y-%m-%d %H:%M:%S"), "status": "active"})
            await query.edit_message_text(f"✅ تم تمديد `{user['name']}` لـ 30 يوم.")
        elif action == "perm":
            requests.patch(f"{DB_URL}/users/{tid}.json", json={"end_date": "2099-01-01 00:00:00", "status": "active"})
            await query.edit_message_text(f"♾️ تم جعل اشتراك `{user['name']}` دائم.")
        elif action == "stop":
            requests.delete(f"{DB_URL}/users/{tid}.json")
            await query.edit_message_text(f"🗑️ تم حذف بيانات `{user['name']}`.")
    except Exception as e:
        await query.edit_message_text(f"❌ خطأ: {e}")

async def manage_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    parts = update.message.text.split("_")
    if len(parts) < 2: return
    tid = parts[1]
    
    try:
        user = requests.get(f"{DB_URL}/users/{tid}.json").json()
        if not user:
            await update.message.reply_text("❌ المستخدم غير موجود.")
            return
            
        text = (
            f"⚙️ <b>إدارة المشترك:</b> {user['name']}\n"
            f"🆔 المعرف: <code>{tid}</code>\n"
            f"الحالة: <code>{user.get('status', 'pending')}</code>\n"
            f"📅 ينتهي: <code>{user.get('end_date', 'N/A')}</code>\n"
            f"━━━━━━━━━━━━━━"
        )
        keyboard = [
            [InlineKeyboardButton("➕ تمديد 30 يوم", callback_data=f"action_ext_{tid}")],
            [InlineKeyboardButton("♾️ دائم", callback_data=f"action_perm_{tid}"), InlineKeyboardButton("🚫 حظر", callback_data=f"action_block_{tid}")],
            [InlineKeyboardButton("🗑️ حذف نهائي", callback_data=f"action_stop_{tid}")]
        ]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.Regex(r'^/manage_\d+$'), manage_cmd))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    
    print("✅ Admin Pro Bot is starting...")
    app.run_polling()

if __name__ == '__main__':
    main()
