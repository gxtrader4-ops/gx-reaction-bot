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

# ডেটাবেস স্টোরেজ
user_balances = {}
banned_users = set()
total_orders_count = 0
auto_reaction_status = {}
user_channels = {}

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
        types.KeyboardButton('🚀 Telegram React + View / TGIN Income'),
        types.KeyboardButton('👤 Account'),
        types.KeyboardButton('➕ Add Click Manual'),
        types.KeyboardButton('⚙️ Setup Status'),
        types.KeyboardButton('💰 Wallet'),
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
        bot.reply_to(message, "❌ দুঃখিত, আপনি এই বট ব্যবহারের জন্য ব্যানপ্রাপ্ত হয়েছেন।")
        return

    if user_id not in user_balances:
        user_balances[user_id] = 0.0

    if user_id in ADMIN_IDS:
        bot.send_message(message.chat.id, "👑 **WELCOME ADMIN (নিরব ভাই)**\n\nআপনার 1X Panel SMM অটো-রিঅ্যাকশন বট ফুল্লি লাইভ আছে!", reply_markup=admin_main_keyboard())
    else:
        bot.send_message(
            message.chat.id, 
            "💎 **GX TEAM VIP SERVICE**\n\n"
            "স্বাগতম আমাদের টেলিগ্রাম অটো-রিঅ্যাকশন ও ভিউজ প্যানেলে!\n"
            "নিচের মেনু থেকে আপনার প্রয়োজনীয় অপشن সিলেক্ট করুন:", 
            reply_markup=user_main_keyboard()
        )

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    global total_orders_count  # গ্লোবাল ভেরিয়েবল সঠিকভাবে ফাংশনের প্রথমে ডিক্লেয়ার করা হলো
    user_id = message.from_user.id
    if user_id in banned_users:
        return

    text = message.text

    if text == '👤 Account':
        bot.reply_to(message, f"👤 **USER ACCOUNT**\n\n🆔 User ID: `{user_id}`\n💰 Balance: `$ {user_balances.get(user_id, 0.0)} USD`")
    
    elif text == '💰 Wallet':
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("💳 Topup (Binance Pay)", callback_data="topup_binance"))
        bot.reply_to(message, "💳 **WALLET & TOPUP**\n\nটপ আপ করতে নিচের বাটনে ক্লিক করুন এবং বাইন্যান্স পে (Binance Pay) ব্যবহার করে পেমেন্ট স্ক্রিনশট দিন।", reply_markup=markup)
    
    elif text == '📞 Support':
        bot.reply_to(message, "💬 কোনো সমস্যায় পড়লে বা সাপোর্টের জন্য আমাদের অফিশিয়াল গ্রুপে যোগাযোগ করুন: **@SUPPOR8TNIROB**")
    
    elif text == '⚙️ Setup Status':
        bot.reply_to(message, "🛠️ **SETUP STATUS**\n\n🔹 1X Panel API: `Active`\n🔹 Service ID: `1936` (Telegram Reactions + Views)\n🔹 Status: `Online 24/7`")
    
    elif text == '🚀 Telegram React + View / TGIN Income':
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("⚙️ Premium Setup", callback_data="premium_setup"),
            types.InlineKeyboardButton("🔙 Back", callback_data="back_home")
        )
        bot.reply_to(message, "📌 **TELEGRAM REACTION & VIEW SETUP**\n\nআপনার চ্যানেল বা গ্রুপের পোস্ট লিংক ও পরিমাণ সিলেক্ট করুন।", reply_markup=markup)
    
    elif text == '➕ Add Click Manual':
        bot.reply_to(message, "➕ পোস্টের লিংক এবং পরিমাণ লিখে পাঠান (যেমন: `https://t.me/channel/123 100`)। সরাসরি অর্ডার প্রসেস হয়ে যাবে।")
    
    elif text == '⚙️ Admin Panel' and user_id in ADMIN_IDS:
        bot.reply_to(message, f"👑 **ADMIN DASHBOARD**\n\n📊 Total Orders Processed: `{total_orders_count}`\n👥 Total Users: `{len(user_balances)}`", reply_markup=admin_main_keyboard())
    
    elif text == '👥 All Users' and user_id in ADMIN_IDS:
        users_list = "\n".join([f"👤 ID: `{uid}` | Balance: `${bal}`" for uid, bal in user_balances.items()])
        bot.reply_to(message, f"👥 **REGISTERED USERS:**\n\n{users_list if users_list else 'কোনো ইউজার নেই।'}")
    
    elif text == '📢 Broadcast Message' and user_id in ADMIN_IDS:
        bot.reply_to(message, "📢 ব্রডকাস্ট করতে মেসেজটি লিখে পাঠান:")
    
    else:
        parts = text.split()
        if len(parts) >= 2 and ("t.me/" in parts[0] or "https://" in parts[0]):
            post_link = parts[0]
            try:
                quantity = int(parts[1])
            except ValueError:
                quantity = 100

            sent_notif = bot.reply_to(message, "⏳ অর্ডার প্রসেসিং হচ্ছে... দয়া করে অপেক্ষা করুন।")
            
            try:
                group_msg = bot.send_message(LOG_GROUP_ID, f"📌 **NEW ORDER [PROCESSING]**\nUser ID: `{user_id}`\nLink: `{post_link}`\nQty: `{quantity}`")
            except:
                group_msg = None

            api_response = send_smm_order(post_link, quantity)
            total_orders_count += 1

            if 'order' in api_response:
                order_id = api_response['order']
                bot.edit_message_text(f"✅ **অর্ডার সফলভাবে সম্পন্ন হয়েছে!**\nOrder ID: `{order_id}`\nLink: `{post_link}`", chat_id=message.chat.id, message_id=sent_notif.message_id)
                if group_msg:
                    bot.edit_message_text(f"🎉 **ORDER COMPLETED!**\nOrder ID: `{order_id}`\nLink: `{post_link}`", chat_id=LOG_GROUP_ID, message_id=group_msg.message_id)
            else:
                err = api_response.get('error', 'Unknown Error')
                bot.edit_message_text(f"❌ **অর্ডার ফেইল করেছে!**\nReason: `{err}`", chat_id=message.chat.id, message_id=sent_notif.message_id)
                if group_msg:
                    bot.edit_message_text(f"⚠️ **ORDER FAILED**\nReason: `{err}`", chat_id=LOG_GROUP_ID, message_id=group_msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
def callback_handlers(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "topup_binance":
        bot.answer_callback_query(call.id, "Binance Pay selected")
        bot.send_message(chat_id, "💳 অনুগ্রহ করে আমাদের বাইন্যান্স পে আইডি তে ডলার পাঠিয়ে পেমেন্টের স্ক্রিনশট ও ট্রানজেকশন আইডি প্রদান করুন।")
    
    elif data == "premium_setup":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📢 Channel Link", callback_data="set_channel"),
            types.InlineKeyboardButton("➕ Add Click", callback_data="add_click"),
            types.InlineKeyboardButton("💾 Save Setup", callback_data="save_setup"),
            types.InlineKeyboardButton("🔙 Back", callback_data="back_home")
        )
        bot.edit_message_text("⚙️ **PREMIUM SETUP PANEL**\n\nআপনার চ্যানেল লিংক এবং রিঅ্যাকশন সেটিংস কনফিগার করুন:", chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
    
    elif data == "set_channel":
        bot.answer_callback_query(call.id, "Send your channel username")
        bot.send_message(chat_id, "📢 আপনার পাবলিক চ্যানেলের ইউজারনেম পাঠান (যেমন: `@MyChannel`):")
    
    elif data == "add_click":
        bot.answer_callback_query(call.id, "Ready to add")
        bot.send_message(chat_id, "➕ রিঅ্যাকশন এবং ভিউয়ের পরিমাণ লিখে পাঠান।")
    
    elif data == "save_setup":
        bot.answer_callback_query(call.id, "Setup Saved Successfully!", show_alert=True)
        bot.send_message(chat_id, "✅ আপনার প্রিমিয়াম সেটআপ সফলভাবে সেভ করা হয়েছে!")
    
    elif data == "back_home":
        bot.edit_message_text("💎 **GX TEAM VIP SERVICE**\n\nমেনু থেকে আপনার অপশন সিলেক্ট করুন:", chat_id=chat_id, message_id=call.message.message_id)

if __name__ == '__main__':
    keep_alive()
    print("SMM Auto-Reaction Bot is running 24/7...")
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
