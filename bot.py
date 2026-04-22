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

# Mapping tên chain người dùng nhập → ID trên DexScreener
CHAIN_MAP = {
    "eth": "ethereum",
    "ethereum": "ethereum",
    "sol": "solana",
    "solana": "solana",
    "base": "base",
    "monad": "monad",
}

# Keywords tìm kiếm theo từng chain — càng nhiều càng tốt để vét được nhiều token
CHAIN_SEARCH_KEYWORDS = {
    "ethereum": [
        "pepe", "shib", "floki", "meme", "wojak", "chad", "doge",
        "turbo", "apu", "landwolf", "inu", "cat", "toad", "bob",
        "higher", "skull", "mog", "hpos10i", "resistance dog",
    ],
    "solana": [
        "bonk", "wif", "popcat", "goat", "neiro", "mew", "slerf",
        "bome", "myro", "wen", "samo", "pnut", "giga", "retardio",
        "ponke", "michi", "ai16z", "fartcoin", "zerebro", "shoggoth",
    ],
    "monad": [
        "chog", "nads", "bob", "shmon", "monad", "MON", "ape",
        "moncock", "shramp", "anago", "emonad", "meme", "cat",
    ],
}

# Symbols bị loại (stablecoin, wrapped token, native coin)
IGNORE_SYMBOLS = {
    "USDT", "USDC", "WETH", "WBTC", "WMON", "DAI", "BUSD", "AUSD",
    "ETH", "MON", "SOL", "WSOL", "WBNB", "BNB", "MATIC", "WMATIC",
    "USDE", "FRAX", "TUSD", "USDP", "GUSD", "LUSD", "MIM",
}


# --- DEXSCREENER LOGIC (GIỮ NGUYÊN) ---
async def search_token_on_dex(query: str):
    await asyncio.sleep(0.5)
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
    await asyncio.sleep(0.5)
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


# --- LEADERBOARD LOGIC (ĐÃ CẢI TIẾN) ---

async def fetch_pairs_by_keyword(client: httpx.AsyncClient, keyword: str, chain: str) -> list:
    """Tìm kiếm 1 keyword, trả về list pair đúng chain."""
    try:
        url = f"https://api.dexscreener.com/latest/dex/search?q={keyword}"
        res = await client.get(url, timeout=10)
        if res.status_code != 200:
            return []
        data = res.json()
        pairs = data.get("pairs") or []
        return [p for p in pairs if p.get("chainId", "").lower() == chain.lower()]
    except Exception as e:
        logging.error(f"[leaderboard] Keyword '{keyword}' lỗi: {e}")
        return []

async def get_top_tokens_dexscreener(chain: str, limit: int = 10):
    """
    Lấy top meme tokens theo market cap cho chain cho trước.
    Trả về (list_pairs, error_message).
    """
    keywords = CHAIN_SEARCH_KEYWORDS.get(chain.lower(), [chain])
    pairs_all = []

    async with httpx.AsyncClient() as client:
        # Gọi song song tất cả keywords để nhanh hơn
        tasks = [fetch_pairs_by_keyword(client, kw, chain) for kw in keywords]
        results = await asyncio.gather(*tasks)
        for batch in results:
            pairs_all.extend(batch)

    if not pairs_all:
        return None, (
            f"Không tìm thấy token nào trên chain `{chain}`.\n"
            f"Monad cần có ít nhất 1 DEX active trên DexScreener."
        )

    # Lọc stablecoin / wrapped token
    pairs_all = [
        p for p in pairs_all
        if p.get("baseToken", {}).get("symbol", "").upper() not in IGNORE_SYMBOLS
    ]

    # Lọc token có thanh khoản quá thấp (< $1000) để tránh rác
    pairs_all = [
        p for p in pairs_all
        if float((p.get("liquidity") or {}).get("usd") or 0) >= 1_000
    ]

    # Ưu tiên marketCap, fallback sang fdv nếu không có
    def get_mcap(p):
        return float(p.get("marketCap") or p.get("fdv") or 0)

    pairs_all.sort(key=get_mcap, reverse=True)

    # Dedup theo contract address (giữ pair có mcap cao nhất)
    seen_addr = set()
    unique = []
    for p in pairs_all:
        addr = p.get("baseToken", {}).get("address", "").lower()
        if addr and addr not in seen_addr:
            seen_addr.add(addr)
            unique.append(p)

    return unique[:limit], None


def format_leaderboard(results: list, chain: str) -> str:
    chain_display = {
        "ethereum": "Ethereum 🔷",
        "solana": "Solana 🟣",
        "base": "Base 🔵",
        "monad": "Monad 🟣",
    }.get(chain.lower(), chain.upper())

    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    lines = [f"🏆 *Top 10 Meme — {chain_display}*\n"]

    for i, p in enumerate(results):
        base = p.get("baseToken", {})
        name = base.get("name", "Unknown")
        symbol = base.get("symbol", "???")

        price_usd  = p.get("priceUsd")
        mcap       = p.get("marketCap") or p.get("fdv") or 0
        vol_24h    = (p.get("volume") or {}).get("h24") or 0
        liquidity  = (p.get("liquidity") or {}).get("usd") or 0
        change_24h = (p.get("priceChange") or {}).get("h24") or 0

        try:
            chg = float(change_24h)
            chg_str = f"{'🟢' if chg > 0 else '🔴'} `{chg:+.1f}%`"
        except:
            chg_str = "⚪ `N/A`"

        medal = medals[i] if i < len(medals) else "🔹"
        lines.append(
            f"{medal} *{name}* (${symbol})\n"
            f"   💵 `{format_price(price_usd)}`  {chg_str}\n"
            f"   🏷 MCap: `{format_number(mcap)}`  "
            f"📊 Vol: `{format_number(vol_24h)}`  "
            f"💧 Liq: `{format_number(liquidity)}`\n"
        )
    return "\n".join(lines)


# --- BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🚀 *Meme Coin Price Bot*\n\n"
        "📌 *Lệnh:*\n"
        "/p `<tên coin>` — Check giá\n"
        "/ca `<contract address>` — Check theo CA\n"
        "/leaderboard `<chain>` — Top 10 meme (eth, sol, monad)\n\n"
        "💡 *Ví dụ:*\n"
        "/p PEPE\n"
        "/leaderboard sol\n\n"
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

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"[leaderboard] Nhận lệnh từ {update.message.from_user.username}, args={context.args}")

    if not context.args:
        await update.message.reply_text(
            "⚠️ Dùng: `/leaderboard <chain>`\n"
            "✅ Chain hỗ trợ: `eth`, `sol`, `monad`\n\n"
            "Ví dụ: `/leaderboard sol`",
            parse_mode="Markdown"
        )
        return

    chain_input = context.args[0].lower()
    chain = CHAIN_MAP.get(chain_input)

    if not chain:
        await update.message.reply_text(
            f"❌ Chain `{chain_input}` không hỗ trợ.\n"
            f"✅ Dùng: `eth`, `sol`, `monad`",
            parse_mode="Markdown"
        )
        return

    msg = await update.message.reply_text(
        f"⏳ Đang tải top 10 meme trên *{chain_input.upper()}*...",
        parse_mode="Markdown"
    )

    results, error = await get_top_tokens_dexscreener(chain)

    if error or not results:
        await msg.edit_text(f"❌ {error or 'Không có dữ liệu.'}", parse_mode="Markdown")
        return

    text = format_leaderboard(results, chain)
    await msg.edit_text(text, parse_mode="Markdown", disable_web_page_preview=True)


if __name__ == "__main__":
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("p", price_command))
    application.add_handler(CommandHandler("ca", ca_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))
    for cmd in SHORTCUTS.keys():
        application.add_handler(CommandHandler(cmd, shortcut_handler))

    logging.info("Bot starting in POLLING mode...")
    application.run_polling(drop_pending_updates=True)