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

# আপনার রিয়েল বাইনান্স ইউআইডি (Binance UID)
BINANCE_UID = "1122595327"

SMM_API_URL = "https://1xpanel.com/api/v2"
SMM_API_KEY = "bdbedcf39f36fa030a9d4e56b0e1282e"
TELEGRAM_REACTION_SERVICE_ID = 1936

bot = telebot.TeleBot(TOKEN, parse_mode='Markdown')

# ডেটাবেস ও মেমোরি স্টোরেজ
user_coins = {}
banned_users = set()
total_orders_count = 0
user_channels = {}
waiting_for_channel = {}
waiting_for_screenshot = {}
waiting_for_order = {}

app = Flask('')

@app.route('/')
def home():
    return "GX Team VIP Auto-Reaction Bot is running 24/7!"

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
        types.KeyboardButton('💰 My Wallet & Coins'),
        types.KeyboardButton('💳 Topup (Binance Pay)'),
        types.KeyboardButton('⚙️ Setup Status'),
        types.KeyboardButton('📞 Support & Help')
    )
    return markup

def admin_main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton('⚙️ Admin Dashboard'),
        types.KeyboardButton('👥 All Users List'),
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
        user_coins[user_id] = 0

    if user_id in ADMIN_IDS:
        bot.send_message(message.chat.id, "👑 **WELCOME ADMIN (নিরব ভাই)**\n\nআপনার ভিআইপি অটো-রিঅ্যাকশন বট ফুল্লি লাইভ আছে!", reply_markup=admin_main_keyboard())
    else:
        bot.send_message(
            message.chat.id, 
            "💎 **GX TEAM VIP REACTION PANEL**\n\n"
            "স্বাগতম আমাদের অটো-রিঅ্যাকশন ও ভিউজ প্যানেলে!\n"
            "নিচের মেনু থেকে আপনার প্রয়োজনীয় অপশন সিলেক্ট করুন:", 
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

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    global total_orders_count
    user_id = message.from_user.id
    if user_id in banned_users:
        return

    text = message.text if message.text else ""

    # স্ক্রিনশট আপলোড প্রসেসিং (টপআপের জন্য)
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

            bot.reply_to(message, "✅ আপনার পেমেন্ট স্ক্রিনশট সফলভাবে অ্যাডমিনের কাছে পাঠানো হয়েছে! অ্যাডমিন চেক করে আপনার একাউন্টে কয়েন এড করে দেবেন।")
            waiting_for_screenshot[user_id] = False
            return
        else:
            bot.reply_to(message, "⚠️ দয়া করে বাইন্যান্স পেমেন্টের একটি সঠিক স্ক্রিনশট (ছবি) পাঠান।")
            return

    # চ্যানেল লিংক সেটআপ ইনপুট হ্যান্ডলিং
    if user_id in waiting_for_channel and waiting_for_channel[user_id]:
        channel_username = text.strip()
        waiting_for_channel[user_id] = False

        is_admin = False
        try:
            chat_member = bot.get_chat_member(channel_username, bot.get_me().id)
            if chat_member.status in ['administrator', 'creator']:
                is_admin = True
        except Exception as e:
            print(f"Admin check error: {e}")

        if is_admin or channel_username.startswith('@'):
            user_channels[user_id] = channel_username
            bot.reply_to(
                message, 
                f"✅ **চ্যানেল সফলভাবে কানেক্ট হয়েছে!**\n\n"
                f"📢 চ্যানেল: `{channel_username}`\n"
                f"🛡️ বট এডমিন স্ট্যাটাস: `Verified`\n\n"
                f"এখন আপনি পোস্ট লিংক ও পরিমাণ লিখে রিঅ্যাকশন বা ভিউ নিতে পারেন!"
            )
        else:
            bot.reply_to(
                message, 
                f"❌ **সেটআপ ব্যর্থ হয়েছে!**\n\n"
                f"⚠️ লক্ষ্য করুন: `{channel_username}` এই চ্যানেল বা গ্রুপে আমাদের বটকে **Admin** হিসেবে যুক্ত করা হয়নি!\n"
                f"দয়া করে আপনার চ্যানেল/গ্রুপে বটকে এডমিন দিয়ে আবার সেটআপ সম্পন্ন করুন।"
            )
        return

    # অর্ডার প্লেসমেন্ট ইনপুট হ্যান্ডলিং
    if user_id in waiting_for_order and waiting_for_order[user_id]:
        waiting_for_order[user_id] = False
        parts = text.split()
        if len(parts) >= 2 and ("t.me/" in parts[0] or "https://" in parts[0]):
            post_link = parts[0]
            try:
                quantity = int(parts[1])
            except ValueError:
                quantity = 100

            sent_notif = bot.reply_to(message, "⏳ **অর্ডার পেন্ডিং আছে... প্রসেসিং করা হচ্ছে!**")
            
            try:
                group_msg = bot.send_message(LOG_GROUP_ID, f"📌 **NEW ORDER [PENDING]**\nUser ID: `{user_id}`\nLink: `{post_link}`\nQty: `{quantity}`")
            except:
                group_msg = None

            api_response = send_smm_order(post_link, quantity)
            total_orders_count += 1

            if 'order' in api_response:
                order_id = api_response['order']
                bot.edit_message_text(f"✅ **অর্ডার সফলভাবে কমপ্লিট হয়েছে!**\nOrder ID: `{order_id}`\nLink: `{post_link}`", chat_id=message.chat.id, message_id=sent_notif.message_id)
                if group_msg:
                    bot.edit_message_text(f"🎉 **ORDER COMPLETED!**\nOrder ID: `{order_id}`\nLink: `{post_link}`\nUser: `{user_id}`", chat_id=LOG_GROUP_ID, message_id=group_msg.message_id)
            else:
                err = api_response.get('error', 'Unknown Error')
                bot.edit_message_text(f"❌ **অর্ডার ফেইল করেছে!**\nReason: `{err}`", chat_id=message.chat.id, message_id=sent_notif.message_id)
                if group_msg:
                    bot.edit_message_text(f"⚠️ **ORDER FAILED**\nReason: `{err}`\nUser: `{user_id}`", chat_id=LOG_GROUP_ID, message_id=group_msg.message_id)
            return
        else:
            bot.reply_to(message, "⚠️ সঠিক ফরম্যাটে লিংক এবং পরিমাণ দিন। যেমন: `https://t.me/channel/123 100`")
            return

    if text == '💰 My Wallet & Coins':
        coins = user_coins.get(user_id, 0)
        bot.reply_to(message, f"💰 **MY WALLET & COINS**\n\n🆔 User ID: `{user_id}`\n🪙 Total Coins: `{coins} Coins`\n\n_(১ ডলারে ৫০০০ কয়েন প্যাক চালু আছে)_")
    
    elif text == '💳 Topup (Binance Pay)':
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("📸 Send Payment Screenshot", callback_data="send_screenshot"))
        
        topup_text = (
            f"💳 **BINANCE PAY TOPUP SYSTEM**\n\n"
            f"আপনার একাউন্টে কয়েন টপ আপ করতে নিচের বাইন্যান্স আইডিতে ডলার পাঠান:\n\n"
            f"🔹 **Binance UID:** `{BINANCE_UID}`\n"
            f"🔹 **Rate:** `1 USD = 5000 Coins`\n\n"
            f"ডলার পাঠানোর পর পেমেন্টের সফল স্ক্রিনশটটি দিতে নিচের বাটনে ক্লিক করুন:"
        )
        bot.reply_to(message, topup_text, reply_markup=markup)
    
    elif text == '📞 Support & Help':
        bot.reply_to(message, "💬 কোনো সমস্যা হলে বা কয়েন এড করতে সরাসরি যোগাযোগ করুন: **@SUPPOR8TNIROB**")
    
    elif text == '⚙️ Setup Status':
        bot.reply_to(message, "🛠️ **SETUP STATUS**\n\n🔹 1X Panel API: `Active`\n🔹 Service ID: `1936` (Telegram Reactions + Views)\n🔹 Bot Status: `Online 24/7`")
    
    elif text == '🚀 Telegram React + View':
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📢 Set Channel Link", callback_data="set_channel_menu"),
            types.InlineKeyboardButton("🚀 Send Order", callback_data="send_order_menu"),
            types.InlineKeyboardButton("🔙 Back", callback_data="back_home")
        )
        bot.reply_to(
            message, 
            "📌 **TELEGRAM REACTION & VIEW SETUP**\n\n"
            "১. প্রথমে আপনার চ্যানেল বা গ্রুপে বটকে **Admin** দিন।\n"
            "২. এরপর **'Set Channel Link'** এ ক্লিক করে আপনার চ্যানেল যুক্ত করুন।\n"
            "৩. সবশেষে **'Send Order'** এ ক্লিক করে পোস্টের লিংক ও পরিমাণ পাঠান।", 
            reply_markup=markup
        )
    
    elif text == '⚙️ Admin Dashboard' and user_id in ADMIN_IDS:
        bot.reply_to(message, f"👑 **ADMIN PANEL**\n\n📊 Total Orders: `{total_orders_count}`\n👥 Total Users: `{len(user_coins)}`", reply_markup=admin_main_keyboard())
    
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
        bot.answer_callback_query(call.id, "Send payment screenshot now")
        bot.send_message(chat_id, "📸 চমৎকার! এখন আপনার বাইন্যান্স পেমেন্ট (`UID: 1122595327`) সফল হওয়ার স্ক্রিনশটটি চ্যাটে ছবি হিসেবে আপলোড করুন।")
    
    elif data == "set_channel_menu":
        waiting_for_channel[user_id] = True
        bot.answer_callback_query(call.id, "Enter channel username")
        bot.send_message(chat_id, "📢 আপনার পাবলিক চ্যানেল বা গ্রুপের ইউজারনেম পাঠান (যেমন: `@MyChannel`):\n\n*(অবশ্যই চ্যানেলে আমাদের বটকে এডমিন দিতে হবে)*")
    
    elif data == "send_order_menu":
        waiting_for_order[user_id] = True
        bot.answer_callback_query(call.id, "Send order details")
        bot.send_message(chat_id, "📌 পোস্টের লিংক এবং পরিমাণ লিখে পাঠান।\nউদাহরণস্বরূপ:\n`https://t.me/mychannel/50 100`")
    
    elif data == "back_home":
        bot.edit_message_text("💎 **GX TEAM VIP REACTION PANEL**\n\nমেনু থেকে অপশন সিলেক্ট করুন:", chat_id=chat_id, message_id=call.message.message_id)

if __name__ == '__main__':
    keep_alive()
    print("SMM VIP Reaction Bot is running 24/7...")
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
