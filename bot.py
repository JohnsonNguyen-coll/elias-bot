import os
import httpx
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

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
    # Hạn chế spam API
    await asyncio.sleep(0.5)
    url = f"https://api.dexscreener.com/latest/dex/search?q={query}"
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, timeout=10)
            data = res.json()
            pairs = data.get("pairs", [])
            if not pairs: return None
            # Lấy pair có volume cao nhất
            pairs.sort(key=lambda x: float(x.get("volume", {}).get("h24", 0) or 0), reverse=True)
            return pairs[0]
        except Exception as e:
            logging.error(f"Error searching token: {e}")
            return None

async def get_token_by_ca(ca: str):
    # Hạn chế spam API
    await asyncio.sleep(0.5)
    url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, timeout=10)
            data = res.json()
            pairs = data.get("pairs", [])
            if not pairs: return None
            # Lấy pair có volume cao nhất
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
    h1 = change.get("h1", 0) or 0
    h6 = change.get("h6", 0) or 0
    h24 = change.get("h24", 0) or 0
    
    volume_24h = pair.get("volume", {}).get("h24")
    liquidity = pair.get("liquidity", {}).get("usd")
    fdv = pair.get("fdv")
    
    dex = pair.get("dexId", "unknown").capitalize()
    chain = pair.get("chainId", "unknown").capitalize()
    url = pair.get("url", "")
    ca = base.get("address", "N/A")
    
    def change_emoji(v):
        try: return "🟢" if float(v) > 0 else "🔴"
        except: return "⚪"

    return (
        f"🪙 *{name}* (${symbol})\n"
        f"⛓ `{chain}` • 🏦 `{dex}`\n\n"
        f"💵 *Giá:* `{format_price(price_usd)}`\n\n"
        f"📈 *Biến động:*\n"
        f"  {change_emoji(h1)} 1h: `{float(h1):+.2f}%`\n"
        f"  {change_emoji(h6)} 6h: `{float(h6):+.2f}%`\n"
        f"  {change_emoji(h24)} 24h: `{float(h24):+.2f}%`\n\n"
        f"📊 *Volume 24h:* `{format_number(volume_24h)}`\n"
        f"💧 *Thanh khoản:* `{format_number(liquidity)}`\n"
        f"🏷 *FDV:* `{format_number(fdv)}`\n\n"
        f"📄 *CA:* `{ca}`"
    )

# --- BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🚀 *Meme Coin Price Bot*\n\n"
        "📌 *Lệnh:*\n"
        "/p `<tên coin>` — Check giá\n"
        "/ca `<contract address>` — Check theo CA\n\n"
        "💡 *Ví dụ:*\n"
        "/p PEPE\n"
        "/p bonk\n"
        "/ca 0xabc...123\n\n"
        "⚡️ *Lệnh tắt:* /bob, /anago, /chog, /emonad, /nads, /moncock, /shramp"
    )
    await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Dùng: `/p <tên coin>`\nVD: `/p PEPE`", parse_mode="Markdown")
        return
    query = " ".join(context.args)
    msg = await update.message.reply_text(f"🔍 Đang tìm *{query.upper()}*...", parse_mode="Markdown")
    pair = await search_token_on_dex(query)
    if not pair:
        await msg.edit_text(f"❌ Không tìm thấy *{query.upper()}* trên DexScreener.", parse_mode="Markdown")
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
        await update.message.reply_text("⚠️ Dùng: `/ca <contract address>`", parse_mode="Markdown")
        return
    ca = context.args[0]
    msg = await update.message.reply_text(f"🔍 Đang check CA...", parse_mode="Markdown")
    pair = await get_token_by_ca(ca)
    if not pair:
        await msg.edit_text(f"❌ Không tìm thấy contract này.")
        return
    await msg.edit_text(format_pair(pair), parse_mode="Markdown", disable_web_page_preview=True)

if __name__ == "__main__":
    application = ApplicationBuilder().token(TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("p", price_command))
    application.add_handler(CommandHandler("ca", ca_command))
    for cmd in SHORTCUTS.keys():
        application.add_handler(CommandHandler(cmd, shortcut_handler))

    logging.info("Bot starting in POLLING mode...")
    
    # Xóa webhook cũ nếu còn tồn tại để tránh lỗi Conflict 409
    import asyncio
    async def run_bot():
        await application.initialize()
        await application.bot.delete_webhook(drop_pending_updates=True)
        await application.updater.start_polling(drop_pending_updates=True)
        await application.start()

    # Lưu ý: run_polling() làm tất cả những việc trên, nhưng đôi khi gặp lỗi Conflict 
    # nếu webhook chưa được xóa sạch. Ta dùng drop_pending_updates=True trực tiếp trong run_polling.
    application.run_polling(drop_pending_updates=True)
