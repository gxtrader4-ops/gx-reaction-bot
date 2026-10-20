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
ADMIN_IDS = [8419760844]  # আপনার সঠিক এডমিন আইডি (শেষের অংশ 844)
LOG_GROUP_ID = -1004452564086

# গ্লোবাল কনফিগারেশন (এডমিন প্যানেল থেকে পরিবর্তনযোগ্য)
bot_config = {
    "binance_uid": "1122595327",
    "reaction_service_id": 1936
}

SMM_API_URL = "https://1xpanel.com/api/v2"
SMM_API_KEY = "bdbedcf39f36fa030a9d4e56b0e1282e"

bot = telebot.TeleBot(TOKEN, parse_mode='Markdown')

# ডেটাবেস ও মেমোরি স্টোরেজ
user_coins = {}
banned_users = set()
total_orders_count = 0
auto_reaction_status = {}  # {chat_id: True/False}
chat_reaction_quantities = {}  # {chat_id: quantity}
waiting_for_channel = {}
waiting_for_quantity = {}
waiting_for_screenshot = {}
waiting_for_binance_change = {}

app = Flask('')

@app.route('/')
def home():
    return "GX Team Auto-Reaction & SMM Bot is running 24/7!"

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
            'service': bot_config["reaction_service_id"],
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
        types.KeyboardButton('⚡ Auto Reaction Control'),
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
        user_coins[user_id] = 100000  # শুরুর জন্য ফ্রি কয়েন উপহার

    if user_id in ADMIN_IDS:
        bot.send_message(message.chat.id, "👑 **WELCOME ADMIN (নিরব ভাই)**\n\nআপনার ফুল অটো-রিঅ্যাকশন বট ফুল্লি লাইভ আছে!", reply_markup=admin_main_keyboard())
    else:
        bot.send_message(
            message.chat.id, 
            "💎 **GX TEAM VIP AUTO-REACTION BOT**\n\n"
            "স্বাগতম! যেকোনো গ্রুপে বটকে এডমিন দিয়ে নিচের মেনু থেকে অটো-রিঅ্যাকশন সেটআপ করুন:", 
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

@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document', 'audio'])
def handle_all_incoming(message):
    global total_orders_count
    user_id = message.from_user.id
    if user_id in banned_users:
        return

    # ১. যদি গ্রুপে কোনো নতুন পোস্ট/মেসেজ আসে এবং অটো-রিঅ্যাকশন ON থাকে
    if message.chat.type in ['group', 'supergroup']:
        chat_id = message.chat.id
        if auto_reaction_status.get(chat_id, False):
            # পোস্টের পারফেক্ট লিংক তৈরি (পাবলিক বা প্রাইভেট চ্যানেলের ক্ষেত্রে)
            if message.chat.username:
                post_link = f"https://t.me/{message.chat.username}/{message.message_id}"
            else:
                post_link = f"https://t.me/c/{str(chat_id).replace('-100', '')}/{message.message_id}"
            
            quantity = chat_reaction_quantities.get(chat_id, 100)
            
            # এসমিএম অর্ডার পাঠানো
            api_response = send_smm_order(post_link, quantity)
            total_orders_count += 1

            try:
                if 'order' in api_response:
                    bot.send_message(LOG_GROUP_ID, f"🎉 **AUTO REACTION COMPLETED!**\nOrder ID: `{api_response['order']}`\nGroup: `{chat_id}`\nQty: `{quantity}`\nLink: `{post_link}`")
                else:
                    bot.send_message(LOG_GROUP_ID, f"⚠️ **AUTO REACTION FAILED**\nReason: `{api_response.get('error', 'Unknown')}`\nGroup: `{chat_id}`")
            except:
                pass
        return

    # ২. প্রাইভেট চ্যাট ইউজার টেক্সট হ্যান্ডলিং
    text = message.text if message.text else ""

    # বাইনান্স ইউআইডি পরিবর্তন (এডমিন)
    if user_id in ADMIN_IDS and waiting_for_binance_change.get(user_id, False):
        bot_config["binance_uid"] = text.strip()
        waiting_for_binance_change[user_id] = False
        bot.reply_to(message, f"✅ সফলভাবে বাইনান্স ইউআইডি পরিবর্তন করে রাখা হলো: `{bot_config['binance_uid']}`")
        return

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

    # রিঅ্যাকশন পরিমাণ ইনপুট
    if user_id in waiting_for_quantity and waiting_for_quantity[user_id]:
        try:
            qty = int(text.strip())
            chat_to_set = waiting_for_quantity[user_id]
            chat_reaction_quantities[chat_to_set] = qty
            waiting_for_quantity[user_id] = False
            bot.reply_to(message, f"✅ সফলভাবে রিঅ্যাকশনের পরিমাণ `{qty}` সেট করা হয়েছে!")
        except ValueError:
            bot.reply_to(message, "⚠️ দয়া করে একটি সঠিক সংখ্যা লিখুন (যেমন: `100` বা `500`)।")
        return

    if text == '💰 My Wallet & Coins':
        coins = user_coins.get(user_id, 0)
        bot.reply_to(message, f"💰 **MY WALLET & COINS**\n\n🆔 User ID: `{user_id}`\n🪙 Total Coins: `{coins} Coins`\n\n_(১ ডলারে ৫০০০ কয়েন প্যাক চালু আছে)_")
    
    elif text == '💳 Topup (Binance Pay)':
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("📸 Send Payment Screenshot", callback_data="send_screenshot"))
        
        topup_text = (
            f"💳 **BINANCE PAY TOPUP SYSTEM**\n\n"
            f"কয়েন টপ আপ করতে নিচের বাইন্যান্স আইডিতে ডলার পাঠান:\n\n"
            f"🔹 **Binance UID:** `{bot_config['binance_uid']}`\n"
            f"🔹 **Rate:** `1 USD = 5000 Coins`\n\n"
            f"ডলার পাঠানোর পর সফল পেমেন্টের স্ক্রিনশট দিতে নিচের বাটনে ক্লিক করুন:"
        )
        bot.reply_to(message, topup_text, reply_markup=markup)
    
    elif text == '📞 Support & Help':
        bot.reply_to(message, "💬 কোনো সমস্যা হলে বা কয়েন এড করতে সরাসরি যোগাযোগ করুন: **@SUPPOR8TNIROB**")
    
    elif text == '🚀 Telegram React + View':
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("⚙️ Setup Auto-Reaction in Group", callback_data="setup_group_guide"),
            types.InlineKeyboardButton("🔙 Back to Home", callback_data="back_home")
        )
        bot.reply_to(
            message, 
            "📌 **TELEGRAM AUTO-REACTION SETUP**\n\n"
            "১. প্রথমে আপনার গ্রুপে বটকে **Admin** দিন।\n"
            "২. নিচের বাটনে ক্লিক করে অটো-রিঅ্যাকশন কনফিগার করুন।", 
            reply_markup=markup
        )
    
    elif text == '⚡ Auto Reaction Control':
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🟢 Turn ON", callback_data="react_on"),
            types.InlineKeyboardButton("🔴 Turn OFF", callback_data="react_off"),
            types.InlineKeyboardButton("📊 Check Status", callback_data="react_status")
        )
        bot.reply_to(message, "⚙️ **AUTO REACTION CONTROL PANEL**\n\nআপনার গ্রুপের অটো-রিঅ্যাকশন সিস্টেম এখান থেকে অন বা অফ করুন:", reply_markup=markup)
    
    elif text == '⚙️ Admin Dashboard' and user_id in ADMIN_IDS:
        bot.reply_to(message, f"👑 **ADMIN PANEL**\n\n📊 Total Orders: `{total_orders_count}`\n👥 Total Users: `{len(user_coins)}`\n💳 Current Binance UID: `{bot_config['binance_uid']}`", reply_markup=admin_main_keyboard())
    
    elif text == '👥 All Users List' and user_id in ADMIN_IDS:
        users_list = "\n".join([f"👤 ID: `{uid}` | Coins: `{coins}`" for uid, coins in user_coins.items()])
        bot.reply_to(message, f"👥 **REGISTERED USERS:**\n\n{users_list if users_list else 'কোনো ইউজার নেই।'}")
    
    elif text == '💳 Change Binance UID' and user_id in ADMIN_IDS:
        waiting_for_binance_change[user_id] = True
        bot.reply_to(message, f"💳 বর্তমান বাইনান্স ইউআইডি: `{bot_config['binance_uid']}`\n\nনতুন বাইনান্স ইউআইডি লিখে পাঠান:")
    
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
        bot.send_message(chat_id, f"📸 আপনার বাইনান্স পেমেন্ট (`UID: {bot_config['binance_uid']}`) সফল হওয়ার স্ক্রিনশটটি ছবি হিসেবে চ্যাটে পাঠান।")
    
    elif data == "setup_group_guide":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🟢 Turn ON", callback_data="react_on"),
            types.InlineKeyboardButton("⚙️ Set Quantity", callback_data="set_qty")
        )
        bot.edit_message_text(
            "📌 **GROUP SETUP GUIDE:**\n\n"
            "১. আপনার গ্রুপে আমাদের বটকে **Admin** করুন।\n"
            "২. নিচের বাটন থেকে রিঅ্যাকশন **ON** করুন এবং পরিমাণ সেট করুন।\n"
            "ব্যাস! এরপর গ্রুপে যত পোস্ট করবেন, অটো রিঅ্যাকশন চলে যাবে!",
            chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup
        )
    
    elif data == "react_on":
        # এখানে বর্তমান চ্যাট বা গ্রুপের জন্য অন করা
        auto_reaction_status[chat_id] = True
        bot.answer_callback_query(call.id, "✅ অটো রিঅ্যাকশন চালু করা হয়েছে!", show_alert=True)
        bot.edit_message_text("🟢 অটো রিঅ্যাকশন বর্তমানে এই চ্যাটে **ON** আছে।", chat_id=chat_id, message_id=call.message.message_id)
    
    elif data == "react_off":
        auto_reaction_status[chat_id] = False
        bot.answer_callback_query(call.id, "❌ অটো রিঅ্যাকশন বন্ধ করা হয়েছে!", show_alert=True)
        bot.edit_message_text("🔴 অটো রিঅ্যাকশন বর্তমানে এই চ্যাটে **OFF** আছে।", chat_id=chat_id, message_id=call.message.message_id)
    
    elif data == "react_status":
        status = auto_reaction_status.get(chat_id, False)
        qty = chat_reaction_quantities.get(chat_id, 100)
        state_text = "🟢 ON" if status else "🔴 OFF"
        bot.answer_callback_query(call.id, f"Status: {state_text} | Qty: {qty}", show_alert=True)
    
    elif data == "set_qty":
        waiting_for_quantity[user_id] = chat_id
        bot.answer_callback_query(call.id, "Enter quantity")
        bot.send_message(chat_id, "🔢 আপনি প্রতি পোস্টে কতটি রিঅ্যাকশন নিতে চান? সংখ্যাটি লিখে পাঠান (যেমন: `150`):")
    
    elif data == "back_home":
        bot.edit_message_text("💎 **GX TEAM VIP AUTO-REACTION BOT**\n\nমেনু থেকে অপশন সিলেক্ট করুন:", chat_id=chat_id, message_id=call.message.message_id)

if __name__ == '__main__':
    keep_alive()
    print("SMM VIP Reaction Bot is running 24/7...")
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
