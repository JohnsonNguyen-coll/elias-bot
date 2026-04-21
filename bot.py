import os
import httpx
import logging
import asyncio
from dotenv import load_dotenv
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL") 
PORT = int(os.environ.get("PORT", 10000)) # Render thường dùng 10000

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Shortcut tokens
SHORTCUTS = {
    "bob": "0x21E325B059Cd83d4037C82F0F5998Ba2dF3d7777",
    "anago": "0x3Ec7310937281CA4Bf89D5bB11704bE9b7ff7777",
    "chog": "0x350035555E10d9AfAF1566AaebfCeD5BA6C27777",
    "emonad": "0x81A224F8A62f52BdE942dBF23A56df77A10b7777",
    "nads": "0x39B9E06f226FF6D7500c870B82333AACbD2F7777",
    "moncock": "0x405b6330e213DED490240CbcDD64790806827777",
    "shramp": "0x42a4aA89864A794dE135B23C6a8D2E05513d7777",
}

# --- DEXSCREENER LOGIC ---
async def search_token_on_dex(query: str):
    url = f"https://api.dexscreener.com/latest/dex/search?q={query}"
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, timeout=10)
            data = res.json()
            pairs = data.get("pairs", [])
            if not pairs: return None
            pairs.sort(key=lambda x: float(x.get("volume", {}).get("h24", 0) or 0), reverse=True)
            return pairs[0]
        except Exception as e:
            logging.error(f"Error searching token: {e}")
            return None

async def get_token_by_ca(ca: str):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, timeout=10)
            data = res.json()
            pairs = data.get("pairs", [])
            if not pairs: return None
            pairs.sort(key=lambda x: float(x.get("volume", {}).get("h24", 0) or 0), reverse=True)
            return pairs[0]
        except Exception as e:
            logging.error(f"Error fetching token by CA: {e}")
            return None

def format_number(n):
    if n is None: return "N/A"
    n = float(n)
    if n >= 1_000_000_000: return f"${n/1_000_000_000:.2f}B"
    elif n >= 1_000_000: return f"${n/1_000_000:.2f}M"
    elif n >= 1_000: return f"${n/1_000:.2f}K"
    return f"${n:.2f}"

def format_price(p):
    if p is None: return "N/A"
    p = float(p)
    if p == 0: return "$0.00"
    if p < 0.000001: return f"${p:.10f}"
    elif p < 0.01: return f"${p:.6f}"
    return f"${p:.4f}"

def format_pair(pair: dict) -> str:
    base = pair.get("baseToken", {})
    name = base.get("name", "Unknown")
    symbol = base.get("symbol", "???")
    price_usd = pair.get("priceUsd")
    change = pair.get("priceChange", {})
    volume_24h = pair.get("volume", {}).get("h24")
    liquidity = pair.get("liquidity", {}).get("usd")
    fdv = pair.get("fdv")
    dex = pair.get("dexId", "unknown").capitalize()
    chain = pair.get("chainId", "unknown").capitalize()
    ca = base.get("address", "N/A")
    
    def emoji(v):
        try: return "🟢" if float(v) > 0 else "🔴"
        except: return "⚪"

    return (
        f"🪙 *{name}* (${symbol})\n"
        f"⛓ `{chain}` • 🏦 `{dex}`\n\n"
        f"💵 *Giá:* `{format_price(price_usd)}`\n\n"
        f"📈 *Biến động:*\n"
        f"  {emoji(change.get('h1',0))} 1h: `{float(change.get('h1',0)):+.2f}%`\n"
        f"  {emoji(change.get('h6',0))} 6h: `{float(change.get('h6',0)):+.2f}%`\n"
        f"  {emoji(change.get('h24',0))} 24h: `{float(change.get('h24',0)):+.2f}%`\n\n"
        f"📊 *Volume 24h:* `{format_number(volume_24h)}`\n"
        f"💧 *Thanh khoản:* `{format_number(liquidity)}`\n"
        f"🏷 *FDV:* `{format_number(fdv)}`\n\n"
        f"📄 *CA:* `{ca}`"
    )

# --- BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🚀 *Meme Coin Price Bot (Webhook)*\n\n"
        "📌 *Lệnh:* /p <coin>, /ca <address>\n"
        "⚡️ *Lệnh tắt:* /bob, /anago, /chog, /emonad, /nads, /moncock, /shramp"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ VD: `/p PEPE`", parse_mode="Markdown")
        return
    query = " ".join(context.args)
    msg = await update.message.reply_text(f"🔍 Đang tìm *{query.upper()}*...", parse_mode="Markdown")
    pair = await search_token_on_dex(query)
    if not pair:
        await msg.edit_text(f"❌ Không tìm thấy *{query.upper()}*.")
        return
    await msg.edit_text(format_pair(pair), parse_mode="Markdown", disable_web_page_preview=True)

async def shortcut_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd = update.message.text.split()[0][1:].lower()
    ca = SHORTCUTS.get(cmd)
    if not ca: return
    msg = await update.message.reply_text(f"🔍 Đang check *{cmd.upper()}*...", parse_mode="Markdown")
    pair = await get_token_by_ca(ca)
    if not pair:
        await msg.edit_text(f"❌ Lỗi dữ liệu.")
        return
    await msg.edit_text(format_pair(pair), parse_mode="Markdown", disable_web_page_preview=True)

async def ca_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ VD: `/ca 0x...`", parse_mode="Markdown")
        return
    ca = context.args[0]
    msg = await update.message.reply_text(f"🔍 Check CA...", parse_mode="Markdown")
    pair = await get_token_by_ca(ca)
    if not pair:
        await msg.edit_text(f"❌ Không tìm thấy Token.")
        return
    await msg.edit_text(format_pair(pair), parse_mode="Markdown", disable_web_page_preview=True)

# --- FLASK & WEBHOOK SETUP ---
app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("p", price_command))
application.add_handler(CommandHandler("ca", ca_command))
for cmd in SHORTCUTS.keys():
    application.add_handler(CommandHandler(cmd, shortcut_handler))

@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle incoming Telegram updates via bridge loop"""
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    
    # Dùng event loop đã được set làm loop chính của thread này
    loop = asyncio.get_event_loop()
    loop.run_until_complete(application.process_update(update))
    return "OK", 200

@app.route("/")
def index():
    return "Bot is running with Webhook!", 200

async def setup_webhook():
    if WEBHOOK_URL:
        webhook_path = f"{WEBHOOK_URL.rstrip('/')}/webhook"
        await application.bot.set_webhook(url=webhook_path)
        logging.info(f"Webhook set to: {webhook_path}")
    else:
        logging.warning("WEBHOOK_URL not set.")

if __name__ == "__main__":
    async def main():
        await application.initialize()
        await application.start() # Cần thiết khi dùng custom bridge
        await setup_webhook()
    
    # Khởi tạo event loop mới
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
    
    # Chạy Flask (blocking)
    app.run(host="0.0.0.0", port=PORT)
