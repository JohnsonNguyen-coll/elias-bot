import os
import httpx
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

async def search_token_on_dex(query: str):
    """Tìm token trên DexScreener bằng search endpoint"""
    url = f"https://api.dexscreener.com/latest/dex/search?q={query}"
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, timeout=10)
            data = res.json()
            pairs = data.get("pairs", [])
            if not pairs:
                return None
            # Lấy pair có volume cao nhất
            pairs.sort(key=lambda x: float(x.get("volume", {}).get("h24", 0) or 0), reverse=True)
            return pairs[0]
        except Exception as e:
            logging.error(f"Error searching token: {e}")
            return None

async def get_token_by_ca(ca: str):
    """Lấy token trên DexScreener bằng contract address"""
    url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, timeout=10)
            data = res.json()
            pairs = data.get("pairs", [])
            if not pairs:
                return None
            pairs.sort(key=lambda x: float(x.get("volume", {}).get("h24", 0) or 0), reverse=True)
            return pairs[0]
        except Exception as e:
            logging.error(f"Error fetching token by CA: {e}")
            return None

def format_number(n):
    """Format số cho dễ đọc"""
    if n is None:
        return "N/A"
    n = float(n)
    if n >= 1_000_000_000:
        return f"${n/1_000_000_000:.2f}B"
    elif n >= 1_000_000:
        return f"${n/1_000_000:.2f}M"
    elif n >= 1_000:
        return f"${n/1_000:.2f}K"
    else:
        return f"${n:.2f}"

def format_price(p):
    """Format giá coin tinh tế"""
    if p is None:
        return "N/A"
    p = float(p)
    if p == 0:
        return "$0.00"
    if p < 0.00000001:
        return f"${p:.12f}"
    elif p < 0.000001:
        return f"${p:.10f}"
    elif p < 0.01:
        return f"${p:.6f}"
    else:
        return f"${p:.4f}"

def format_pair(pair: dict) -> str:
    """Format thông tin pair thành message đẹp"""
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
        try:
            return "🟢" if float(v) > 0 else "🔴"
        except:
            return "⚪"

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🚀 *Meme Coin Price Bot*\n\n"
        "Tôi sẽ giúp bạn check giá token cực nhanh từ DexScreener!\n\n"
        "📌 *Lệnh cơ bản:*\n"
        "/p `<tên hoặc symbol>` — Check giá (VD: `/p PEPE`)\n"
        "/ca `<address>` — Check theo contract (VD: `/ca 0x...`)\n\n"
        "⚡️ *Lệnh tắt nhanh:*\n"
        "/bob, /anago, /chog, /emonad, /nads, /moncock, /shramp\n\n"
        "💡 *Ví dụ:* /p bonk, /p doge, /p solana"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Vui lòng nhập tên hoặc symbol coin!\nVD: `/p PEPE`", parse_mode="Markdown")
        return

    query = " ".join(context.args)
    status_msg = await update.message.reply_text(f"🔍 Đang tìm *{query.upper()}*...", parse_mode="Markdown")

    pair = await search_token_on_dex(query)

    if not pair:
        await status_msg.edit_text(f"❌ Không tìm thấy *{query.upper()}* trên DexScreener.", parse_mode="Markdown")
        return

    await status_msg.edit_text(format_pair(pair), parse_mode="Markdown", disable_web_page_preview=True)

async def shortcut_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command = update.message.text.split()[0][1:].lower() # Lấy text sau dấu /
    ca = SHORTCUTS.get(command)
    
    if not ca:
        return

    status_msg = await update.message.reply_text(f"🔍 Đang check *{command.upper()}*...", parse_mode="Markdown")
    pair = await get_token_by_ca(ca)

    if not pair:
        await status_msg.edit_text(f"❌ Không tìm thấy Token cho lệnh /{command}.", parse_mode="Markdown")
        return

    await status_msg.edit_text(format_pair(pair), parse_mode="Markdown", disable_web_page_preview=True)

async def ca_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Vui lòng nhập Contract Address!\nVD: `/ca 0x...`", parse_mode="Markdown")
        return

    ca = context.args[0]
    status_msg = await update.message.reply_text(f"🔍 Đang kiểm tra Contract...", parse_mode="Markdown")

    pair = await get_token_by_ca(ca)

    if not pair:
        await status_msg.edit_text(f"❌ Không tìm thấy Token với CA này.", parse_mode="Markdown")
        return

    await status_msg.edit_text(format_pair(pair), parse_mode="Markdown", disable_web_page_preview=True)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ LỖI: Chưa có TELEGRAM_BOT_TOKEN trong file .env!")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("p", price_command))
        app.add_handler(CommandHandler("ca", ca_command))
        
        # Thêm handlers cho các phím tắt
        for cmd in SHORTCUTS.keys():
            app.add_handler(CommandHandler(cmd, shortcut_handler))

        print("✅ Bot Meme Coin đang khởi động...")
        app.run_polling()
