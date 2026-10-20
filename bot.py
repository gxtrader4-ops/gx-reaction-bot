import os
import random
import time
from datetime import datetime
from threading import Thread
import requests
from flask import Flask
import telebot
from telebot import types

TOKEN = '8328274170:AAFrNNK1tapx67WjaADQUXjmRc9wbPSDZ1w'
ADMIN_IDS = [8419760844]
LOG_GROUP_ID = -1004452564086

SMM_API_URL = "https://1xpanel.com/api/v2"
SMM_API_KEY = "bdbedcf39f36fa030a9d4e56b0e1282e"
TELEGRAM_REACTION_SERVICE_ID = 1936

bot = telebot.TeleBot(TOKEN, parse_mode='Markdown')

user_balances = {}
banned_users = set()
total_orders_count = 0
auto_reaction_status = {}

app = Flask('')

@app.route('/')
def home():
    return "1X Panel SMM Auto-Reaction Bot is running 24/7!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

def send_smm_order(post_link, quantity):
    try:
        payload = {
            'key': SMM_API_KEY,
            'action': 'add',
            'service': TELEGRAM_REACTION_SERVICE_ID,
            'link': post_link,
            'quantity': quantity
        }
        response = requests.post(SMM_API_URL, data=payload, timeout=15)
        return response.json()
    except Exception as e:
        return {'error': str(e)}

def user_main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton('🚀 Telegram React + View'),
        types.KeyboardButton('⚡ Auto Reaction ON/OFF'),
        types.KeyboardButton('👤 Account'),
        types.KeyboardButton('💰 Wallet'),
        types.KeyboardButton('🛠️ Setup Status'),
        types.KeyboardButton('📞 Support')
    )
    return markup

def admin_main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton('⚙️ Admin Panel'),
        types.KeyboardButton('👥 All Users'),
        types.KeyboardButton('📢 Broadcast Message')
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if user_id in banned_users:
        bot.reply_to(message, "❌ দুঃখিত, আপনি এই বট ব্যবহারের জন্য ব্যানপ্রাপ্ত হয়েছেন।")
        return

    if user_id not in user_balances:
        user_balances[user_id] = 0.0

    if user_id in ADMIN_IDS:
        bot.send_message(message.chat.id, "👑 **WELCOME ADMIN**\n\nআপনার 1X Panel SMM অটো-রিঅ্যাকশন বট ফুল্লি লাইভ আছে!", reply_markup=admin_main_keyboard())
    else:
        bot.send_message(message.chat.id, "💎 **1X PANEL VIP AUTO-REACTION BOT**\n\nস্বাগতম আমাদের টেলিগ্রাম প্যানেলে!", reply_markup=user_main_keyboard())

@bot.message_handler(func=lambda message: message.text == '⚡ Auto Reaction ON/OFF')
def toggle_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🟢 Turn ON", callback_data="react_on"),
        types.InlineKeyboardButton("🔴 Turn OFF", callback_data="react_off")
    )
    bot.reply_to(message, "⚙️ অটো রিঅ্যাকশন সিস্টেম কন্ট্রোল প্যানেল:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["react_on", "react_off"])
def callback_toggle(call):
    chat_id = call.message.chat.id
    if call.data == "react_on":
        auto_reaction_status[chat_id] = True
        bot.answer_callback_query(call.id, "✅ অটো রিঅ্যাকশন চালু করা হয়েছে!", show_alert=True)
        bot.edit_message_text("🟢 অটো রিঅ্যাকশন বর্তমানে **ON** আছে।", chat_id=chat_id, message_id=call.message.message_id)
    else:
        auto_reaction_status[chat_id] = False
        bot.answer_callback_query(call.id, "❌ অটো রিঅ্যাকশন বন্ধ করা হয়েছে!", show_alert=True)
        bot.edit_message_text("🔴 অটো রিঅ্যাকশন বর্তমানে **OFF** আছে।", chat_id=chat_id, message_id=call.message.message_id)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    if user_id in banned_users:
        return

    text = message.text

    if text == '👤 Account':
        bot.reply_to(message, f"👤 **USER ACCOUNT**\n\n🆔 User ID: `{user_id}`\n💰 Balance: `$ {user_balances.get(user_id, 0.0)} USD`")
    elif text == '💰 Wallet':
        bot.reply_to(message, "💳 টপ আপ করতে বিন্যান্স পে ব্যবহার করুন এবং স্ক্রিনশট পাঠান।")
    elif text == '📞 Support':
        bot.reply_to(message, "💬 সাপোর্টের জন্য যোগাযোগ করুন।")
    elif text == '🚀 Telegram React + View':
        bot.reply_to(message, "📌 পোস্টের লিংক এবং পরিমাণ লিখে পাঠান (যেমন: `https://t.me/channel/123 100`)।")
    elif text == '🛠️ Setup Status':
        bot.reply_to(message, "🛠️ 1X Panel API: Active (`Service ID: 1936`)")
    elif text == '⚙️ Admin Panel' and user_id in ADMIN_IDS:
        bot.reply_to(message, f"👑 **ADMIN DASHBOARD**\nTotal Orders: `{total_orders_count}`", reply_markup=admin_main_keyboard())
    else:
        parts = text.split()
        if len(parts) >= 2 and ("t.me/" in parts[0] or "https://" in parts[0]):
            post_link = parts[0]
            try:
                quantity = int(parts[1])
            except ValueError:
                quantity = 100

            sent_notif = bot.reply_to(message, "⏳ অর্ডার প্রসেসিং হচ্ছে...")
            
            try:
                group_msg = bot.send_message(LOG_GROUP_ID, f"📌 **NEW ORDER [PROCESSING]**\nUser: `{user_id}`\nLink: `{post_link}`\nQty: `{quantity}`")
            except:
                group_msg = None

            api_response = send_smm_order(post_link, quantity)
            global total_orders_count
            total_orders_count += 1

            if 'order' in api_response:
                order_id = api_response['order']
                bot.edit_message_text(f"✅ **অর্ডার সম্পন্ন!**\nOrder ID: `{order_id}`", chat_id=message.chat.id, message_id=sent_notif.message_id)
                if group_msg:
                    bot.edit_message_text(f"🎉 **COMPLETED!**\nOrder ID: `{order_id}`\nLink: `{post_link}`", chat_id=LOG_GROUP_ID, message_id=group_msg.message_id)
            else:
                err = api_response.get('error', 'Unknown Error')
                bot.edit_message_text(f"❌ **ফেইল করেছে!**\nReason: `{err}`", chat_id=message.chat.id, message_id=sent_notif.message_id)
                if group_msg:
                    bot.edit_message_text(f"⚠️ **FAILED**\nReason: `{err}`", chat_id=LOG_GROUP_ID, message_id=group_msg.message_id)

if __name__ == '__main__':
    keep_alive()
    print("Bot is running...")
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
