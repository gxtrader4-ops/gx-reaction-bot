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
ADMIN_IDS = [8419760844]  # আপনার সঠিক এডমিন আইডি
LOG_GROUP_ID = -1004452564086

# 1X Panel অফিশিয়াল এপিআই কনফিগারেশন
API_URL = "https://1xpanel.com/api/v2"
API_KEY = "bdbedcf39f36fa030a9d4e56b0e1282e"
REACTION_SERVICE_ID = 1936

bot = telebot.TeleBot(TOKEN, parse_mode='Markdown')

# ডেটাবেস ও মেমোরি স্টোরেজ
user_coins = {}
banned_users = set()
total_orders_count = 0
group_setups = {}  # {chat_id: {"qty": quantity, "link": group_link, "active": True}}
waiting_for_group_link = {}
waiting_for_group_qty = {}
waiting_for_screenshot = {}
waiting_for_binance_change = {}

app = Flask('')

@app.route('/')
def home():
    return "GX Team 1X Panel SMM Bot is running 24/7!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# অফিশিয়াল পাইথন এপিআই কানেক্টর
def call_1xpanel_api(data):
    try:
        post_data = {'key': API_KEY}
        post_data.update(data)
        
        print(f"Sending API Request to 1XPanel: {post_data}")
        response = requests.post(API_URL, data=post_data, timeout=20)
        print(f"API Response Raw: {response.text}")
        
        return response.json()
    except Exception as e:
        print(f"API Connection Error: {e}")
        return {'error': str(e)}

def user_main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton('🚀 Telegram React + View'),
        types.KeyboardButton('💰 My Wallet & Coins'),
        types.KeyboardButton('💳 Topup (Binance Pay)'),
        types.KeyboardButton('📞 Support & Help')
    )
    return markup

def admin_main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton('⚙️ Admin Dashboard'),
        types.KeyboardButton('👥 All Users List'),
        types.KeyboardButton('💳 Change Binance UID'),
        types.KeyboardButton('📢 Broadcast Message')
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if user_id in banned_users:
        bot.reply_to(message, "❌ দুঃখিত, আপনি এই বট ব্যবহারের জন্য ব্যানপ্রাপ্ত হয়েছেন।")
        return

    if user_id not in user_coins:
        user_coins[user_id] = 50000  # টেস্টের জন্য ফ্রি কয়েন

    if user_id in ADMIN_IDS:
        bot.send_message(
            message.chat.id, 
            "👑 **WELCOME ADMIN (নিরব ভাই)**\n\nআপনার 1X Panel অটো-রিঅ্যাকশন বট ফুল্লি লাইভ আছে!", 
            reply_markup=admin_main_keyboard()
        )
    else:
        bot.send_message(
            message.chat.id, 
            "💎 **GX TEAM 1X PANEL VIP REACTION**\n\n"
            "স্বাগতম! নিচের মেনু থেকে অটো-রিঅ্যাকশন সেটআপ করুন:", 
            reply_markup=user_main_keyboard()
        )

@bot.message_handler(commands=['addcoin', 'removecoin', 'ban', 'unban'])
def handle_admin_commands(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = message.text.split()
    cmd = text[0]

    try:
        target_id = int(text[1])
        amount = int(text[2]) if len(text) > 2 else 0

        if cmd == '/addcoin':
            if target_id not in user_coins:
                user_coins[target_id] = 0
            user_coins[target_id] += amount
            bot.reply_to(message, f"✅ সফলভাবে ইউজার `{target_id}` এর একাউন্টে `{amount}` কয়েন যোগ করা হয়েছে।")
            try:
                bot.send_message(target_id, f"🎉 অভিনন্দন! আপনার একাউন্টে এডমিন `{amount}` কয়েন যোগ করেছেন।")
            except:
                pass
        elif cmd == '/removecoin':
            if target_id in user_coins:
                user_coins[target_id] = max(0, user_coins[target_id] - amount)
            bot.reply_to(message, f"⚠️ ইউজার `{target_id}` এর একাউন্ট থেকে `{amount}` কয়েন কেটে নেওয়া হয়েছে।")
        elif cmd == '/ban':
            banned_users.add(target_id)
            bot.reply_to(message, f"🚫 ইউজার `{target_id}` কে ব্যান করা হয়েছে।")
        elif cmd == '/unban':
            if target_id in banned_users:
                banned_users.remove(target_id)
            bot.reply_to(message, f"✅ ইউজার `{target_id}` কে আনব্যান করা হয়েছে।")
    except Exception as e:
        bot.reply_to(message, f"⚠️ সঠিক নিয়মে কমান্ড দিন:\nযেমন: `/addcoin [UserID] [Amount]` বা `/ban [UserID]`")

# ১. গ্রুপে নতুন পোস্ট ডিটেক্ট করার জন্য ডেডিকেটেড হ্যান্ডলার
@bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'], content_types=['text', 'photo', 'video', 'document', 'audio', 'animation', 'sticker'])
def handle_group_posts(message):
    global total_orders_count
    chat_id = message.chat.id
    print(f"Group message received from Chat ID: {chat_id}")

    # চেক করা এই গ্রুপটি সেটআপ করা আছে কি না
    if chat_id in group_setups and group_setups[chat_id].get("active", False):
        quantity = group_setups[chat_id].get("qty", 1000)

        # পোস্টের পারফেক্ট লিংক তৈরি
        if message.chat.username:
            post_link = f"https://t.me/{message.chat.username}/{message.message_id}"
        else:
            # প্রাইভেট বা সুপারগ্রুপের ক্ষেত্রে লিংক ফরম্যাট
            clean_chat_id = str(chat_id).replace('-100', '')
            post_link = f"https://t.me/c/{clean_chat_id}/{message.message_id}"
        
        print(f"Generated Post Link for API: {post_link} | Quantity: {quantity}")

        # লগ গ্রুপে পেন্ডিং মেসেজ পাঠানো
        try:
            pending_msg = bot.send_message(LOG_GROUP_ID, f"⏳ **ORDER PENDING [1X PANEL]**\nGroup ID: `{chat_id}`\nQty: `{quantity}`\nLink: `{post_link}`")
        except Exception as e:
            print(f"Failed to send pending log: {e}")
            pending_msg = None

        # 1X Panel API Call (`action: add`)
        api_response = call_1xpanel_api({
            'action': 'add',
            'service': REACTION_SERVICE_ID,
            'link': post_link,
            'quantity': quantity
        })
        total_orders_count += 1

        try:
            if isinstance(api_response, dict) and 'order' in api_response:
                order_id = api_response['order']
                success_text = f"🎉 **ORDER COMPLETED [1X PANEL]**\nOrder ID: `{order_id}`\nGroup ID: `{chat_id}`\nQty: `{quantity}`\nLink: `{post_link}`"
                if pending_msg:
                    bot.edit_message_text(success_text, chat_id=LOG_GROUP_ID, message_id=pending_msg.message_id)
                else:
                    bot.send_message(LOG_GROUP_ID, success_text)
            else:
                err_msg = api_response.get('error', 'Unknown Error') if isinstance(api_response, dict) else f'Response: {api_response}'
                fail_text = f"⚠️ **ORDER FAILED [1X PANEL]**\nReason: `{err_msg}`\nGroup ID: `{chat_id}`\nLink: `{post_link}`"
                if pending_msg:
                    bot.edit_message_text(fail_text, chat_id=LOG_GROUP_ID, message_id=pending_msg.message_id)
                else:
                    bot.send_message(LOG_GROUP_ID, fail_text)
        except Exception as e:
            print(f"Error updating log group: {e}")

# ২. প্রাইভেট চ্যাট ইউজার মেসেজ হ্যান্ডলার
@bot.message_handler(func=lambda message: message.chat.type == 'private')
def handle_private_messages(message):
    user_id = message.from_user.id
    if user_id in banned_users:
        return

    text = message.text if message.text else ""

    # পেমেন্ট স্ক্রিনশট আপলোড
    if user_id in waiting_for_screenshot and waiting_for_screenshot[user_id]:
        if message.content_type == 'photo':
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            temp_img_name = f"payment_{user_id}.jpg"
            with open(temp_img_name, "wb") as f:
                f.write(downloaded_file)

            for admin_id in ADMIN_IDS:
                caption_text = (
                    f"💳 **NEW TOPUP PAYMENT SCREENSHOT!**\n\n"
                    f"👤 **User Name:** {message.from_user.first_name}\n"
                    f"🆔 **User ID:** `{user_id}`\n"
                    f"🔗 **Username:** @{message.from_user.username if message.from_user.username else 'N/A'}\n\n"
                    f"👉 কয়েন যোগ করতে কমান্ড দিন:\n`/addcoin {user_id} [Amount]`"
                )
                with open(temp_img_name, "rb") as photo_f:
                    bot.send_photo(admin_id, photo_f, caption=caption_text, parse_mode='Markdown')
            os.remove(temp_img_name)

            bot.reply_to(message, "✅ পেমেন্ট স্ক্রিনশট সফলভাবে অ্যাডমিনের কাছে পাঠানো হয়েছে! চেক করে কয়েন এড করে দেওয়া হবে।")
            waiting_for_screenshot[user_id] = False
            return

    # গ্রুপ লিংক ইনপুট হ্যান্ডলিং
    if user_id in waiting_for_group_link and waiting_for_group_link[user_id]:
        group_input = text.strip()
        waiting_for_group_link[user_id] = False
        waiting_for_group_qty[user_id] = group_input

        bot.reply_to(message, "🔢 আপনি প্রতি পোস্টে কত রিঅ্যাকশন নিতে চান? (যেমন: `1000` বা `5000`) সংখ্যাটি লিখে পাঠান:")
        return

    # রিঅ্যাকশন পরিমাণ ইনপুট হ্যান্ডলিং (সেটআপ সম্পন্ন)
    if user_id in waiting_for_group_qty and waiting_for_group_qty[user_id]:
        try:
            qty = int(text.strip())
            group_input = waiting_for_group_qty[user_id]
            waiting_for_group_qty[user_id] = None

            # ইউজার যে গ্রুপে বট এডমিন দিছে এবং সেটআপ করতেছে, সেই চ্যাট আইডি রিকভার করার চেষ্টা
            # অথবা বর্তমান চ্যাটে সেটআপ সেভ করা
            target_chat_id = message.chat.id # অথবা গ্রুপ আইডি যদি ইউজার চ্যাটে দেয়
            group_setups[target_chat_id] = {"qty": qty, "link": group_input, "active": True}

            bot.reply_to(
                message, 
                f"✅ **অটো-রিঅ্যাকশন সফলভাবে সেটআপ হয়ে গেছে!**\n\n"
                f"📢 গ্রুপ/চ্যানেল: `{group_input}`\n"
                f"🔢 রিঅ্যাকশন পরিমাণ: `{qty}`\n"
                f"⚙️ স্ট্যাটাস: `Active`\n\n"
                f"এখন আপনার গ্রুপে পোস্ট করলেই 1X Panel থেকে অটো রিঅ্যাকশন চলে যাবে!"
            )
        except ValueError:
            bot.reply_to(message, "⚠️ দয়া করে একটি সঠিক সংখ্যা লিখুন (যেমন: `1000` বা `5000`)।")
        return

    if text == '💰 My Wallet & Coins':
        coins = user_coins.get(user_id, 0)
        bot.reply_to(message, f"💰 **MY WALLET & COINS**\n\n🆔 User ID: `{user_id}`\n🪙 Total Coins: `{coins} Coins`")
    
    elif text == '💳 Topup (Binance Pay)':
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("📸 Send Payment Screenshot", callback_data="send_screenshot"))
        
        topup_text = (
            f"💳 **BINANCE PAY TOPUP SYSTEM**\n\n"
            f"কয়েন টপ আপ করতে নিচের বাইন্যান্স আইডিতে ডলার পাঠান:\n\n"
            f"🔹 **Binance UID:** `1122595327`\n"
            f"🔹 **Rate:** `1 USD = 5000 Coins`\n\n"
            f"ডলার পাঠানোর পর সফল পেমেন্টের স্ক্রিনশট দিতে নিচের বাটনে ক্লিক করুন:"
        )
        bot.reply_to(message, topup_text, reply_markup=markup)
    
    elif text == '📞 Support & Help':
        bot.reply_to(message, "💬 কোনো সমস্যা হলে বা কয়েন এড করতে সরাসরি যোগাযোগ করুন: **@SUPPOR8TNIROB**")
    
    elif text == '🚀 Telegram React + View':
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🔗 Telegram Reaction One-Click Setup", callback_data="one_click_setup"))
        bot.reply_to(
            message, 
            "📌 **TELEGRAM AUTO-REACTION SETUP**\n\n"
            "নিচের বাটনে ক্লিক করে এক ক্লিকে আপনার গ্রুপ সেটআপ করুন:", 
            reply_markup=markup
        )
    
    elif text == '⚙️ Admin Dashboard' and user_id in ADMIN_IDS:
        bot.reply_to(message, f"👑 **ADMIN PANEL**\n\n📊 Total Orders: `{total_orders_count}`\n👥 Total Users: `{len(user_coins)}`\n🌐 API URL: `{API_URL}`", reply_markup=admin_main_keyboard())
    
    elif text == '👥 All Users List' and user_id in ADMIN_IDS:
        users_list = "\n".join([f"👤 ID: `{uid}` | Coins: `{coins}`" for uid, coins in user_coins.items()])
        bot.reply_to(message, f"👥 **REGISTERED USERS:**\n\n{users_list if users_list else 'কোনো ইউজার নেই।'}")
    
    elif text == '📢 Broadcast Message' and user_id in ADMIN_IDS:
        bot.reply_to(message, "📢 ব্রডকাস্ট করতে মেসেজটি লিখে পাঠান:")
    
    else:
        bot.reply_to(message, "❓ দুঃখিত, আমি আপনার কথা বুঝতে পারিনি। নিচের মেনু থেকে সঠিক অপশনটি সিলেক্ট করুন।", reply_markup=user_main_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def callback_handlers(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    data = call.data

    if data == "send_screenshot":
        waiting_for_screenshot[user_id] = True
        bot.answer_callback_query(call.id, "Send screenshot")
        bot.send_message(chat_id, "📸 আপনার বাইনান্স পেমেন্ট (`UID: 1122595327`) সফল হওয়ার স্ক্রিনশটটি ছবি হিসেবে চ্যাটে পাঠান।")
    
    elif data == "one_click_setup":
        waiting_for_group_link[user_id] = True
        bot.answer_callback_query(call.id, "Setup started")
        bot.send_message(chat_id, "📢 আপনার পাবলিক গ্রুপের লিংক বা ইউজারনেম পাঠান (যেমন: `@YourGroupName`):")

if __name__ == '__main__':
    keep_alive()
    print("1X Panel SMM VIP Reaction Bot is running 24/7...")
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
